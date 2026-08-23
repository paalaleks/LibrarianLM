from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from librarianlm_i18n import kernel
from librarianlm_i18n.adapters import FilesystemArtifactStore, HmacPackageSigner, LxmlHtmlDocument
from librarianlm_i18n.workflows import PrepareWorkflow


RUN_DIGEST = "f" * 64
DIGEST = "a" * 64


def component() -> kernel.ComponentIdentity:
    return kernel.ComponentIdentity(
        implementation="component:fixture-converter", implementation_version="1",
        platform_abi="fixture", uv_lock_digest=DIGEST, package_versions=(),
        lxml_version="6.1.2", libxml_version="fixture", libxslt_version="fixture",
        html_serialization_fixture_digest=DIGEST,
    )


def sheets() -> tuple[kernel.EditorialSheet, kernel.EditorialSheet]:
    return (
        kernel.EditorialSheet(kind=kernel.EditorialSheetKind.TERMINOLOGY, state=kernel.EditorialSheetState.CONFIRMED),
        kernel.EditorialSheet(kind=kernel.EditorialSheetKind.STYLE, state=kernel.EditorialSheetState.CONFIRMED),
    )


def package(*, projection: bool = True, html: str | None = None) -> kernel.CanonicalSourcePackage:
    html = html or "<html><body><article id=\"book\"><p id=\"one\">same</p><p id=\"two\">same</p><p id=\"three\">same</p><img id=\"cover\" alt=\"Cover\"><aside id=\"app\" data-librarianlm-owned=\"application\">chrome</aside></article></body></html>"
    projections = ()
    if projection:
        projections = (kernel.DeclaredProjection(
            projection_key="duplicated-heading",
            member_locations=(
                kernel.StructuralLocation(owned_root_id="book", path=(0,), slot="text"),
                kernel.StructuralLocation(owned_root_id="book", path=(1,), slot="text"),
            ),
            transformation_rule="replace-text",
        ),)
    return kernel.CanonicalSourcePackage(
        source_html=html, source_html_digest=kernel.sha256_digest(html.encode()), converter_identity=component(),
        ownership_profile=kernel.OwnershipProfile(
            profile_id="component:ownership-fixture", profile_version="1",
            owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),),
            slot_rules=(kernel.SlotRule(element_id="cover", disposition=kernel.SlotDisposition.REQUIRED, reason="cover alt", attribute_names=("alt",)),),
        ),
        projection_profile=kernel.ProjectionProfile(profile_id="component:projection-fixture", profile_version="1", projections=projections),
        segmentation_profile=kernel.SegmentationProfile(profile_id="component:fixture-v1", profile_version="1", rule="fixture-v1-one-unit-per-nonblank-slot"),
    )


def policy(source: kernel.CanonicalSourcePackage | None = None, *, allow_warnings: bool = False) -> kernel.PreparePolicy:
    source = source or package()
    return kernel.PreparePolicy(
        policy_id="component:policy-fixture", policy_version="1",
        accepted_ownership_profile_id=source.ownership_profile.profile_id,
        accepted_ownership_profile_version=source.ownership_profile.profile_version,
        accepted_projection_profile_id=source.projection_profile.profile_id,
        accepted_projection_profile_version=source.projection_profile.profile_version,
        accepted_segmentation_profile_id=source.segmentation_profile.profile_id,
        accepted_segmentation_profile_version=source.segmentation_profile.profile_version,
        allow_warnings=allow_warnings,
    )


