"""Resume fixture assembly/validation only from fully verified durable evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    AssembleValidateInvocation, CompatibilityMetadata, InvocationReceipt,
    InvocationTerminalResult, OperationalOutcome, PreparePackage, RunSnapshot,
    SignatureRecord, WorkflowDeclaration,
)
from librarianlm_i18n.kernel.errors import ActionableError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from .assemble_validate import ASSEMBLE_VALIDATE_DECLARATION, AssembleValidateWorkflow
from .references import verify_completed_outputs


ORCHESTRATE_DECLARATION = WorkflowDeclaration(
    workflow_id="fixture-orchestrate",
    purpose="Resume or compose a confirmed fixture run exclusively from verified artifact and receipt chains.",
    input_contracts=(CompatibilityMetadata(contract_name="AssembleValidateInvocation", accepted_versions=(1,)),),
    output_kinds=("unit-manifest", "candidate-draft", "assembly-report", "validation-report", "translation-draft", "translation-run-summary"),
    preconditions=("verified Story 1.2 run recovery", "snapshot/package/confirmation lineage", "explicit operator authorization"),
    confirmation_required=True,
    retry_policy="Append a durable orchestration receipt and reuse only typed compatible completed output.",
    failure_policy="Stop before feature execution on invalid lineage or recovered history.",
    terminal_outcomes=(OperationalOutcome.COMPLETED, OperationalOutcome.RETRYABLE_FAILURE, OperationalOutcome.TERMINAL_FAILURE, OperationalOutcome.RECONCILIATION_REQUIRED),
)


class Orchestrator:
    """A reuse decision is valid only after both Story 1.2 and invocation history verify."""

    def __init__(self, *, store: ArtifactStore, assemble_validate: AssembleValidateWorkflow) -> None:
        self._store = store
        self._assemble_validate = assemble_validate

    def resume(self, invocation: AssembleValidateInvocation) -> InvocationTerminalResult:
        started = datetime.now(UTC)
        snapshot: RunSnapshot | None = None
        try:
            snapshot_result = self._store.read_object(invocation.snapshot_digest, RunSnapshot)
            if snapshot_result.error is not None or snapshot_result.value is None:
                return self._from_error(snapshot_result.error or self._error("snapshot-unavailable", "missing", retryable=True))
            snapshot = snapshot_result.value
            terminal = self._resume_verified(snapshot, invocation)
        except Exception as error:
            terminal = self._from_error(self._error("orchestration-failure", f"{type(error).__name__}: {error}", retryable=True))
        if snapshot is None:
            return terminal
        if terminal.outcome is OperationalOutcome.COMPLETED and self._has_completed_orchestration(snapshot, invocation):
            return terminal
        return self._record(snapshot, invocation, started, terminal)

    def _resume_verified(self, snapshot: RunSnapshot, invocation: AssembleValidateInvocation) -> InvocationTerminalResult:
        if not invocation.operator_authorized:
            return self._from_error(self._error("operator-authorization-required", "missing", retryable=False))
        recovered = self._store.recover(snapshot.run_id)
        if recovered.error is not None or recovered.reference is None or recovered.manifest is None or not recovered.receipts:
            return self._from_error(recovered.error or self._error("operational-recovery-invalid", "missing Story 1.2 recovery state", retryable=False))
        package_result = self._store.read_object(invocation.package_digest, PreparePackage)
        if package_result.error is not None or package_result.value is None:
            return self._from_error(package_result.error or self._error("prepare-package-unavailable", "missing", retryable=False))
        package = package_result.value
        if (
            package.run_snapshot_digest != invocation.snapshot_digest
            or recovered.reference.manifest_digest != package.manifest_digest
            or recovered.manifest.run_snapshot_digest != invocation.snapshot_digest
            or recovered.manifest.source_package_digest != package.source_package_digest
            or sha256_digest(canonical_bytes(snapshot.source_package)) != package.source_package_digest
        ):
            return self._from_error(self._error("recovered-lineage-mismatch", "snapshot, package, and recovered manifest do not bind one graph", retryable=False))
        if invocation.confirmation.package_digest != invocation.package_digest:
            return self._from_error(self._error("confirmation-package-mismatch", invocation.confirmation.package_digest, retryable=False))
        confirmation_error = self._assemble_validate.verify_confirmation(package_digest=invocation.package_digest, confirmation=invocation.confirmation)
        if confirmation_error is not None:
            return self._from_error(confirmation_error)
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._from_error(history.error)
        declaration_digest = sha256_digest(canonical_bytes(ASSEMBLE_VALIDATE_DECLARATION))
        inputs = (invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation.confirmation)))
        for receipt in reversed(history.receipts):
            if receipt.workflow_id != ASSEMBLE_VALIDATE_DECLARATION.workflow_id or receipt.declaration_digest != declaration_digest or receipt.snapshot_digest != invocation.snapshot_digest or receipt.input_digests != inputs:
                continue
            if receipt.terminal.outcome is not OperationalOutcome.COMPLETED:
                if not receipt.terminal.recoverable:
                    return receipt.terminal
                break
            error = verify_completed_outputs(self._store, snapshot=snapshot, package=package, references=receipt.output_references, workflow="orchestrate")
            if error is not None:
                return self._from_error(error)
            return receipt.terminal
        return self._assemble_validate.run(invocation)

    def _has_completed_orchestration(self, snapshot: RunSnapshot, invocation: AssembleValidateInvocation) -> bool:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return False
        inputs = (invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation.confirmation)))
        declaration_digest = sha256_digest(canonical_bytes(ORCHESTRATE_DECLARATION))
        return any(
            receipt.workflow_id == ORCHESTRATE_DECLARATION.workflow_id
            and receipt.declaration_digest == declaration_digest
            and receipt.snapshot_digest == invocation.snapshot_digest
            and receipt.input_digests == inputs
            and receipt.terminal.outcome is OperationalOutcome.COMPLETED
            for receipt in history.receipts
        )

    def _record(self, snapshot: RunSnapshot, invocation: AssembleValidateInvocation, started: datetime, terminal: InvocationTerminalResult) -> InvocationTerminalResult:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._from_error(history.error)
        prior = history.receipts[-1] if history.receipts else None
        attempt = 1 if prior is None else prior.attempt + 1
        if attempt > snapshot.attempt_ceiling:
            return self._from_error(self._error("attempt-ceiling-exhausted", str(snapshot.attempt_ceiling), retryable=False))
        receipt = InvocationReceipt(
            run_id=snapshot.run_id,
            workflow_id=ORCHESTRATE_DECLARATION.workflow_id,
            declaration_digest=sha256_digest(canonical_bytes(ORCHESTRATE_DECLARATION)),
            snapshot_digest=sha256_digest(canonical_bytes(snapshot)),
            input_digests=(invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation.confirmation))),
            output_references=terminal.references,
            attempt=attempt,
            attempt_ceiling=snapshot.attempt_ceiling,
            started_at=started,
            completed_at=datetime.now(UTC),
            finding_count=0,
            terminal=terminal,
            predecessor_receipt_digest=sha256_digest(canonical_bytes(prior)) if prior else None,
        )
        appended = self._store.append_invocation_receipt(receipt)
        return terminal if appended.error is None else self._from_error(appended.error)

    @staticmethod
    def _error(code: str, observed: str, *, retryable: bool) -> ActionableError:
        return actionable_error(code=code, workflow="orchestrate", subject="invocation", rule="verified-receipt-resume", expected="a compatible verified Story 1.2 and invocation receipt graph", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Repair the durable history or start a new fixture run.")

    @staticmethod
    def _from_error(error: ActionableError) -> InvocationTerminalResult:
        return InvocationTerminalResult(outcome=OperationalOutcome.RETRYABLE_FAILURE if error.retryability is Retryability.RETRYABLE else OperationalOutcome.TERMINAL_FAILURE, recoverable=error.retryability is Retryability.RETRYABLE, error=error, retry_guidance=error.next_action)
