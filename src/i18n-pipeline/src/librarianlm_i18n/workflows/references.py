"""Typed verification for durable public output references."""

from __future__ import annotations

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    ApplicationEvidence,
    ArtifactReference,
    AssemblyReport,
    CandidateDraft,
    ConfirmationReceipt,
    PreparePackage,
    RunSnapshot,
    SignatureRecord,
    TranslationDraft,
    TranslationRunSummary,
    UnitManifest,
    ValidationReport,
)
from librarianlm_i18n.kernel.errors import ActionableError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest
from librarianlm_i18n.ports.artifact_store import ArtifactStore


_REFERENCE_MODELS = {
    "application-evidence": ApplicationEvidence,
    "assembly-report": AssemblyReport,
    "candidate-draft": CandidateDraft,
    "confirmation-receipt": ConfirmationReceipt,
    "prepare-package": PreparePackage,
    "run-snapshot": RunSnapshot,
    "signature": SignatureRecord,
    "translation-draft": TranslationDraft,
    "translation-run-summary": TranslationRunSummary,
    "unit-manifest": UnitManifest,
    "validation-report": ValidationReport,
}


def verify_output_reference(store: ArtifactStore, reference: ArtifactReference, *, workflow: str) -> ActionableError | None:
    """Require a reference's declared kind and digest to resolve to that contract."""

    model = _REFERENCE_MODELS.get(reference.kind)
    if model is None:
        return actionable_error(
            code="unknown-output-reference-kind", workflow=workflow, subject="output-reference",
            rule="declared-artifact-kind", expected="a supported declared output kind", observed=reference.kind,
            retryability=Retryability.NOT_RETRYABLE,
            next_action="Correct the persisted invocation receipt before resuming.",
        )
    result = store.read_object(reference.digest, model)
    if result.error is not None or result.value is None:
        return result.error or actionable_error(
            code="recorded-output-invalid", workflow=workflow, subject=reference.kind,
            rule="typed-artifact-reference", expected=model.__name__, observed="missing parsed object",
            retryability=Retryability.NOT_RETRYABLE,
            next_action="Repair the durable artifact history before resuming.",
        )
    return None


def verify_completed_outputs(
    store: ArtifactStore, *, snapshot: RunSnapshot, package: PreparePackage,
    references: tuple[ArtifactReference, ...], workflow: str,
) -> ActionableError | None:
    """Verify the complete eligible-output set and its cross-object lineage."""

    expected = {"unit-manifest", "candidate-draft", "assembly-report", "validation-report", "translation-draft", "translation-run-summary"}
    by_kind = {reference.kind: reference for reference in references}
    if set(by_kind) != expected or len(by_kind) != len(references):
        return actionable_error(code="completed-output-set-invalid", workflow=workflow, subject="output-reference", rule="exact-eligible-output-inventory", expected=repr(tuple(sorted(expected))), observed=repr(tuple(reference.kind for reference in references)), retryability=Retryability.NOT_RETRYABLE, next_action="Repair the completed invocation receipt before resuming.")
    values: dict[str, object] = {}
    for reference in references:
        error = verify_output_reference(store, reference, workflow=workflow)
        if error is not None:
            return error
        values[reference.kind] = store.read_object(reference.digest, _REFERENCE_MODELS[reference.kind]).value
    manifest = values["unit-manifest"]
    candidate = values["candidate-draft"]
    assembly = values["assembly-report"]
    validation = values["validation-report"]
    draft = values["translation-draft"]
    summary = values["translation-run-summary"]
    assert isinstance(manifest, UnitManifest) and isinstance(candidate, CandidateDraft)
    assert isinstance(assembly, AssemblyReport) and isinstance(validation, ValidationReport)
    assert isinstance(draft, TranslationDraft) and isinstance(summary, TranslationRunSummary)
    digests = {kind: reference.digest for kind, reference in by_kind.items()}
    package_digest = sha256_digest(canonical_bytes(package))
    valid = (
        manifest.run_snapshot_digest == sha256_digest(canonical_bytes(snapshot))
        and manifest.source_package_digest == package.source_package_digest
        and digests["unit-manifest"] == package.manifest_digest
        and candidate.manifest_digest == package.manifest_digest
        and candidate.source_package_digest == package.source_package_digest
        and assembly.manifest_digest == package.manifest_digest
        and assembly.candidate_draft_digest == digests["candidate-draft"]
        and validation.manifest_digest == package.manifest_digest
        and validation.prepare_package_digest == package_digest
    )
    summary_refs = {item.kind: item.digest for item in summary.report_references}
    valid = valid and validation.assembly_report_digest == digests["assembly-report"] and validation.candidate_draft_digest == digests["candidate-draft"] and draft.manifest_digest == package.manifest_digest and draft.source_package_digest == package.source_package_digest and draft.candidate_draft_digest == digests["candidate-draft"] and draft.validation_report_digest == digests["validation-report"] and summary.manifest_digest == package.manifest_digest and summary_refs.get("assembly-report") == digests["assembly-report"] and summary_refs.get("validation-report") == digests["validation-report"] and summary_refs.get("translation-draft") == digests["translation-draft"]
    if valid:
        return None
    return actionable_error(code="completed-output-lineage-invalid", workflow=workflow, subject="output-reference", rule="cross-object-eligible-lineage", expected="one snapshot-bound prepared graph", observed="cross-wired completed artifacts", retryability=Retryability.NOT_RETRYABLE, next_action="Repair the completed invocation receipt before resuming.")
