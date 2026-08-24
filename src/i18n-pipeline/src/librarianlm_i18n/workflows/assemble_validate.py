"""Verified composition of the existing fixture assembly and validation filters."""

from __future__ import annotations

from datetime import UTC, datetime

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    ArtifactReference,
    AssembleValidateInvocation,
    AssemblyReport,
    CompatibilityMetadata,
    InvocationReceipt,
    InvocationTerminalResult,
    OperationalOutcome,
    PreparePackage,
    RunSnapshot,
    TranslationDraft,
    TranslationRunSummary,
    ValidationReport,
    WorkflowDeclaration,
)
from librarianlm_i18n.kernel.errors import ActionableError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from .assemble import AssemblyWorkflow
from .validate import ValidationWorkflow
from .references import verify_completed_outputs


ASSEMBLE_VALIDATE_DECLARATION = WorkflowDeclaration(
    workflow_id="fixture-assemble-validate",
    purpose="Assemble only snapshot-bound fixture targets, then validate the immutable assembled graph.",
    input_contracts=(CompatibilityMetadata(contract_name="AssembleValidateInvocation", accepted_versions=(1,)),),
    output_kinds=("unit-manifest", "candidate-draft", "assembly-report", "validation-report", "translation-draft", "translation-run-summary"),
    preconditions=("explicit fixture snapshot", "confirmed prepare package", "verified detached confirmation"),
    confirmation_required=True,
    retry_policy="Append a receipt; reuse only verified compatible completed output.",
    failure_policy="Return reports and validation status truthfully; never advertise an ineligible draft.",
    terminal_outcomes=(OperationalOutcome.COMPLETED, OperationalOutcome.RETRYABLE_FAILURE, OperationalOutcome.TERMINAL_FAILURE, OperationalOutcome.RECONCILIATION_REQUIRED),
)


