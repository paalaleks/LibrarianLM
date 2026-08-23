from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from librarianlm_i18n import kernel
from librarianlm_i18n.adapters import FilesystemArtifactStore, HmacPackageSigner, LxmlHtmlDocument
from librarianlm_i18n.workflows import AssemblyWorkflow, PrepareWorkflow


DIGEST = "a" * 64
RUN = "f" * 64


def source() -> kernel.CanonicalSourcePackage:
    html = '<html><body><article id="book"><p id="one">Start <em class="kept">middle <i>deep</i><a id="anchor" href="#note">anchor</a></em> end<img alt="image"> tail</p><p id="two">Start <em class="kept">middle <i>deep</i><a id="anchor-two" href="#note">anchor</a></em> end<img alt="image"> tail</p><aside id="chrome">untouched</aside><aside id="note">footnote</aside></article></body></html>'
    return kernel.CanonicalSourcePackage(
        source_html=html, source_html_digest=kernel.sha256_digest(html.encode()),
        converter_identity=kernel.ComponentIdentity(implementation="component:fixture", implementation_version="1", platform_abi="fixture", uv_lock_digest=DIGEST, package_versions=(), lxml_version="6.1.2", libxml_version="fixture", libxslt_version="fixture", html_serialization_fixture_digest=DIGEST),
        ownership_profile=kernel.OwnershipProfile(profile_id="component:ownership", profile_version="1", owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),), slot_rules=(kernel.SlotRule(element_id="chrome", disposition=kernel.SlotDisposition.EXCLUDED, reason="application chrome"), kernel.SlotRule(element_id="note", disposition=kernel.SlotDisposition.EXCLUDED, reason="footnote chrome"))),
        projection_profile=kernel.ProjectionProfile(profile_id="component:projection", profile_version="1", projections=(kernel.DeclaredProjection(projection_key="same", member_locations=(kernel.StructuralLocation(owned_root_id="book", path=(0,), slot="text"), kernel.StructuralLocation(owned_root_id="book", path=(1,), slot="text")), transformation_rule="replace-text"),)),
        segmentation_profile=kernel.SegmentationProfile(profile_id="component:protected", profile_version="2", rule="fixture-v2-protected-blocks"),
    )


def policy(value: kernel.CanonicalSourcePackage) -> kernel.PreparePolicy:
    return kernel.PreparePolicy(policy_id="component:policy", policy_version="1", accepted_ownership_profile_id=value.ownership_profile.profile_id, accepted_ownership_profile_version=value.ownership_profile.profile_version, accepted_projection_profile_id=value.projection_profile.profile_id, accepted_projection_profile_version=value.projection_profile.profile_version, accepted_segmentation_profile_id=value.segmentation_profile.profile_id, accepted_segmentation_profile_version=value.segmentation_profile.profile_version)


def sheets() -> tuple[kernel.EditorialSheet, kernel.EditorialSheet]:
    return (kernel.EditorialSheet(kind=kernel.EditorialSheetKind.TERMINOLOGY, state=kernel.EditorialSheetState.CONFIRMED), kernel.EditorialSheet(kind=kernel.EditorialSheetKind.STYLE, state=kernel.EditorialSheetState.CONFIRMED))


class AssemblyWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.store = FilesystemArtifactStore(Path(self.temp.name))
        self.signer = HmacPackageSigner({"key": b"secret"}, active_key_ids=frozenset({"key"}))
        self.prepare = PrepareWorkflow(store=self.store, document=LxmlHtmlDocument(), signer=self.signer)
        self.assemble = AssemblyWorkflow(store=self.store, document=LxmlHtmlDocument(), signer=self.signer)
        self.prepared = self.prepare.prepare(run_id="prepare", source_package=source(), policy=policy(source()), sheets=sheets(), run_snapshot_digest=RUN)
        self.assertIsNone(self.prepared.error)
        self.confirmed = self.prepare.confirm(package_digest=self.prepared.value.outcome.package_digest, requested_key_id="key", operator_id="operator")
        self.assertIsNone(self.confirmed.error)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _target(self) -> kernel.FixtureTargets:
        canonical = self.prepared.value.manifest.units[0]
        binding = self.store.read_object(canonical.inline_binding_map_digest, kernel.InlineBindingMap).value
        segments = self.store.read_object(canonical.protected_segments_digest, kernel.ProtectedBlockSegments).value
        stream = "".join(item.value for item in segments.segments)
        return kernel.FixtureTargets(targets=(kernel.FixtureTarget(source_unit_id=canonical.source_unit_id, value=stream.replace("Start", "Translated").replace("middle", "inner").replace("deep", "nested").replace("end", "finish").replace("tail", "after")),))

    def _forge(self, manifest: kernel.UnitManifest) -> tuple[str, kernel.ConfirmationReceipt]:
        manifest_digest = self.store.put_object(manifest).digest
        package = self.prepared.value.package.model_copy(update={"manifest_digest": manifest_digest})
        package_digest = self.store.put_object(package).digest
        signature = self.signer.sign(package_digest, "key").signature
        signature_digest = self.store.put_object(signature).digest
        return package_digest, kernel.ConfirmationReceipt(package_digest=package_digest, signature_digest=signature_digest, key_id="key", operator_id="operator")

    def _assert_blocked(self, package_digest: str, confirmation: kernel.ConfirmationReceipt, targets: kernel.FixtureTargets, code: str) -> None:
        before = len(tuple(self.store.objects.glob("*.json")))
        result = self.assemble.assemble(package_digest=package_digest, confirmation=confirmation, fixture_targets=targets)
        self.assertIsNone(result.value)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, code)
        self.assertEqual(len(tuple(self.store.objects.glob("*.json"))), before)

    def test_prepare_persists_pair_and_singleton_maps_and_assembly_preserves_markup(self) -> None:
        canonical = self.prepared.value.manifest.units[0]
        binding = self.store.read_object(canonical.inline_binding_map_digest, kernel.InlineBindingMap).value
        self.assertEqual(binding.entries[0].kind, "open")
        self.assertEqual(binding.entries[0].pair_id, binding.entries[-2].token_id)
        self.assertEqual(binding.entries[-1].kind, "empty")
        result = self.assemble.assemble(package_digest=self.prepared.value.outcome.package_digest, confirmation=self.confirmed.receipt, fixture_targets=self._target())
        self.assertIsNone(result.error)
        self.assertIn('<em class="kept">inner <i>nested</i><a id="anchor" href="#note">anchor</a></em> finish<img alt="image"> after', result.value.draft.html)
        self.assertEqual(result.value.draft.html.count("Translated"), 2)
        self.assertIn('<a id="anchor" href="#note">anchor</a>', result.value.draft.html)
        self.assertIn('<aside id="chrome">untouched</aside><aside id="note">footnote</aside>', result.value.draft.html)

    def test_forged_signature_and_every_invalid_token_shape_block_without_draft(self) -> None:
        signature = self.store.read_object(self.confirmed.receipt.signature_digest, kernel.SignatureRecord).value
        forged_digest = self.store.put_object(signature.model_copy(update={"signature": "forged"})).digest
        forged = self.confirmed.receipt.model_copy(update={"signature_digest": forged_digest})
        self._assert_blocked(self.prepared.value.outcome.package_digest, forged, self._target(), "signature-invalid")
        good = self._target()
        value = good.targets[0].value
        token = self.store.read_object(self.prepared.value.manifest.units[0].inline_binding_map_digest, kernel.InlineBindingMap).value.entries[0].token_id
        rendered = kernel.render_protected_token(token)
        cases = {
            "missing": value.replace(rendered, "", 1),
            "duplicate": value + rendered,
            "malformed": value + "[[[LLM:BIND:bad]]]",
            "crossed": value.replace(rendered, "TEMP", 1).replace(kernel.render_protected_token(self.store.read_object(self.prepared.value.manifest.units[0].inline_binding_map_digest, kernel.InlineBindingMap).value.entries[-2].token_id), rendered, 1).replace("TEMP", kernel.render_protected_token(self.store.read_object(self.prepared.value.manifest.units[0].inline_binding_map_digest, kernel.InlineBindingMap).value.entries[-2].token_id), 1),
            "foreign": value + "[[[LLM:BIND:AAAAAAAAAAAAAAAAAAAAAAAAAA]]]",
        }
        for name, invalid_value in cases.items():
            with self.subTest(name=name):
                invalid = good.model_copy(update={"targets": (good.targets[0].model_copy(update={"value": invalid_value}),)})
                self._assert_blocked(self.prepared.value.outcome.package_digest, self.confirmed.receipt, invalid, "malformed-binding-token" if name == "malformed" else "binding-token-sequence-invalid")

    def test_deterministic_repeated_assembly_is_byte_equivalent_and_rejects_unused_targets(self) -> None:
        targets = self._target()
        first = self.assemble.assemble(package_digest=self.prepared.value.outcome.package_digest, confirmation=self.confirmed.receipt, fixture_targets=targets)
        second = self.assemble.assemble(package_digest=self.prepared.value.outcome.package_digest, confirmation=self.confirmed.receipt, fixture_targets=targets)
        self.assertEqual(first.value.draft.html.encode(), second.value.draft.html.encode())
        self.assertEqual(kernel.canonical_bytes(first.value.report), kernel.canonical_bytes(second.value.report))
        self.assertEqual(first.value.report.candidate_draft_digest, second.value.report.candidate_draft_digest)
        self.assertEqual(first.value.report.application_evidence_digest, second.value.report.application_evidence_digest)
        extra = targets.model_copy(update={"targets": targets.targets + (kernel.FixtureTarget(source_unit_id=self.prepared.value.manifest.units[1].source_unit_id, value="unused"),)})
        self._assert_blocked(self.prepared.value.outcome.package_digest, self.confirmed.receipt, extra, "fixture-target-inventory-mismatch")

    def test_manifest_readiness_lineage_fingerprint_and_artifact_tampering_block(self) -> None:
        manifest = self.prepared.value.manifest
        for field, value in (("processing", kernel.StatusValue.INCOMPLETE), ("processing", kernel.StatusValue.BLOCKED), ("publication", kernel.StatusValue.NOT_READY)):
            with self.subTest(readiness=f"{field}:{value}"):
                altered = manifest.model_copy(update={"status": manifest.status.model_copy(update={field: value})})
                package_digest, receipt = self._forge(altered)
                self._assert_blocked(package_digest, receipt, self._target(), "manifest-not-ready")
        altered_source = source().model_copy(update={"source_html": source().source_html.replace("Start", "Drift", 1), "source_html_digest": kernel.sha256_digest(source().source_html.replace("Start", "Drift", 1).encode())})
        changed_package = self.prepared.value.package.model_copy(update={"source_package_digest": self.store.put_object(altered_source).digest})
        changed_digest = self.store.put_object(changed_package).digest
        signature = self.signer.sign(changed_digest, "key").signature
        changed_receipt = kernel.ConfirmationReceipt(package_digest=changed_digest, signature_digest=self.store.put_object(signature).digest, key_id="key", operator_id="operator")
        self._assert_blocked(changed_digest, changed_receipt, self._target(), "manifest-source-mismatch")
        unit = manifest.units[0].model_copy(update={"structural_fingerprint": f"structural-fingerprint:{'b' * 64}"})
        altered = manifest.model_copy(update={"units": (unit,) + manifest.units[1:]})
        package_digest, receipt = self._forge(altered)
        self._assert_blocked(package_digest, receipt, self._target(), "structural-resolution-failed")
        mismatch = manifest.units[0].model_copy(update={"inline_binding_map_digest": manifest.units[1].inline_binding_map_digest})
        altered = manifest.model_copy(update={"units": (mismatch,) + manifest.units[1:]})
        package_digest, receipt = self._forge(altered)
        self._assert_blocked(package_digest, receipt, self._target(), "protected-artifact-mismatch")
        mismatch = manifest.units[0].model_copy(update={"protected_segments_digest": manifest.units[1].protected_segments_digest})
        altered = manifest.model_copy(update={"units": (mismatch,) + manifest.units[1:]})
        package_digest, receipt = self._forge(altered)
        self._assert_blocked(package_digest, receipt, self._target(), "protected-artifact-mismatch")

    def test_protected_artifact_contract_and_projection_fail_closed_cases(self) -> None:
        canonical = self.prepared.value.manifest.units[0]
        segments = self.store.read_object(canonical.protected_segments_digest, kernel.ProtectedBlockSegments).value
        for replacement in (segments.segments[0].model_copy(update={"ordinal": 2}), segments.segments[1].model_copy(update={"ordinal": 0})):
            changed = (replacement,) + segments.segments[1:]
            with self.subTest(segments=tuple(item.ordinal for item in changed)):
                with self.assertRaises(ValidationError):
                    kernel.ProtectedBlockSegments(**(segments.model_dump() | {"segments": changed}))
        transform = self.prepared.value.manifest.projection_groups[0].model_copy(update={"transformation_rule": "unsupported-transform"})
        altered = self.prepared.value.manifest.model_copy(update={"projection_groups": (transform,)})
        package_digest, receipt = self._forge(altered)
        self._assert_blocked(package_digest, receipt, self._target(), "unsupported-projection-transform")
        incompatible_html = source().source_html.replace('<a id="anchor-two" href="#note">anchor</a>', '<strong>different topology</strong>')
        incompatible_source = source().model_copy(update={"source_html": incompatible_html, "source_html_digest": kernel.sha256_digest(incompatible_html.encode())})
        rejected = self.prepare.prepare(run_id="incompatible", source_package=incompatible_source, policy=policy(incompatible_source), sheets=sheets(), run_snapshot_digest=RUN)
        self.assertIsNone(rejected.error)
        self.assertEqual(rejected.value.outcome.status, "blocked")
        self.assertEqual(rejected.value.outcome.findings[0].code, "invalid-declared-projection")

    def test_missing_targets_and_translated_declared_attributes(self) -> None:
        self._assert_blocked(self.prepared.value.outcome.package_digest, self.confirmed.receipt, kernel.FixtureTargets(targets=()), "fixture-target-inventory-mismatch")
        html = '<html><body><article id="book"><p>body</p><img id="cover" alt="Cover"><aside id="chrome">chrome</aside></article></body></html>'
        attribute_source = source().model_copy(update={
            "source_html": html, "source_html_digest": kernel.sha256_digest(html.encode()),
            "ownership_profile": kernel.OwnershipProfile(profile_id="component:attribute-owner", profile_version="1", owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),), slot_rules=(kernel.SlotRule(element_id="cover", disposition=kernel.SlotDisposition.REQUIRED, reason="alt", attribute_names=("alt",)), kernel.SlotRule(element_id="chrome", disposition=kernel.SlotDisposition.EXCLUDED, reason="chrome"))),
            "projection_profile": kernel.ProjectionProfile(profile_id="component:attribute-projection", profile_version="1"),
            "segmentation_profile": kernel.SegmentationProfile(profile_id="component:attribute-segments", profile_version="1", rule="fixture-v1-one-unit-per-nonblank-slot"),
        })
        prepared = self.prepare.prepare(run_id="attribute", source_package=attribute_source, policy=policy(attribute_source), sheets=sheets(), run_snapshot_digest=RUN)
        confirmed = self.prepare.confirm(package_digest=prepared.value.outcome.package_digest, requested_key_id="key", operator_id="operator")
        targets = kernel.FixtureTargets(targets=tuple(kernel.FixtureTarget(source_unit_id=unit.source_unit_id, value="Translated Cover" if unit.content_class is kernel.ContentClass.ATTRIBUTE else "<b>translated</b>") for unit in prepared.value.manifest.units if unit.eligibility is kernel.Eligibility.REQUIRED))
        token_targets = targets.model_copy(update={"targets": tuple(target.model_copy(update={"value": "[[[LLM:BIND:AAAAAAAAAAAAAAAAAAAAAAAAAA]]]"}) if target.source_unit_id == prepared.value.manifest.units[0].source_unit_id else target for target in targets.targets)})
        self._assert_blocked(prepared.value.outcome.package_digest, confirmed.receipt, token_targets, "protected-token-in-plain-target")
        result = self.assemble.assemble(package_digest=prepared.value.outcome.package_digest, confirmation=confirmed.receipt, fixture_targets=targets)
        self.assertIsNone(result.error)
        self.assertIn('alt="Translated Cover"', result.value.draft.html)
        self.assertIn('&lt;b&gt;translated&lt;/b&gt;', result.value.draft.html)

    def test_final_guard_regressions_for_selection_identity_movement_and_projection_order(self) -> None:
        binding = self.store.read_object(self.prepared.value.manifest.units[0].inline_binding_map_digest, kernel.InlineBindingMap).value
        self.assertEqual(tuple(entry.token_id for entry in binding.entries), tuple(kernel.derive_token_id(binding.source_unit_id, entry.kind, entry.source_order_ordinal) for entry in binding.entries))
        # Move two complete, balanced sibling pairs: this is legal protected
        # token movement and must not be rejected as an order-only violation.
        target = self._target()
        tokens = tuple(kernel.render_protected_token(entry.token_id) for entry in binding.entries)
        moved = "Translated " + tokens[0] + tokens[3] + "link" + tokens[4] + tokens[1] + "nested" + tokens[2] + tokens[5] + " finish" + tokens[6] + " after"
        moved_result = self.assemble.assemble(package_digest=self.prepared.value.outcome.package_digest, confirmation=self.confirmed.receipt, fixture_targets=target.model_copy(update={"targets": (target.targets[0].model_copy(update={"value": moved}),)}))
        self.assertIsNone(moved_result.error)
        self.assertIn('<em class="kept"><a id="anchor" href="#note">link</a><i>nested</i></em> finish', moved_result.value.draft.html)
        self.assertIn('<aside id="chrome">untouched</aside><aside id="note">footnote</aside>', moved_result.value.draft.html)
        reserved_html = source().source_html.replace("Start", "[[[LLM:BIND:AAAAAAAAAAAAAAAAAAAAAAAAAA]]]", 1)
        reserved = source().model_copy(update={"source_html": reserved_html, "source_html_digest": kernel.sha256_digest(reserved_html.encode())})
        blocked = self.prepare.prepare(run_id="reserved", source_package=reserved, policy=policy(reserved), sheets=sheets(), run_snapshot_digest=RUN)
        self.assertEqual(blocked.value.outcome.findings[0].code, "reserved-binding-token-source")
        script_html = source().source_html.replace("middle", "<script>bad</script>", 1)
        unsupported = source().model_copy(update={"source_html": script_html, "source_html_digest": kernel.sha256_digest(script_html.encode())})
        blocked = self.prepare.prepare(run_id="script", source_package=unsupported, policy=policy(unsupported), sheets=sheets(), run_snapshot_digest=RUN)
        self.assertEqual(blocked.value.outcome.findings[0].code, "protected-block-unsupported")
        profile = source().projection_profile.projections[0]
        reordered_source = source().model_copy(update={"projection_profile": source().projection_profile.model_copy(update={"projections": (profile.model_copy(update={"member_locations": tuple(reversed(profile.member_locations))}),)})})
        reordered = self.prepare.prepare(run_id="reordered", source_package=reordered_source, policy=policy(reordered_source), sheets=sheets(), run_snapshot_digest=RUN)
        self.assertEqual(reordered.value.outcome.status, "ready-for-confirmation")
        group = reordered.value.manifest.projection_groups[0]
        self.assertEqual(group.member_locators, tuple(unit.locator for unit in reordered.value.manifest.units if unit.projection_group_id == group.group_id))
