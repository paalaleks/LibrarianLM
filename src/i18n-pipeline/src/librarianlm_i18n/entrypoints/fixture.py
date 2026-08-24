"""Thin raw-input boundaries; all feature behavior remains in workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

from librarianlm_i18n.kernel.boundary import BoundaryExecutionResult, run_boundary
from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    ArtifactReference,
    CompatibilityMetadata,
    ConfirmationInvocation,
    ConfirmationReceipt,
    InvocationReceipt,
    InvocationTerminalResult,
    OperationalOutcome,
    PrepareInvocation,
    PreparePackage,
    RunSnapshot,
    WorkflowDeclaration,
)
from librarianlm_i18n.kernel.errors import Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from librarianlm_i18n.workflows.assemble_validate import ASSEMBLE_VALIDATE_DECLARATION, AssembleValidateWorkflow
from librarianlm_i18n.workflows.orchestrate import ORCHESTRATE_DECLARATION, Orchestrator
from librarianlm_i18n.workflows.prepare import PrepareWorkflow
from librarianlm_i18n.workflows.references import verify_output_reference


PREPARE_DECLARATION = WorkflowDeclaration(
    workflow_id="fixture-prepare",
    purpose="Freeze a fixture Run Snapshot and produce a package eligible for detached confirmation.",
    input_contracts=(CompatibilityMetadata(contract_name="PrepareInvocation", accepted_versions=(1,)),),
    output_kinds=("run-snapshot", "unit-manifest", "prepare-package"),
    preconditions=("strict raw invocation", "explicit fixture mode", "explicit operator authorization"),
    confirmation_required=True,
    retry_policy="Append a receipt and respect the snapshot's frozen attempt ceiling.",
    failure_policy="Return blocked preparation truthfully and never imply confirmation.",
    terminal_outcomes=(OperationalOutcome.COMPLETED, OperationalOutcome.RETRYABLE_FAILURE, OperationalOutcome.TERMINAL_FAILURE, OperationalOutcome.RECONCILIATION_REQUIRED),
)

CONFIRM_DECLARATION = WorkflowDeclaration(
    workflow_id="fixture-confirm",
    purpose="Create a detached operator confirmation for one verified prepared package.",
    input_contracts=(CompatibilityMetadata(contract_name="ConfirmationInvocation", accepted_versions=(1,)),),
    output_kinds=("prepare-package", "signature", "confirmation-receipt"),
    preconditions=("persisted snapshot", "ready package bound to that snapshot", "explicit operator authorization"),
    confirmation_required=True,
    retry_policy="Append a receipt and never infer an operator decision.",
    failure_policy="Return a typed error without signing or advancing a manifest.",
    terminal_outcomes=(OperationalOutcome.COMPLETED, OperationalOutcome.RETRYABLE_FAILURE, OperationalOutcome.TERMINAL_FAILURE),
)


class FixtureEntrypoints:
    """The public Python surface.  It never exposes parsing or workflow exceptions."""

    def __init__(self, *, store: ArtifactStore, prepare: PrepareWorkflow, assemble_validate: AssembleValidateWorkflow, orchestrator: Orchestrator) -> None:
        self._store = store
        self._prepare = prepare
        self._assemble_validate = assemble_validate
        self._orchestrator = orchestrator

    @property
    def declarations(self) -> tuple[WorkflowDeclaration, ...]:
        """Inspectable contract metadata for every independently invocable boundary."""

        return (PREPARE_DECLARATION, CONFIRM_DECLARATION, ASSEMBLE_VALIDATE_DECLARATION, ORCHESTRATE_DECLARATION)

    def prepare(self, raw: str | bytes | bytearray | Mapping[str, Any] | None) -> BoundaryExecutionResult[InvocationTerminalResult]:
        return run_boundary(raw, PrepareInvocation, self._prepare_invocation, workflow="fixture-prepare", subject="prepare-invocation")

    def confirm(self, raw: str | bytes | bytearray | Mapping[str, Any] | None) -> BoundaryExecutionResult[InvocationTerminalResult]:
        return run_boundary(raw, ConfirmationInvocation, self._confirm_invocation, workflow="fixture-confirm", subject="confirmation-invocation")

    def assemble_and_validate(self, raw: str | bytes | bytearray | Mapping[str, Any] | None) -> BoundaryExecutionResult[InvocationTerminalResult]:
        from librarianlm_i18n.kernel.contracts import AssembleValidateInvocation
        return run_boundary(raw, AssembleValidateInvocation, self._assemble_validate.run, workflow="fixture-assemble-validate", subject="assemble-validate-invocation")

    def orchestrate(self, raw: str | bytes | bytearray | Mapping[str, Any] | None) -> BoundaryExecutionResult[InvocationTerminalResult]:
        from librarianlm_i18n.kernel.contracts import AssembleValidateInvocation
        return run_boundary(raw, AssembleValidateInvocation, self._orchestrator.resume, workflow="fixture-orchestrate", subject="orchestration-invocation")

    def _prepare_invocation(self, invocation: PrepareInvocation) -> InvocationTerminalResult:
        started = datetime.now(UTC)
        snapshot = invocation.snapshot
        persisted = self._store.put_object(snapshot)
        if persisted.error is not None or persisted.digest is None:
            return self._failure(persisted.error, "snapshot-persistence-failed")
        reused = self._completed_reuse(snapshot, PREPARE_DECLARATION, (persisted.digest,))
        if reused is not None:
            return reused
        exhausted = self._ceiling_exhausted(snapshot)
        if exhausted is not None:
            return exhausted
        if not invocation.operator_authorized:
            return self._record(snapshot, PREPARE_DECLARATION, (persisted.digest,), started, self._terminal_error("operator-authorization-required", "operator authorization", "missing"))
        attempt, prior_manifest, retry_error = self._prepare_retry_state(snapshot)
        if retry_error is not None:
            return self._record(snapshot, PREPARE_DECLARATION, (persisted.digest,), started, retry_error)
        result = self._prepare.prepare(
            run_id=snapshot.run_id,
            source_package=snapshot.source_package,
            policy=snapshot.prepare_policy,
            sheets=snapshot.editorial_sheets,
            run_snapshot_digest=persisted.digest,
            prior_manifest=prior_manifest,
            attempt=attempt,
            attempt_ceiling=snapshot.attempt_ceiling,
        )
        if result.error is not None:
            return self._record(snapshot, PREPARE_DECLARATION, (persisted.digest,), started, self._terminal_from_error(result.error))
        if result.value.outcome.status == "blocked":
            terminal = InvocationTerminalResult(
                outcome=OperationalOutcome.RECONCILIATION_REQUIRED,
                recoverable=False,
                error=self._terminal_error("prepare-blocked", "eligible preparation", "blocking preparation findings").error,
                retry_guidance="Resolve preparation findings and start the next legal attempt.",
            )
            return self._record(snapshot, PREPARE_DECLARATION, (persisted.digest,), started, terminal, finding_count=len(result.value.outcome.findings))
        refs = (
            ArtifactReference(kind="run-snapshot", digest=persisted.digest),
            ArtifactReference(kind="unit-manifest", digest=result.value.outcome.manifest_digest),
            ArtifactReference(kind="prepare-package", digest=result.value.outcome.package_digest),
        )
        terminal = InvocationTerminalResult(outcome=OperationalOutcome.COMPLETED, recoverable=False, references=refs, status=result.value.manifest.status, retry_guidance="Obtain explicit detached operator confirmation before assembly.")
        return self._record(snapshot, PREPARE_DECLARATION, (persisted.digest,), started, terminal, finding_count=len(result.value.outcome.findings))

    def _confirm_invocation(self, invocation: ConfirmationInvocation) -> InvocationTerminalResult:
        started = datetime.now(UTC)
        snapshot = self._read_snapshot(invocation.snapshot_digest)
        if isinstance(snapshot, InvocationTerminalResult):
            return snapshot
        confirmation_inputs = self._confirmation_inputs(invocation)
        reused = self._completed_reuse(snapshot, CONFIRM_DECLARATION, confirmation_inputs)
        if reused is not None:
            return reused
        exhausted = self._ceiling_exhausted(snapshot)
        if exhausted is not None:
            return exhausted
        if not invocation.operator_authorized:
            return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, self._terminal_error("operator-authorization-required", "operator authorization", "missing"))
        package = self._store.read_object(invocation.package_digest, PreparePackage)
        if package.error is not None or package.value is None:
            return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, self._failure(package.error, "prepare-package-unavailable"))
        if package.value.run_snapshot_digest != invocation.snapshot_digest:
            return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, self._terminal_error("snapshot-package-mismatch", invocation.snapshot_digest, package.value.run_snapshot_digest))
        confirmed = self._prepare.confirm(package_digest=invocation.package_digest, requested_key_id=invocation.requested_key_id, operator_id=invocation.operator_id)
        if confirmed.error is not None:
            return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, self._terminal_from_error(confirmed.error))
        signature_digest = sha256_digest(canonical_bytes(confirmed.signature))
        receipt_digest = sha256_digest(canonical_bytes(confirmed.receipt))
        persisted_signature = self._store.read_object(signature_digest, type(confirmed.signature))
        persisted_receipt = self._store.read_object(receipt_digest, ConfirmationReceipt)
        if persisted_signature.error is not None or persisted_signature.value != confirmed.signature or persisted_receipt.error is not None or persisted_receipt.value != confirmed.receipt:
            return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, self._failure(persisted_signature.error or persisted_receipt.error, "confirmation-persistence-failed"))
        terminal = InvocationTerminalResult(
            outcome=OperationalOutcome.COMPLETED,
            recoverable=False,
            references=(
                ArtifactReference(kind="prepare-package", digest=invocation.package_digest),
                ArtifactReference(kind="signature", digest=signature_digest),
                ArtifactReference(kind="confirmation-receipt", digest=receipt_digest),
            ),
            retry_guidance="The confirmation is detached; pass it unchanged to orchestration.",
        )
        return self._record(snapshot, CONFIRM_DECLARATION, confirmation_inputs, started, terminal)

    def _read_snapshot(self, digest: str) -> RunSnapshot | InvocationTerminalResult:
        result = self._store.read_object(digest, RunSnapshot)
        if result.error is not None or result.value is None:
            return self._failure(result.error, "snapshot-unavailable")
        return result.value

    @staticmethod
    def _confirmation_inputs(invocation: ConfirmationInvocation) -> tuple[str, str, str]:
        return (invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation)))

    def _completed_reuse(self, snapshot: RunSnapshot, declaration: WorkflowDeclaration, inputs: tuple[str, ...]) -> InvocationTerminalResult | None:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._failure(history.error, "invocation-history-invalid")
        declaration_digest = sha256_digest(canonical_bytes(declaration))
        snapshot_digest = sha256_digest(canonical_bytes(snapshot))
        for receipt in reversed(history.receipts):
            if receipt.workflow_id != declaration.workflow_id or receipt.declaration_digest != declaration_digest or receipt.snapshot_digest != snapshot_digest or receipt.input_digests != inputs:
                continue
            if receipt.terminal.outcome is not OperationalOutcome.COMPLETED:
                return receipt.terminal if not receipt.terminal.recoverable else None
            if {reference.kind for reference in receipt.output_references} != set(declaration.output_kinds):
                return self._terminal_error("completed-output-set-invalid", repr(tuple(declaration.output_kinds)), repr(tuple(reference.kind for reference in receipt.output_references)))
            for reference in receipt.output_references:
                error = verify_output_reference(self._store, reference, workflow="fixture-entrypoint")
                if error is not None:
                    return self._terminal_from_error(error)
            return receipt.terminal
        return None

    def _prepare_retry_state(self, snapshot: RunSnapshot):
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return 1, None, self._failure(history.error, "invocation-history-invalid")
        attempt = 1 if not history.receipts else history.receipts[-1].attempt + 1
        recovered = self._store.recover(snapshot.run_id)
        if recovered.error is not None:
            if recovered.error.code == "recovery-not-found":
                # No Story 1.2 receipt exists yet, so its independent chain
                # must still begin at attempt one even if invocation history
                # contains a retryable boundary failure.
                return 1, None, None
            return attempt, None, self._failure(recovered.error, "operational-recovery-invalid")
        if recovered.manifest is None or recovered.manifest.run_snapshot_digest != sha256_digest(canonical_bytes(snapshot)):
            return attempt, None, self._terminal_error("recovered-lineage-mismatch", sha256_digest(canonical_bytes(snapshot)), "missing or cross-wired manifest")
        operational_attempt = max((receipt.attempt for receipt in recovered.receipts), default=0)
        return max(attempt, operational_attempt + 1), recovered.manifest, None

    def _ceiling_exhausted(self, snapshot: RunSnapshot) -> InvocationTerminalResult | None:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._failure(history.error, "invocation-history-invalid")
        if history.receipts and history.receipts[-1].attempt >= snapshot.attempt_ceiling:
            return self._terminal_error("attempt-ceiling-exhausted", str(snapshot.attempt_ceiling), str(history.receipts[-1].attempt + 1))
        return None

    def _record(self, snapshot: RunSnapshot, declaration: WorkflowDeclaration, inputs: tuple[str, ...], started: datetime, terminal: InvocationTerminalResult, *, finding_count: int = 0) -> InvocationTerminalResult:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._failure(history.error, "invocation-history-invalid")
        prior = history.receipts[-1] if history.receipts else None
        attempt = 1 if prior is None else prior.attempt + 1
        if attempt > snapshot.attempt_ceiling:
            return self._terminal_error("attempt-ceiling-exhausted", str(snapshot.attempt_ceiling), str(attempt))
        receipt = InvocationReceipt(
            run_id=snapshot.run_id,
            workflow_id=declaration.workflow_id,
            declaration_digest=sha256_digest(canonical_bytes(declaration)),
            snapshot_digest=sha256_digest(canonical_bytes(snapshot)),
            input_digests=inputs,
            output_references=terminal.references,
            attempt=attempt,
            attempt_ceiling=snapshot.attempt_ceiling,
            started_at=started,
            completed_at=datetime.now(UTC),
            finding_count=finding_count,
            terminal=terminal,
            predecessor_receipt_digest=sha256_digest(canonical_bytes(prior)) if prior else None,
        )
        appended = self._store.append_invocation_receipt(receipt)
        return terminal if appended.error is None else self._failure(appended.error, "invocation-receipt-write-failed")

    @staticmethod
    def _failure(error, fallback: str) -> InvocationTerminalResult:
        return FixtureEntrypoints._terminal_from_error(error or actionable_error(code=fallback, workflow="fixture-entrypoint", subject="artifact", rule="durable-read", expected="a persisted compatible artifact", observed="missing", retryability=Retryability.RETRYABLE, next_action="Inspect the artifact store and retry after repair."))

    @staticmethod
    def _terminal_error(code: str, expected: str, observed: str) -> InvocationTerminalResult:
        return FixtureEntrypoints._terminal_from_error(actionable_error(code=code, workflow="fixture-entrypoint", subject="invocation", rule="explicit-authorized-fixture-boundary", expected=expected, observed=observed, retryability=Retryability.NOT_RETRYABLE, next_action="Correct the invocation and submit a new explicit request."))

    @staticmethod
    def _terminal_from_error(error) -> InvocationTerminalResult:
        return InvocationTerminalResult(outcome=OperationalOutcome.RETRYABLE_FAILURE if error.retryability is Retryability.RETRYABLE else OperationalOutcome.TERMINAL_FAILURE, recoverable=error.retryability is Retryability.RETRYABLE, error=error, retry_guidance=error.next_action)