class AssembleValidateWorkflow:
    """Artifact-only composition; it has no provider or model-gateway seam."""

    def __init__(self, *, store: ArtifactStore, assembly: AssemblyWorkflow, validation: ValidationWorkflow) -> None:
        self._store = store
        self._assembly = assembly
        self._validation = validation

    def verify_confirmation(self, *, package_digest: str, confirmation) -> ActionableError | None:
        """Public confirmation seam shared by execution and orchestration reuse."""
        return self._assembly.verify_confirmation(package_digest=package_digest, confirmation=confirmation)

    def run(self, invocation: AssembleValidateInvocation) -> InvocationTerminalResult:
        started = datetime.now(UTC)
        snapshot: RunSnapshot | None = None
        try:
            snapshot = self._read(invocation.snapshot_digest, RunSnapshot)
            package = self._read(invocation.package_digest, PreparePackage)
            history = self._store.recover_invocation_receipts(snapshot.run_id)
            if history.error is not None:
                return self._from_error(history.error)
            if not invocation.operator_authorized:
                return self._record(snapshot, invocation, started, self._failure("operator-authorization-required", "operator authorization", "missing"))
            if package.run_snapshot_digest != invocation.snapshot_digest:
                return self._record(snapshot, invocation, started, self._failure("snapshot-package-mismatch", invocation.snapshot_digest, package.run_snapshot_digest))
            if invocation.confirmation.package_digest != invocation.package_digest:
                return self._record(snapshot, invocation, started, self._failure("confirmation-package-mismatch", invocation.package_digest, invocation.confirmation.package_digest))
            confirmation_error = self.verify_confirmation(package_digest=invocation.package_digest, confirmation=invocation.confirmation)
            if confirmation_error is not None:
                return self._record(snapshot, invocation, started, self._from_error(confirmation_error))
            inputs = (invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation.confirmation)))
            declaration_digest = sha256_digest(canonical_bytes(ASSEMBLE_VALIDATE_DECLARATION))
            for receipt in reversed(history.receipts):
                if receipt.workflow_id != ASSEMBLE_VALIDATE_DECLARATION.workflow_id or receipt.declaration_digest != declaration_digest or receipt.snapshot_digest != invocation.snapshot_digest or receipt.input_digests != inputs:
                    continue
                if receipt.terminal.outcome is OperationalOutcome.COMPLETED:
                    package_error = verify_completed_outputs(self._store, snapshot=snapshot, package=package, references=receipt.output_references, workflow="assemble-validate")
                    return receipt.terminal if package_error is None else self._record(snapshot, invocation, started, self._from_error(package_error))
                if not receipt.terminal.recoverable:
                    return receipt.terminal
                break
            if history.receipts and history.receipts[-1].attempt >= snapshot.attempt_ceiling:
                return self._failure("attempt-ceiling-exhausted", str(snapshot.attempt_ceiling), str(history.receipts[-1].attempt + 1))
            assembled = self._assembly.assemble(
                package_digest=invocation.package_digest,
                confirmation=invocation.confirmation,
                fixture_targets=snapshot.fixture_targets,
            )
            if assembled.error is not None:
                return self._record(snapshot, invocation, started, self._from_error(assembled.error))
            validated = self._validation.validate(
                package_digest=invocation.package_digest,
                confirmation=invocation.confirmation,
                assembly_report_digest=assembled.value.report_digest,
            )
            if validated.error is not None:
                return self._record(snapshot, invocation, started, self._from_error(validated.error))
            report_digest = sha256_digest(canonical_bytes(validated.value.report))
            summary_digest = sha256_digest(canonical_bytes(validated.value.summary))
            references = [
                ArtifactReference(kind="unit-manifest", digest=package.manifest_digest),
                ArtifactReference(kind="candidate-draft", digest=assembled.value.report.candidate_draft_digest),
                ArtifactReference(kind="assembly-report", digest=assembled.value.report_digest),
                ArtifactReference(kind="validation-report", digest=report_digest),
                ArtifactReference(kind="translation-run-summary", digest=summary_digest),
            ]
            blocked = validated.value.draft is None
            if not blocked:
                references.append(ArtifactReference(kind="translation-draft", digest=sha256_digest(canonical_bytes(validated.value.draft))))
            if blocked:
                terminal = InvocationTerminalResult(
                    outcome=OperationalOutcome.RECONCILIATION_REQUIRED,
                    recoverable=False,
                    references=tuple(references),
                    status=validated.value.report.status,
                    error=self._error("validation-blocked", "validation", "blocking findings", retryable=False),
                    retry_guidance="Repair the frozen inputs or confirmed graph and start a new legal attempt.",
                )
            else:
                terminal = InvocationTerminalResult(
                    outcome=OperationalOutcome.COMPLETED,
                    recoverable=False,
                    references=tuple(references),
                    status=validated.value.report.status,
                    retry_guidance="No retry is required; eligibility does not imply review or publication approval.",
                )
            return self._record(snapshot, invocation, started, terminal, finding_count=len(validated.value.report.findings))
        except Exception as error:  # Public composition is intentionally exception-safe.
            terminal = self._from_error(self._error("assemble-validate-failure", "assemble-validate", f"{type(error).__name__}: {error}", retryable=True))
            return terminal if snapshot is None else self._record(snapshot, invocation, started, terminal)

    def _record(self, snapshot: RunSnapshot, invocation: AssembleValidateInvocation, started: datetime, terminal: InvocationTerminalResult, *, finding_count: int = 0) -> InvocationTerminalResult:
        history = self._store.recover_invocation_receipts(snapshot.run_id)
        if history.error is not None:
            return self._from_error(history.error)
        previous = history.receipts[-1] if history.receipts else None
        attempt = 1 if previous is None else previous.attempt + 1
        if attempt > snapshot.attempt_ceiling:
            return self._failure("attempt-ceiling-exhausted", str(snapshot.attempt_ceiling), str(attempt))
        receipt = InvocationReceipt(
            run_id=snapshot.run_id,
            workflow_id=ASSEMBLE_VALIDATE_DECLARATION.workflow_id,
            declaration_digest=sha256_digest(canonical_bytes(ASSEMBLE_VALIDATE_DECLARATION)),
            snapshot_digest=sha256_digest(canonical_bytes(snapshot)),
            input_digests=(invocation.snapshot_digest, invocation.package_digest, sha256_digest(canonical_bytes(invocation.confirmation))),
            output_references=terminal.references,
            attempt=attempt,
            attempt_ceiling=snapshot.attempt_ceiling,
            started_at=started,
            completed_at=datetime.now(UTC),
            finding_count=finding_count,
            terminal=terminal,
            predecessor_receipt_digest=sha256_digest(canonical_bytes(previous)) if previous else None,
        )
        appended = self._store.append_invocation_receipt(receipt)
        return terminal if appended.error is None else self._from_error(appended.error)

    def _read(self, digest: str, model):
        result = self._store.read_object(digest, model)
        if result.error is not None or result.value is None:
            raise RuntimeError(result.error.code if result.error else "artifact-read-failed")
        return result.value

    @staticmethod
    def _error(code: str, subject: str, observed: str, *, retryable: bool) -> ActionableError:
        return actionable_error(code=code, workflow="assemble-validate", subject=subject, rule="verified-fixture-composition", expected="a compatible confirmed snapshot-bound graph", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Inspect the durable receipts and repair the named immutable input before retrying.")

    def _failure(self, code: str, expected: str, observed: str) -> InvocationTerminalResult:
        return self._from_error(self._error(code, "invocation", observed, retryable=False).model_copy(update={"expected": expected}))

    @staticmethod
    def _from_error(error: ActionableError) -> InvocationTerminalResult:
        return InvocationTerminalResult(
            outcome=OperationalOutcome.RETRYABLE_FAILURE if error.retryability is Retryability.RETRYABLE else OperationalOutcome.TERMINAL_FAILURE,
            recoverable=error.retryability is Retryability.RETRYABLE,
            error=error,
            retry_guidance=error.next_action,
        )
