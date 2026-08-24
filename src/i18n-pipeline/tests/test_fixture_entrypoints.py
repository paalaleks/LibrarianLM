from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import inspect
from datetime import UTC, datetime
import unittest

from pydantic import ValidationError

from librarianlm_i18n import kernel
from librarianlm_i18n.adapters import FilesystemArtifactStore, HmacPackageSigner, LxmlHtmlDocument
from librarianlm_i18n.entrypoints import FixtureEntrypoints
from librarianlm_i18n.workflows import ASSEMBLE_VALIDATE_DECLARATION, AssembleValidateWorkflow, AssemblyWorkflow, Orchestrator, PrepareWorkflow, ValidationWorkflow


DIGEST = "a" * 64


def source() -> kernel.CanonicalSourcePackage:
    html = '<html lang="en" dir="ltr"><body><article id="book"><p id="one">hello</p></article></body></html>'
    identity = kernel.ComponentIdentity(
        implementation="component:fixture", implementation_version="1", platform_abi="fixture", uv_lock_digest=DIGEST,
        package_versions=(), lxml_version="6.1.2", libxml_version="fixture", libxslt_version="fixture",
        html_serialization_fixture_digest=DIGEST,
    )
    return kernel.CanonicalSourcePackage(
        source_html=html, source_html_digest=kernel.sha256_digest(html.encode()), converter_identity=identity,
        ownership_profile=kernel.OwnershipProfile(profile_id="component:ownership", profile_version="1", owned_roots=(kernel.OwnedRoot(root_id="book", element_id="book"),)),
        projection_profile=kernel.ProjectionProfile(profile_id="component:projection", profile_version="1"),
        segmentation_profile=kernel.SegmentationProfile(profile_id="component:segmentation", profile_version="1", rule="fixture-v1-one-unit-per-nonblank-slot"),
    )


def snapshot(run_id: str, *, blocked: bool = False, ceiling: int = 8) -> kernel.RunSnapshot:
    package = source()
    slot = LxmlHtmlDocument().select(package).slots[0]
    unit_id = kernel.derive_typed_id("source-unit", {
        "source_html_digest": package.source_html_digest, "location": slot.location.model_dump(mode="json"),
        "segmentation_profile": {"id": package.segmentation_profile.profile_id, "version": package.segmentation_profile.profile_version}, "ordinal": 0,
    })
    controls = kernel.ValidationControls(terminology=(
        kernel.TerminologyControl(rule_id="must-have", required_unit_ids=(unit_id,), required_terms=("required-term",)),
    )) if blocked else kernel.ValidationControls()
    policy = kernel.PreparePolicy(
        policy_id="component:policy", policy_version="1",
        accepted_ownership_profile_id=package.ownership_profile.profile_id, accepted_ownership_profile_version=package.ownership_profile.profile_version,
        accepted_projection_profile_id=package.projection_profile.profile_id, accepted_projection_profile_version=package.projection_profile.profile_version,
        accepted_segmentation_profile_id=package.segmentation_profile.profile_id, accepted_segmentation_profile_version=package.segmentation_profile.profile_version, validation_controls=controls,
    )
    return kernel.RunSnapshot(
        run_id=run_id, fixture_mode=kernel.FixtureMode.FIXTURE, source_package=package, prepare_policy=policy,
        editorial_sheets=(
            kernel.EditorialSheet(kind=kernel.EditorialSheetKind.TERMINOLOGY, state=kernel.EditorialSheetState.CONFIRMED),
            kernel.EditorialSheet(kind=kernel.EditorialSheetKind.STYLE, state=kernel.EditorialSheetState.CONFIRMED),
        ),
        validation_controls=controls, component_identities=(package.converter_identity,),
        fixture_targets=kernel.FixtureTargets(targets=(kernel.FixtureTarget(source_unit_id=unit_id, value="hei"),)),
        attempt_ceiling=ceiling,
    )


class FixtureEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.store = FilesystemArtifactStore(Path(self.temp.name))
        self.entrypoints = self._new_entrypoints()

    def _new_entrypoints(self) -> FixtureEntrypoints:
        signer = HmacPackageSigner({"fixture-key": b"fixture-secret", "fixture-key-two": b"fixture-secret-two"}, active_key_ids=frozenset({"fixture-key", "fixture-key-two"}))
        document = LxmlHtmlDocument()
        prepare = PrepareWorkflow(store=self.store, document=document, signer=signer)
        composed = AssembleValidateWorkflow(
            store=self.store,
            assembly=AssemblyWorkflow(store=self.store, document=document, signer=signer),
            validation=ValidationWorkflow(store=self.store, document=document, signer=signer),
        )
        return FixtureEntrypoints(store=self.store, prepare=prepare, assemble_validate=composed, orchestrator=Orchestrator(store=self.store, assemble_validate=composed))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _materialized_receipt(self, run_id: str, snapshot_digest: str, attempt: int, predecessor: str | None = None) -> kernel.InvocationReceipt:
        reference = kernel.ArtifactReference(kind="unit-manifest", digest="a" * 64)
        terminal = kernel.InvocationTerminalResult(
            outcome=kernel.OperationalOutcome.COMPLETED, recoverable=False, references=(reference,), retry_guidance="fixture",
        )
        now = datetime.now(UTC)
        return kernel.InvocationReceipt(
            run_id=run_id, workflow_id="fixture-history", declaration_digest="b" * 64, snapshot_digest=snapshot_digest,
            input_digests=("c" * 64,), output_references=(reference,), attempt=attempt, attempt_ceiling=8,
            started_at=now, completed_at=now, finding_count=0, terminal=terminal, predecessor_receipt_digest=predecessor,
        )

    def test_prepare_confirm_orchestrate_and_resume_are_durable_and_gateway_free(self) -> None:
        frozen = snapshot("run-entrypoint", ceiling=4)
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=frozen, operator_authorized=True).model_dump(mode="python"))
        self.assertIsNone(prepared.error)
        self.assertEqual(prepared.value.outcome, kernel.OperationalOutcome.COMPLETED)
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        reconstructed = self._new_entrypoints()
        re_prepared = reconstructed.prepare(kernel.PrepareInvocation(snapshot=frozen, operator_authorized=True).model_dump(mode="python"))
        self.assertEqual(re_prepared.value, prepared.value)
        confirmed = reconstructed.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(confirmed.error)
        reconstructed = self._new_entrypoints()
        self.assertEqual(reconstructed.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python")).value, confirmed.value)
        confirmation_digest = {reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"]
        confirmation = self.store.read_object(confirmation_digest, kernel.ConfirmationReceipt).value
        completed = reconstructed.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(completed.error)
        self.assertEqual(completed.value.outcome, kernel.OperationalOutcome.COMPLETED)
        outputs = {reference.kind for reference in completed.value.references}
        self.assertEqual(outputs, {"unit-manifest", "candidate-draft", "assembly-report", "validation-report", "translation-draft", "translation-run-summary"})
        resumed = reconstructed.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertEqual(resumed.value, completed.value)
        self.assertEqual(len(self.store.recover_invocation_receipts("run-entrypoint").receipts), 4)
        before = len(self.store.recover_invocation_receipts("run-entrypoint").receipts)
        direct_repeat = reconstructed.assemble_and_validate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertEqual(direct_repeat.value, completed.value)
        self.assertEqual(len(self.store.recover_invocation_receipts("run-entrypoint").receipts), before)
        self.assertEqual(tuple(declaration.workflow_id for declaration in reconstructed.declarations), ("fixture-prepare", "fixture-confirm", "fixture-assemble-validate", "fixture-orchestrate"))
        self.assertNotIn("Gateway", inspect.getsource(AssembleValidateWorkflow))

    def test_hostile_input_and_missing_operator_authorization_are_typed_failures(self) -> None:
        hostile = self.entrypoints.prepare('{"snapshot": 1, "extra": true}')
        self.assertIsNotNone(hostile.error)
        denied = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-denied"), operator_authorized=False).model_dump(mode="python"))
        self.assertIsNone(denied.error)
        self.assertEqual(denied.value.outcome, kernel.OperationalOutcome.TERMINAL_FAILURE)
        self.assertEqual(denied.value.error.code, "operator-authorization-required")

    def test_genuinely_blocked_prepare_is_truthful_and_durably_recorded(self) -> None:
        frozen = snapshot("run-prepare-blocked")
        blocked_source = frozen.source_package.model_copy(update={
            "converter_findings": (
                kernel.PreparationFinding(
                    code="book-owned-omission", severity="blocking-error", subject="converter",
                    observed="a book-owned source location was omitted", next_action="repair converter output",
                ),
            ),
        })
        blocked_snapshot = frozen.model_copy(update={"source_package": blocked_source})
        result = self.entrypoints.prepare(kernel.PrepareInvocation(
            snapshot=blocked_snapshot, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(result.error)
        self.assertEqual(result.value.outcome, kernel.OperationalOutcome.RECONCILIATION_REQUIRED)
        self.assertEqual(result.value.error.code, "prepare-blocked")
        self.assertEqual(result.value.references, ())
        history = self.store.recover_invocation_receipts("run-prepare-blocked")
        self.assertIsNone(history.error)
        self.assertEqual(len(history.receipts), 1)
        self.assertEqual(history.receipts[0].workflow_id, "fixture-prepare")
        self.assertEqual(history.receipts[0].terminal, result.value)
        repeated = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=blocked_snapshot, operator_authorized=True).model_dump(mode="python"))
        self.assertEqual(repeated.value, result.value)
        self.assertEqual(len(self.store.recover_invocation_receipts("run-prepare-blocked").receipts), 1)

    def test_blocking_validation_keeps_reports_but_never_emits_an_eligible_draft(self) -> None:
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-blocked", blocked=True), operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        confirmed = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        confirmation = self.store.read_object({reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        result = self.entrypoints.assemble_and_validate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(result.error)
        self.assertEqual(result.value.outcome, kernel.OperationalOutcome.RECONCILIATION_REQUIRED)
        kinds = {reference.kind for reference in result.value.references}
        self.assertTrue({"assembly-report", "validation-report", "translation-run-summary"}.issubset(kinds))
        self.assertNotIn("translation-draft", kinds)

    def test_snapshot_and_terminal_contracts_reject_cross_wiring(self) -> None:
        frozen = snapshot("run-contract")
        with self.assertRaises(ValidationError):
            frozen.model_copy(update={"validation_controls": kernel.ValidationControls(accessibility_required=True)}).model_validate({
                **frozen.model_dump(mode="python"), "validation_controls": kernel.ValidationControls(accessibility_required=True),
                "prepare_policy": frozen.prepare_policy.model_copy(update={"validation_controls": kernel.ValidationControls(terminology=(kernel.TerminologyControl(rule_id="other", required_terms=("x",)),))}),
            })
        with self.assertRaises(ValidationError):
            kernel.InvocationTerminalResult(
                outcome=kernel.OperationalOutcome.COMPLETED, recoverable=False,
                error=kernel.ActionableError(code="bad", workflow="test", subject="test", rule="test", expected="none", observed="error", retryability=kernel.Retryability.NOT_RETRYABLE, next_action="fix"),
                retry_guidance="fix",
            )
        with self.assertRaises(ValidationError):
            kernel.InvocationTerminalResult(
                outcome=kernel.OperationalOutcome.COMPLETED, recoverable=False,
                references=(
                    kernel.ArtifactReference(kind="unit-manifest", digest="a" * 64),
                    kernel.ArtifactReference(kind="unit-manifest", digest="b" * 64),
                ), retry_guidance="fix",
            )
        with self.assertRaises(ValidationError):
            kernel.InvocationReceipt(
                run_id="run", workflow_id="fixture", declaration_digest="a" * 64, snapshot_digest="b" * 64,
                input_digests=(), output_references=(kernel.ArtifactReference(kind="unit-manifest", digest="a" * 64),),
                attempt=1, attempt_ceiling=1, started_at=datetime.now(UTC), completed_at=datetime.now(UTC), finding_count=0,
                terminal=kernel.InvocationTerminalResult(outcome=kernel.OperationalOutcome.COMPLETED, recoverable=False, references=(kernel.ArtifactReference(kind="unit-manifest", digest="a" * 64),), retry_guidance="done"),
            )

    def test_confirmation_reuse_binds_the_operator_and_key_request(self) -> None:
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-confirmation-inputs"), operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        first = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="one", operator_authorized=True,
        ).model_dump(mode="python"))
        second = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key-two", operator_id="two", operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(second.error)
        self.assertNotEqual(first.value.references, second.value.references)

    def test_corrupt_invocation_chain_and_exhausted_ceiling_stop_before_feature_execution(self) -> None:
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-corrupt"), operator_authorized=True).model_dump(mode="python"))
        invocation_path = next((Path(self.temp.name) / "runs" / "run-corrupt" / "invocations").glob("*.json"))
        invocation_path.write_bytes(b"{}")
        self.assertEqual(self.store.recover_invocation_receipts("run-corrupt").error.code, "invocation-recovery-invalid")

        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-ceiling", ceiling=2), operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        confirmed = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        confirmation = self.store.read_object({reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        stopped = self.entrypoints.assemble_and_validate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(stopped.error)
        self.assertEqual(stopped.value.error.code, "attempt-ceiling-exhausted")
        self.assertFalse(any(reference.kind == "candidate-draft" for reference in stopped.value.references))

    def test_orchestration_stops_on_cross_wiring_or_corrupt_recovered_history(self) -> None:
        first = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-a"), operator_authorized=True).model_dump(mode="python"))
        second = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-b"), operator_authorized=True).model_dump(mode="python"))
        first_refs = {reference.kind: reference.digest for reference in first.value.references}
        second_refs = {reference.kind: reference.digest for reference in second.value.references}
        confirmation = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=first_refs["run-snapshot"], package_digest=first_refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        receipt = self.store.read_object({reference.kind: reference.digest for reference in confirmation.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        cross_wired = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=second_refs["run-snapshot"], package_digest=second_refs["prepare-package"], confirmation=receipt, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(cross_wired.error)
        self.assertEqual(cross_wired.value.error.code, "confirmation-package-mismatch")

        operational = next((Path(self.temp.name) / "runs" / "run-a" / "receipts").glob("*.json"))
        operational.write_bytes(b"{}")
        blocked = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=first_refs["run-snapshot"], package_digest=first_refs["prepare-package"], confirmation=receipt, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(blocked.error)
        self.assertEqual(blocked.value.error.code, "recovery-invalid")

        # A distinct valid run demonstrates invocation corruption through the
        # public orchestrator rather than only the store adapter.
        third = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-c"), operator_authorized=True).model_dump(mode="python"))
        third_refs = {reference.kind: reference.digest for reference in third.value.references}
        third_confirmation = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=third_refs["run-snapshot"], package_digest=third_refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        third_receipt = self.store.read_object({reference.kind: reference.digest for reference in third_confirmation.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        invocation = next((Path(self.temp.name) / "runs" / "run-c" / "invocations").glob("*.json"))
        invocation.write_bytes(b"{}")
        invalid_history = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=third_refs["run-snapshot"], package_digest=third_refs["prepare-package"], confirmation=third_receipt, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(invalid_history.error)
        self.assertEqual(invalid_history.value.error.code, "invocation-recovery-invalid")

    def test_reuse_rejects_a_kind_forged_output_reference(self) -> None:
        frozen = snapshot("run-kind-forged")
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=frozen, operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        confirmed = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        confirmation = self.store.read_object({reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        completed = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertEqual(completed.value.outcome, kernel.OperationalOutcome.COMPLETED)
        history = self.store.recover_invocation_receipts("run-kind-forged").receipts
        prior = history[-1]
        forged_reference = kernel.ArtifactReference(kind="unit-manifest", digest=refs["run-snapshot"])
        forged_terminal = kernel.InvocationTerminalResult(
            outcome=kernel.OperationalOutcome.COMPLETED, recoverable=False, references=(forged_reference,), retry_guidance="forged",
        )
        forged = kernel.InvocationReceipt(
            run_id="run-kind-forged", workflow_id=ASSEMBLE_VALIDATE_DECLARATION.workflow_id,
            declaration_digest=kernel.sha256_digest(kernel.canonical_bytes(ASSEMBLE_VALIDATE_DECLARATION)),
            snapshot_digest=refs["run-snapshot"],
            input_digests=(refs["run-snapshot"], refs["prepare-package"], kernel.sha256_digest(kernel.canonical_bytes(confirmation))),
            output_references=(forged_reference,), attempt=prior.attempt + 1, attempt_ceiling=frozen.attempt_ceiling,
            started_at=datetime.now(UTC), completed_at=datetime.now(UTC), finding_count=0, terminal=forged_terminal,
            predecessor_receipt_digest=kernel.sha256_digest(kernel.canonical_bytes(prior)),
        )
        self.assertIsNone(self.store.append_invocation_receipt(forged).error)
        rejected = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True,
        ).model_dump(mode="python"))
        self.assertIsNone(rejected.error)
        self.assertEqual(rejected.value.error.code, "completed-output-set-invalid")

    def test_forged_persisted_confirmation_signature_blocks_execution_and_reuse(self) -> None:
        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-forged-confirm"), operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        confirmed = self.entrypoints.confirm(kernel.ConfirmationInvocation(
            snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True,
        ).model_dump(mode="python"))
        receipt = self.store.read_object({reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        signature = self.store.read_object(receipt.signature_digest, kernel.SignatureRecord).value
        forged_signature = signature.model_copy(update={"signature": "forged"})
        forged_signature_digest = self.store.put_object(forged_signature).digest
        forged_receipt = receipt.model_copy(update={"signature_digest": forged_signature_digest})
        self.store.put_object(forged_receipt)
        invocation = kernel.AssembleValidateInvocation(snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=forged_receipt, operator_authorized=True).model_dump(mode="python")
        direct = self.entrypoints.assemble_and_validate(invocation)
        self.assertEqual(direct.value.error.code, "signature-invalid")
        cached = self.entrypoints.orchestrate(invocation)
        self.assertEqual(cached.value.error.code, "signature-invalid")

    def test_materialized_valid_receipt_history_shapes_fail_recovery_and_orchestration(self) -> None:
        root = Path(self.temp.name)
        non_genesis = self._materialized_receipt("run-non-genesis", "d" * 64, 2)
        self.store._write_invocation_receipt(non_genesis)
        self.assertEqual(self.store.recover_invocation_receipts("run-non-genesis").error.code, "invocation-recovery-invalid")

        first = self._materialized_receipt("run-two-genesis", "d" * 64, 1)
        second = self._materialized_receipt("run-two-genesis", "d" * 64, 1)
        # Make the second otherwise-valid canonical object distinct.
        second = second.model_copy(update={"declaration_digest": "e" * 64})
        self.store._write_invocation_receipt(first)
        self.store._write_invocation_receipt(second)
        self.assertEqual(self.store.recover_invocation_receipts("run-two-genesis").error.code, "invocation-recovery-invalid")

        genesis = self._materialized_receipt("run-fork", "d" * 64, 1)
        genesis_digest = self.store._write_invocation_receipt(genesis)
        self.store._write_invocation_receipt(self._materialized_receipt("run-fork", "d" * 64, 2, genesis_digest))
        fork = self._materialized_receipt("run-fork", "d" * 64, 2, genesis_digest).model_copy(update={"declaration_digest": "e" * 64})
        self.store._write_invocation_receipt(fork)
        self.assertEqual(self.store.recover_invocation_receipts("run-fork").error.code, "invocation-recovery-invalid")

        changed = self._materialized_receipt("run-snapshot-change", "d" * 64, 1)
        changed_digest = self.store._write_invocation_receipt(changed)
        self.store._write_invocation_receipt(self._materialized_receipt("run-snapshot-change", "e" * 64, 2, changed_digest))
        self.assertEqual(self.store.recover_invocation_receipts("run-snapshot-change").error.code, "invocation-recovery-invalid")

        prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot("run-public-fork"), operator_authorized=True).model_dump(mode="python"))
        refs = {reference.kind: reference.digest for reference in prepared.value.references}
        confirmed = self.entrypoints.confirm(kernel.ConfirmationInvocation(snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True).model_dump(mode="python"))
        confirmation = self.store.read_object({reference.kind: reference.digest for reference in confirmed.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
        history = self.store.recover_invocation_receipts("run-public-fork").receipts
        predecessor = kernel.sha256_digest(kernel.canonical_bytes(history[-1]))
        for declaration in ("d" * 64, "e" * 64):
            forged = self._materialized_receipt("run-public-fork", refs["run-snapshot"], 3, predecessor).model_copy(update={"declaration_digest": declaration})
            self.store._write_invocation_receipt(forged)
        stopped = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True).model_dump(mode="python"))
        self.assertEqual(stopped.value.error.code, "invocation-recovery-invalid")

    def test_exact_completed_inventory_rejects_same_schema_cross_run_lineage(self) -> None:
        def completed(run_id: str):
            prepared = self.entrypoints.prepare(kernel.PrepareInvocation(snapshot=snapshot(run_id), operator_authorized=True).model_dump(mode="python"))
            refs = {reference.kind: reference.digest for reference in prepared.value.references}
            confirmation_result = self.entrypoints.confirm(kernel.ConfirmationInvocation(snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], requested_key_id="fixture-key", operator_id="operator", operator_authorized=True).model_dump(mode="python"))
            confirmation = self.store.read_object({reference.kind: reference.digest for reference in confirmation_result.value.references}["confirmation-receipt"], kernel.ConfirmationReceipt).value
            result = self.entrypoints.orchestrate(kernel.AssembleValidateInvocation(snapshot_digest=refs["run-snapshot"], package_digest=refs["prepare-package"], confirmation=confirmation, operator_authorized=True).model_dump(mode="python"))
            return refs, confirmation, result.value
        left_refs, left_confirmation, left = completed("run-lineage-left")
        _, _, right = completed("run-lineage-right")
        history = self.store.recover_invocation_receipts("run-lineage-left").receipts
        prior = history[-1]
        forged = kernel.InvocationReceipt(
            run_id="run-lineage-left", workflow_id=ASSEMBLE_VALIDATE_DECLARATION.workflow_id,
            declaration_digest=kernel.sha256_digest(kernel.canonical_bytes(ASSEMBLE_VALIDATE_DECLARATION)), snapshot_digest=left_refs["run-snapshot"],
            input_digests=(left_refs["run-snapshot"], left_refs["prepare-package"], kernel.sha256_digest(kernel.canonical_bytes(left_confirmation))),
            output_references=right.references, attempt=prior.attempt + 1, attempt_ceiling=8, started_at=datetime.now(UTC), completed_at=datetime.now(UTC), finding_count=0,
            terminal=right, predecessor_receipt_digest=kernel.sha256_digest(kernel.canonical_bytes(prior)),
        )
        self.assertIsNone(self.store.append_invocation_receipt(forged).error)
        rejected = self.entrypoints.assemble_and_validate(kernel.AssembleValidateInvocation(snapshot_digest=left_refs["run-snapshot"], package_digest=left_refs["prepare-package"], confirmation=left_confirmation, operator_authorized=True).model_dump(mode="python"))
        self.assertEqual(rejected.value.error.code, "completed-output-lineage-invalid")
