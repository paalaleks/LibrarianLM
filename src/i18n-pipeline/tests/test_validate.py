from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from pydantic import ValidationError

from librarianlm_i18n import kernel
from librarianlm_i18n.adapters import (
    FilesystemArtifactStore,
    FixtureResidualLanguageDetector,
    HmacPackageSigner,
    LxmlHtmlDocument,
)
from librarianlm_i18n.ports import ResidualLanguageResult
from librarianlm_i18n.workflows import AssemblyWorkflow, PrepareWorkflow, ValidationWorkflow


DIGEST = "a" * 64
RUN = "f" * 64


def component(name: str = "fixture") -> kernel.ComponentIdentity:
    return kernel.ComponentIdentity(
        implementation=f"component:{name}", implementation_version="1", platform_abi="fixture",
        uv_lock_digest=DIGEST, package_versions=(), lxml_version="6.1.2",
        libxml_version="fixture", libxslt_version="fixture",
        html_serialization_fixture_digest=DIGEST,
    )


def source() -> kernel.CanonicalSourcePackage:
    html = (
        '<html lang="en" dir="ltr"><body>'
        '<header><h1>Reader</h1></header>'
        '<nav aria-label="Chapters"><a id="navlink" href="#chapter" tabindex="0">Chapter</a></nav>'
        '<main><article id="book">'
        '<h2 id="chapter">Hello</h2>'
        '<p id="body">Hello <em class="kept">world</em></p>'
        '<p id="body-copy">Hello <em class="kept">world</em></p>'
        '<p id="foreign" lang="fr" dir="ltr">Bonjour</p>'
        '</article><a id="noteref" role="doc-noteref" href="#note">Note</a>'
        '<aside id="note" role="doc-footnote">Footnote <a href="#noteref">Back</a></aside></main>'
        '<footer><button id="next" tabindex="0">Next</button></footer>'
        '</body></html>'
    )
    return kernel.CanonicalSourcePackage(
        source_html=html,
        source_html_digest=kernel.sha256_digest(html.encode()),
        converter_identity=component(),
        ownership_profile=kernel.OwnershipProfile(
            profile_id="component:ownership", profile_version="1",
            owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),),
            slot_rules=(kernel.SlotRule(
                element_id="foreign", disposition=kernel.SlotDisposition.EXCLUDED,
                reason="declared foreign-language quotation",
            ),),
        ),
        projection_profile=kernel.ProjectionProfile(
            profile_id="component:projection", profile_version="1",
            projections=(kernel.DeclaredProjection(
                projection_key="body-copy",
                member_locations=(
                    kernel.StructuralLocation(owned_root_id="book", path=(1,), slot="text"),
                    kernel.StructuralLocation(owned_root_id="book", path=(2,), slot="text"),
                ),
                transformation_rule="replace-text",
            ),),
        ),
        segmentation_profile=kernel.SegmentationProfile(
            profile_id="component:protected", profile_version="2",
            rule="fixture-v2-protected-blocks",
        ),
    )


class AlternatingDetector:
    def __init__(self, identity: kernel.ComponentIdentity) -> None:
        self._identity = identity
        self._calls = 0

    @property
    def identity(self) -> kernel.ComponentIdentity:
        return self._identity

    def inspect(self, *, source_unit_id: str, source_text: str, target_text: str) -> ResidualLanguageResult:
        self._calls += 1
        return ResidualLanguageResult(evidence=kernel.ResidualLanguageEvidence(
            source_unit_id=source_unit_id,
            detector=self.identity,
            residual_count=self._calls % 2,
            matched_terms=("unstable",) if self._calls % 2 else (),
            limitation="deliberately alternating test detector",
        ))


class MisattributedDetector:
    def __init__(self, identity: kernel.ComponentIdentity, wrong_unit_id: str) -> None:
        self._identity = identity
        self._wrong_unit_id = wrong_unit_id

    @property
    def identity(self) -> kernel.ComponentIdentity:
        return self._identity

    def inspect(self, *, source_unit_id: str, source_text: str, target_text: str) -> ResidualLanguageResult:
        return ResidualLanguageResult(evidence=kernel.ResidualLanguageEvidence(
            source_unit_id=self._wrong_unit_id, detector=component("wrong-detector"),
            residual_count=0, matched_terms=(), limitation="misattribution test",
        ))


class ValidationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.store = FilesystemArtifactStore(Path(self.temp.name))
        self.signer = HmacPackageSigner({"key": b"secret"}, active_key_ids=frozenset({"key"}))
        self.document = LxmlHtmlDocument()
        self.source = source()
        self.counter = 0
        self.base = self._build()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _build(
        self,
        controls: kernel.ValidationControls | None = None,
        *,
        replacements: dict[tuple[int, ...], dict[str, str]] | None = None,
        detector=None,
    ) -> SimpleNamespace:
        self.counter += 1
        controls = controls or kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
        )
        policy = kernel.PreparePolicy(
            policy_id="component:policy", policy_version="1",
            accepted_ownership_profile_id=self.source.ownership_profile.profile_id,
            accepted_ownership_profile_version=self.source.ownership_profile.profile_version,
            accepted_projection_profile_id=self.source.projection_profile.profile_id,
            accepted_projection_profile_version=self.source.projection_profile.profile_version,
            accepted_segmentation_profile_id=self.source.segmentation_profile.profile_id,
            accepted_segmentation_profile_version=self.source.segmentation_profile.profile_version,
            validation_controls=controls,
        )
        prepare = PrepareWorkflow(store=self.store, document=self.document, signer=self.signer)
        prepared = prepare.prepare(
            run_id=f"prepare-{self.counter}", source_package=self.source, policy=policy,
            sheets=(
                kernel.EditorialSheet(kind=kernel.EditorialSheetKind.TERMINOLOGY, state=kernel.EditorialSheetState.CONFIRMED),
                kernel.EditorialSheet(kind=kernel.EditorialSheetKind.STYLE, state=kernel.EditorialSheetState.CONFIRMED),
            ),
            run_snapshot_digest=RUN,
        )
        self.assertIsNone(prepared.error)
        self.assertEqual(prepared.value.outcome.status, "ready-for-confirmation")
        package_digest = prepared.value.outcome.package_digest
        confirmed = prepare.confirm(package_digest=package_digest, requested_key_id="key", operator_id="operator")
        self.assertIsNone(confirmed.error)
        manifest = prepared.value.manifest
        groups = {group.group_id: group for group in manifest.projection_groups}
        canonicals = tuple(
            unit for unit in manifest.units
            if unit.eligibility is kernel.Eligibility.REQUIRED
            and (unit.projection_group_id is None or groups[unit.projection_group_id].canonical_source_unit_id == unit.source_unit_id)
        )
        values = []
        for unit in canonicals:
            if unit.protected_segments_digest is not None:
                segments = self.store.read_object(unit.protected_segments_digest, kernel.ProtectedBlockSegments).value
                value = "".join(item.value for item in segments.segments)
            else:
                selected = self.document.select(self.source).slots
                value = next(slot.text for slot in selected if slot.location == unit.structural_location)
            mapping = (replacements or {}).get(unit.structural_location.path)
            if mapping is None:
                mapping = {"Hello": "Kapittel"} if unit.structural_location.path == (0,) else {"Hello": "Hei", "world": "verden"}
            for old, new in mapping.items():
                value = value.replace(old, new)
            values.append(kernel.FixtureTarget(source_unit_id=unit.source_unit_id, value=value))
        assembled = AssemblyWorkflow(store=self.store, document=self.document, signer=self.signer).assemble(
            package_digest=package_digest,
            confirmation=confirmed.receipt,
            fixture_targets=kernel.FixtureTargets(targets=tuple(values)),
        )
        self.assertIsNone(assembled.error)
        workflow = ValidationWorkflow(
            store=self.store, document=self.document, signer=self.signer,
            residual_detector=detector,
        )
        return SimpleNamespace(
            prepared=prepared.value, package_digest=package_digest,
            confirmation=confirmed.receipt, assembled=assembled.value,
            workflow=workflow,
            units_by_path={unit.structural_location.path: unit for unit in manifest.units if unit.structural_location is not None},
        )

    def _validate(self, built: SimpleNamespace, report_digest: str | None = None):
        return built.workflow.validate(
            package_digest=built.package_digest,
            confirmation=built.confirmation,
            assembly_report_digest=report_digest or built.assembled.report_digest,
        )

    def _tampered_report(self, built: SimpleNamespace, html: str) -> str:
        candidate = built.assembled.draft.model_copy(update={
            "html": html,
            "html_digest": kernel.sha256_digest(html.encode()),
        })
        candidate_digest = self.store.put_object(candidate).digest
        evidence = self.store.read_object(
            built.assembled.report.application_evidence_digest, kernel.ApplicationEvidence,
        ).value.model_copy(update={"candidate_html_digest": candidate.html_digest})
        evidence_digest = self.store.put_object(evidence).digest
        report = built.assembled.report.model_copy(update={
            "candidate_draft_digest": candidate_digest,
            "application_evidence_digest": evidence_digest,
        })
        return self.store.put_object(report).digest

    def test_clean_graph_is_read_only_and_emits_repeatable_machine_truth(self) -> None:
        input_bytes = {path.name: path.read_bytes() for path in self.store.objects.glob("*.json")}
        first = self._validate(self.base)
        second = self._validate(self.base)
        self.assertIsNone(first.error)
        self.assertIsNotNone(first.value.draft)
        self.assertEqual(kernel.canonical_bytes(first.value.report), kernel.canonical_bytes(second.value.report))
        self.assertEqual(kernel.canonical_bytes(first.value.summary), kernel.canonical_bytes(second.value.summary))
        self.assertEqual(kernel.canonical_bytes(first.value.draft), kernel.canonical_bytes(second.value.draft))
        self.assertEqual(first.value.report.status.completeness, kernel.StatusValue.COMPLETE)
        self.assertEqual(first.value.report.status.compliance, kernel.StatusValue.CLEAN)
        self.assertEqual(first.value.draft.status.review, kernel.StatusValue.NOT_STARTED)
        self.assertEqual(first.value.draft.status.publication, kernel.StatusValue.NOT_READY)
        self.assertEqual(
            input_bytes,
            {name: (self.store.objects / name).read_bytes() for name in input_bytes},
        )

    def test_structural_accessibility_binding_projection_and_excluded_tampering_block(self) -> None:
        original = self.base.assembled.draft.html
        cases = {
            "heading": original.replace("<h2", "<h4").replace("</h2>", "</h4>"),
            "landmark": original.replace("<nav ", "<section ").replace("</nav>", "</section>"),
            "focus": original.replace('tabindex="0">Chapter', 'tabindex="2">Chapter'),
            "anchor-footnote": original.replace('href="#note"', 'href="#missing"'),
            "binding": original.replace('<em class="kept">', '<strong class="kept">').replace("</em>", "</strong>"),
            "projection": original.replace("Hei <em", "Forskjellig <em", 1),
            "excluded": original.replace("Bonjour", "Salut"),
            "outside-owned-root": original.replace("Reader", "Changed reader chrome"),
        }
        for name, html in cases.items():
            with self.subTest(name=name):
                result = self._validate(self.base, self._tampered_report(self.base, html))
                self.assertIsNone(result.error)
                self.assertIsNone(result.value.draft)
                self.assertTrue(result.value.report.findings)
                self.assertEqual(result.value.report.status.publication, kernel.StatusValue.NOT_READY)
                for finding in result.value.report.findings:
                    self.assertTrue(finding.expected)
                    self.assertTrue(finding.observed)
                    self.assertTrue(finding.next_action)

    def test_hostile_or_cross_wired_lineage_fails_before_outputs(self) -> None:
        result = self._validate(self.base, "b" * 64)
        self.assertIsNotNone(result.error)
        report = self.base.assembled.report.model_copy(update={
            "lineage": self.base.assembled.report.lineage.model_copy(update={
                "confirmation_signature_digest": "b" * 64,
            }),
        })
        report_digest = self.store.put_object(report).digest
        before = len(tuple(self.store.objects.glob("*.json")))
        result = self._validate(self.base, report_digest)
        self.assertEqual(result.error.code, "assembly-report-lineage-invalid")
        self.assertEqual(len(tuple(self.store.objects.glob("*.json"))), before)
        evidence = self.store.read_object(
            self.base.assembled.report.application_evidence_digest, kernel.ApplicationEvidence,
        ).value.model_copy(update={"applied_member_ids": ()})
        report = self.base.assembled.report.model_copy(update={
            "application_evidence_digest": self.store.put_object(evidence).digest,
        })
        result = self._validate(self.base, self.store.put_object(report).digest)
        self.assertEqual(result.error.code, "application-evidence-member-mismatch")

    def test_scoped_terminology_blocker_preserves_complete_status(self) -> None:
        body_id = self.base.units_by_path[(1,)].source_unit_id
        controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
            terminology=(kernel.TerminologyControl(
                rule_id="locked-body-term", required_unit_ids=(body_id,), required_terms=("Mangler",),
            ),),
        )
        built = self._build(controls)
        result = self._validate(built)
        self.assertIsNone(result.error)
        self.assertIsNone(result.value.draft)
        self.assertEqual(result.value.report.findings[0].code, "terminology-control-failed")
        self.assertEqual(result.value.report.status.completeness, kernel.StatusValue.COMPLETE)
        self.assertEqual(result.value.report.status.compliance, kernel.StatusValue.FAILED)

    def test_residual_tolerance_exemption_evidence_and_limitations(self) -> None:
        detector_identity = component("residual")
        detector = FixtureResidualLanguageDetector(detector_identity)
        body_id = self.base.units_by_path[(1,)].source_unit_id
        failing_controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
            residual_language=kernel.ResidualLanguageControl(detector=detector_identity, tolerance=0),
        )
        replacements = {(1,): {"world": "verden"}}
        failed = self._validate(self._build(failing_controls, replacements=replacements, detector=detector))
        self.assertTrue(any(item.code == "residual-language-detected" for item in failed.value.report.findings))
        self.assertTrue(failed.value.report.residual_language_evidence)
        self.assertIn("fixture exact-token overlap", failed.value.report.limitations[0])
        tolerant_controls = failing_controls.model_copy(update={
            "residual_language": failing_controls.residual_language.model_copy(update={"tolerance": 1}),
        })
        tolerant = self._validate(self._build(tolerant_controls, replacements=replacements, detector=detector))
        self.assertIsNotNone(tolerant.value.draft)
        body_copy_id = self.base.units_by_path[(2,)].source_unit_id
        exempt_controls = failing_controls.model_copy(update={
            "residual_language": failing_controls.residual_language.model_copy(update={"exempt_unit_ids": (body_id, body_copy_id)}),
        })
        exempt = self._validate(self._build(exempt_controls, replacements=replacements, detector=detector))
        self.assertIsNotNone(exempt.value.draft)
        self.assertEqual(exempt.value.report.residual_exempt_unit_ids, (body_id, body_copy_id))

    def test_canonical_bcp47_rtl_and_passage_directionality(self) -> None:
        with self.assertRaises(ValidationError):
            kernel.LocaleMetadata(language="EN-us", direction="ltr")
        with self.assertRaises(ValidationError):
            kernel.LocaleMetadata(language="ar", direction="ltr")
        rtl_controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="ar", direction="rtl"),
        )
        built = self._build(rtl_controls)
        valid = self._validate(built)
        self.assertIsNotNone(valid.value.draft)
        self.assertIn('<html lang="ar" dir="rtl">', built.assembled.draft.html)
        invalid_html = built.assembled.draft.html.replace('lang="fr" dir="ltr"', 'lang="AR" dir="ltr"')
        invalid = self._validate(built, self._tampered_report(built, invalid_html))
        self.assertTrue(any(item.code == "passage-locale-invalid" for item in invalid.value.report.findings))
        self.assertIsNone(invalid.value.draft)

    def test_source_locale_mismatch_and_invalid_candidate_emit_machine_truth(self) -> None:
        controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="fr", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
        )
        built = self._build(controls)
        mismatch = self._validate(built)
        self.assertIsNone(mismatch.error)
        self.assertIsNone(mismatch.value.draft)
        self.assertTrue(any(item.code == "source-locale-mismatch" for item in mismatch.value.report.findings))
        invalid_html = self.base.assembled.draft.html.replace('id="book"', 'id="missing-book"')
        invalid = self._validate(self.base, self._tampered_report(self.base, invalid_html))
        self.assertIsNone(invalid.error)
        self.assertIsNone(invalid.value.draft)
        self.assertEqual(invalid.value.report.findings[0].code, "candidate-html-invalid")

    def test_residual_detector_must_be_declared_and_evidence_must_be_attributed(self) -> None:
        undeclared = self._build(detector=AlternatingDetector(component("undeclared")))
        ignored = self._validate(undeclared)
        self.assertIsNotNone(ignored.value.draft)
        self.assertEqual(ignored.value.report.residual_language_evidence, ())
        detector_identity = component("declared")
        controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
            residual_language=kernel.ResidualLanguageControl(detector=detector_identity, tolerance=0),
        )
        wrong_unit = self.base.units_by_path[(0,)].source_unit_id
        built = self._build(controls, detector=MisattributedDetector(detector_identity, wrong_unit))
        result = self._validate(built)
        self.assertEqual(result.error.code, "residual-detector-evidence-mismatch")

    def test_validation_control_scopes_fail_during_prepare(self) -> None:
        existing = self.base.units_by_path[(1,)].source_unit_id
        unknown = existing[:-1] + ("a" if existing[-1] != "a" else "b")
        controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
            terminology=(kernel.TerminologyControl(
                rule_id="unknown-scope", required_unit_ids=(unknown,), required_terms=("Hei",),
            ),),
        )
        policy = kernel.PreparePolicy(
            policy_id="component:policy", policy_version="1",
            accepted_ownership_profile_id=self.source.ownership_profile.profile_id,
            accepted_ownership_profile_version=self.source.ownership_profile.profile_version,
            accepted_projection_profile_id=self.source.projection_profile.profile_id,
            accepted_projection_profile_version=self.source.projection_profile.profile_version,
            accepted_segmentation_profile_id=self.source.segmentation_profile.profile_id,
            accepted_segmentation_profile_version=self.source.segmentation_profile.profile_version,
            validation_controls=controls,
        )
        result = PrepareWorkflow(store=self.store, document=self.document, signer=self.signer).prepare(
            run_id="invalid-controls", source_package=self.source, policy=policy,
            sheets=(
                kernel.EditorialSheet(kind=kernel.EditorialSheetKind.TERMINOLOGY, state=kernel.EditorialSheetState.CONFIRMED),
                kernel.EditorialSheet(kind=kernel.EditorialSheetKind.STYLE, state=kernel.EditorialSheetState.CONFIRMED),
            ),
            run_snapshot_digest=RUN,
        )
        self.assertEqual(result.error.code, "validation-control-scope-invalid")

    def test_nondeterministic_detector_is_explicitly_blocking(self) -> None:
        detector_identity = component("alternating")
        controls = kernel.ValidationControls(
            source_locale=kernel.LocaleMetadata(language="en", direction="ltr"),
            target_locale=kernel.LocaleMetadata(language="nb", direction="ltr"),
            residual_language=kernel.ResidualLanguageControl(detector=detector_identity, tolerance=2),
        )
        built = self._build(controls, detector=AlternatingDetector(detector_identity))
        result = self._validate(built)
        self.assertIsNone(result.error)
        self.assertIsNone(result.value.draft)
        self.assertTrue(any(item.code == "validation-nondeterministic" for item in result.value.report.findings))


if __name__ == "__main__":
    unittest.main()