class LxmlSelectionTests(unittest.TestCase):
    def test_parser_repaired_structure_is_rejected(self) -> None:
        malformed = "<html><body><article id=\"book\"><p>bad<div>nested</div></p></article></body></html>"
        selected = LxmlHtmlDocument().select(package(projection=False, html=malformed))
        self.assertEqual(selected.error.code, "malformed-source-html")

    def test_declared_selection_includes_attribute_excludes_application_and_never_infers_equal_text_projection(self) -> None:
        selected = LxmlHtmlDocument().select(package())
        self.assertIsNone(selected.error)
        values = {slot.location.slot: slot.text for slot in selected.slots}
        self.assertEqual(values["attribute:alt"], "Cover")
        self.assertNotIn("chrome", tuple(slot.text for slot in selected.slots if slot.eligibility is kernel.Eligibility.REQUIRED))
        self.assertEqual(next(slot.eligibility for slot in selected.slots if slot.text == "chrome"), kernel.Eligibility.EXCLUDED)

    def test_tail_is_owned_by_parent_and_required_override_below_excluded_is_rejected(self) -> None:
        html = "<html><body><article id=\"book\">lead <i>child</i> tail <span id=\"excluded\"><b id=\"required\">no</b></span></article></body></html>"
        tail_source = package(projection=False, html=html)
        tail_selected = LxmlHtmlDocument().select(tail_source)
        tail = next(slot for slot in tail_selected.slots if slot.text == " tail ")
        self.assertEqual(tail.location.path, ())
        self.assertEqual(tail.location.slot, "tail:0")
        source = package(projection=False, html=html).model_copy(update={"ownership_profile": kernel.OwnershipProfile(
            profile_id="component:ownership-fixture", profile_version="1", owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),),
            slot_rules=(
                kernel.SlotRule(element_id="excluded", disposition=kernel.SlotDisposition.EXCLUDED, reason="excluded"),
                kernel.SlotRule(element_id="required", disposition=kernel.SlotDisposition.REQUIRED, reason="invalid override"),
            ),
        )})
        selected = LxmlHtmlDocument().select(source)
        self.assertIsNotNone(selected.error)
        self.assertEqual(selected.error.code, "invalid-source-classification")

    def test_idless_or_unresolved_owned_roots_are_rejected(self) -> None:
        idless = package(projection=False, html="<html><body><article>book</article></body></html>")
        self.assertEqual(LxmlHtmlDocument().select(idless).error.code, "invalid-source-classification")
        unresolved = package(projection=False).model_copy(update={"ownership_profile": kernel.OwnershipProfile(
            profile_id="component:ownership-fixture", profile_version="1",
            owned_roots=(kernel.OwnedRoot(root_id="book", element_id="missing"),),
        )})
        self.assertEqual(LxmlHtmlDocument().select(unresolved).error.code, "invalid-source-classification")


class PrepareWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.store = FilesystemArtifactStore(Path(self.temp.name))
        self.workflow = PrepareWorkflow(store=self.store, document=LxmlHtmlDocument(), signer=HmacPackageSigner({"fixture-key": b"fixture-secret"}, active_key_ids=frozenset({"fixture-key"})))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_prepare_is_deterministic_and_uses_only_declared_projection_groups(self) -> None:
        first = self.workflow.prepare(run_id="run-a", source_package=package(), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(first.error)
        self.assertEqual(first.value.outcome.status, "ready-for-confirmation")
        self.assertEqual(len(first.value.manifest.projection_groups), 1)
        unprojected = next(unit for unit in first.value.manifest.units if unit.structural_location.path == (2,))
        self.assertIsNone(unprojected.projection_group_id)
        second = self.workflow.prepare(run_id="run-b", source_package=package(), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(second.error)
        self.assertEqual(kernel.canonical_bytes(first.value.manifest), kernel.canonical_bytes(second.value.manifest))
        self.assertEqual(kernel.canonical_bytes(first.value.package), kernel.canonical_bytes(second.value.package))

    def test_prepare_inventory_preserves_real_text_parent_tail_and_declared_attribute_slots(self) -> None:
        html = "<html><body><article id=\"book\">root<i id=\"child\">child</i> tail<img id=\"cover\" alt=\"Cover\"></article></body></html>"
        source = package(projection=False, html=html)
        selected = LxmlHtmlDocument().select(source)
        self.assertIsNone(selected.error)
        self.assertEqual(
            tuple((slot.location.path, slot.location.slot, slot.content_class, slot.text) for slot in selected.slots),
            (
                ((), "text", kernel.ContentClass.TEXT, "root"),
                ((0,), "text", kernel.ContentClass.TEXT, "child"),
                ((), "tail:0", kernel.ContentClass.TAIL, " tail"),
                ((1,), "attribute:alt", kernel.ContentClass.ATTRIBUTE, "Cover"),
            ),
        )
        prepared = self.workflow.prepare(run_id="run-slots", source_package=source, policy=policy(source), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(prepared.error)
        self.assertEqual(
            tuple((unit.structural_location.path, unit.structural_location.slot, unit.content_class, unit.source_text_digest) for unit in prepared.value.manifest.units),
            tuple((slot.location.path, slot.location.slot, slot.content_class, slot.text_digest) for slot in selected.slots),
        )

    def test_unsupported_or_empty_required_is_blocked_and_recorded(self) -> None:
        html = "<html><body><article id=\"book\"><p id=\"unsupported\">cannot translate</p></article></body></html>"
        source = package(projection=False, html=html).model_copy(update={"ownership_profile": kernel.OwnershipProfile(
            profile_id="component:ownership-fixture", profile_version="1", owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),),
            slot_rules=(kernel.SlotRule(element_id="unsupported", disposition=kernel.SlotDisposition.UNSUPPORTED, reason="fixture unsupported"),),
        )})
        result = self.workflow.prepare(run_id="run-blocked", source_package=source, policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(result.error)
        self.assertEqual(result.value.outcome.status, "blocked")
        self.assertIsNone(result.value.outcome.package_digest)
        self.assertTrue(self.store._latest_receipt("run-blocked", None))

    def test_converter_omissions_and_unconfirmed_or_nonrequired_editorial_scopes_fail_closed(self) -> None:
        omitted = package(projection=False).model_copy(update={"converter_findings": (
            kernel.PreparationFinding(code="book-owned-omission", severity="blocking-error", subject="converter", observed="one omitted book location", next_action="repair converter"),
        )})
        blocked = self.workflow.prepare(run_id="run-omission", source_package=omitted, policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertEqual(blocked.value.outcome.status, "blocked")
        draft_sheets = (sheets()[0].model_copy(update={"state": kernel.EditorialSheetState.DRAFT}), sheets()[1])
        unconfirmed = self.workflow.prepare(run_id="run-sheets", source_package=package(projection=False), policy=policy(), sheets=draft_sheets, run_snapshot_digest=RUN_DIGEST)
        self.assertEqual(unconfirmed.error.code, "editorial-sheet-unconfirmed")

    def test_allowed_warnings_are_signed_findings_and_disallowed_warnings_block(self) -> None:
        warning = kernel.PreparationFinding(code="converter-warning", severity="warning", subject="converter", observed="advisory", next_action="inspect")
        source = package(projection=False).model_copy(update={"converter_findings": (warning,)})
        allowed = self.workflow.prepare(run_id="run-warning", source_package=source, policy=policy(source, allow_warnings=True), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(allowed.error)
        self.assertEqual(allowed.value.outcome.findings, (warning,))
        persisted = self.store.read_object(allowed.value.package.findings_digest, kernel.PreparationFindings)
        self.assertEqual(persisted.value.findings, (warning,))
        self.assertIsNone(self.workflow.confirm(package_digest=allowed.value.outcome.package_digest, requested_key_id="fixture-key", operator_id="operator").error)
        blocked = self.workflow.prepare(run_id="run-warning-blocked", source_package=source, policy=policy(source), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertIsNone(blocked.error)
        self.assertEqual(blocked.value.outcome.status, "blocked")
        self.assertEqual(blocked.value.outcome.findings, (warning,))

    def test_profile_incompatibility_fails_before_parsing_and_profile_version_separates_prior_identity_domain(self) -> None:
        source = package(projection=False)
        incompatible = policy(source).model_copy(update={"accepted_ownership_profile_version": "2"})
        rejected = self.workflow.prepare(run_id="run-incompatible", source_package=source, policy=incompatible, sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        self.assertEqual(rejected.error.code, "profile-incompatible")
        first = self.workflow.prepare(run_id="run-profile-first", source_package=source, policy=policy(source), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        changed_html = source.source_html.replace("same", "changed", 1)
        changed = source.model_copy(update={
            "source_html": changed_html,
            "source_html_digest": kernel.sha256_digest(changed_html.encode()),
            "segmentation_profile": source.segmentation_profile.model_copy(update={"profile_version": "2"}),
        })
        second = self.workflow.prepare(run_id="run-profile-second", source_package=changed, policy=policy(changed), sheets=sheets(), run_snapshot_digest=RUN_DIGEST, prior_manifest=first.value.manifest)
        self.assertIsNone(second.error)
        self.assertEqual(second.value.outcome.status, "ready-for-confirmation")

    def test_prior_identity_text_change_is_terminal(self) -> None:
        first = self.workflow.prepare(run_id="run-first", source_package=package(projection=False), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        changed_html = "<html><body><article id=\"book\"><p id=\"one\">changed</p><p id=\"two\">same</p><p id=\"three\">same</p><img id=\"cover\" alt=\"Cover\"><aside id=\"app\" data-librarianlm-owned=\"application\">chrome</aside></article></body></html>"
        result = self.workflow.prepare(run_id="run-changed", source_package=package(projection=False, html=changed_html), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST, prior_manifest=first.value.manifest)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "source-text-digest-mismatch")

    def test_confirmation_recomputes_graph_and_returns_detached_signature_and_receipt(self) -> None:
        prepared = self.workflow.prepare(run_id="run-confirm", source_package=package(), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        result = self.workflow.confirm(package_digest=prepared.value.outcome.package_digest, requested_key_id="fixture-key", operator_id="operator")
        self.assertIsNone(result.error)
        self.assertEqual(result.signature.package_digest, prepared.value.outcome.package_digest)
        self.assertNotEqual(result.receipt.signature_digest, prepared.value.outcome.package_digest)
        revoked = PrepareWorkflow(store=self.store, document=LxmlHtmlDocument(), signer=HmacPackageSigner({"fixture-key": b"fixture-secret"}, active_key_ids=frozenset({"fixture-key"}), revoked_key_ids=frozenset({"fixture-key"})))
        rejected = revoked.confirm(package_digest=prepared.value.outcome.package_digest, requested_key_id="fixture-key", operator_id="operator")
        self.assertEqual(rejected.error.code, "signing-key-revoked")

    def test_confirmation_rejects_fabricated_persisted_manifest(self) -> None:
        prepared = self.workflow.prepare(run_id="run-tamper", source_package=package(), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        original = prepared.value.manifest
        altered_unit = original.units[0].model_copy(update={"structural_fingerprint": f"structural-fingerprint:{'b' * 64}"})
        fabricated_manifest = original.model_copy(update={"units": (altered_unit,) + original.units[1:]})
        fabricated_manifest_digest = self.store.put_object(fabricated_manifest).digest
        fabricated_package = prepared.value.package.model_copy(update={"manifest_digest": fabricated_manifest_digest})
        fabricated_package_digest = self.store.put_object(fabricated_package).digest
        rejected = self.workflow.confirm(package_digest=fabricated_package_digest, requested_key_id="fixture-key", operator_id="operator")
        self.assertEqual(rejected.error.code, "prepared-artifact-drift")

    def test_confirmation_rejects_declared_projection_member_tampering(self) -> None:
        prepared = self.workflow.prepare(run_id="run-projection-tamper", source_package=package(), policy=policy(), sheets=sheets(), run_snapshot_digest=RUN_DIGEST)
        declared = prepared.value.package.projection_profile.projections[0]
        tampered_projection = prepared.value.package.projection_profile.model_copy(update={"projections": (
            declared.model_copy(update={"member_locations": (
                kernel.StructuralLocation(owned_root_id="book", path=(0,), slot="text"),
                kernel.StructuralLocation(owned_root_id="book", path=(2,), slot="text"),
            )}),
        )})
        fabricated = prepared.value.package.model_copy(update={"projection_profile": tampered_projection})
        rejected = self.workflow.confirm(package_digest=self.store.put_object(fabricated).digest, requested_key_id="fixture-key", operator_id="operator")
        self.assertEqual(rejected.error.code, "prepared-artifact-drift")
