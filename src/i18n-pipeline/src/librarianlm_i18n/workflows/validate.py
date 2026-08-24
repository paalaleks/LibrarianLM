"""Read-only deterministic validation of an assembled fixture graph."""

from __future__ import annotations

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    ApplicationEvidence, ArtifactReference, AssemblyReport, CandidateDraft, CanonicalSourcePackage,
    ConfirmationReceipt, Eligibility, Finding, LocaleMetadata, PreparePackage,
    ResidualLanguageEvidence, SignatureRecord,
    StatusValue, StatusVector, TranslationDraft, TranslationRunSummary,
    UnitManifest, ValidationReport, ValidationResult,
)
from librarianlm_i18n.kernel.errors import ActionableError, KernelValidationError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from librarianlm_i18n.ports.html_document import HtmlDocument
from librarianlm_i18n.ports.package_signer import PackageSigner
from librarianlm_i18n.ports.residual_language import ResidualLanguageDetector


class ValidationExecutionResult:
    def __init__(self, *, value: ValidationResult | None = None, error: ActionableError | None = None) -> None:
        if (value is None) == (error is None):
            raise ValueError("validation execution results require exactly one value or error")
        self.value = value
        self.error = error


class ValidationWorkflow:
    """The sole eligibility authority; it never mutates candidate or manifest input."""

    def __init__(self, *, store: ArtifactStore, document: HtmlDocument, signer: PackageSigner, residual_detector: ResidualLanguageDetector | None = None) -> None:
        self._store = store
        self._document = document
        self._signer = signer
        self._residual_detector = residual_detector

    def validate(self, *, package_digest: str, confirmation: ConfirmationReceipt, assembly_report_digest: str) -> ValidationExecutionResult:
        try:
            package = self._read(package_digest, PreparePackage)
            self._assert_graph(package_digest, package, confirmation, assembly_report_digest)
            manifest = self._read(package.manifest_digest, UnitManifest)
            source = self._read(package.source_package_digest, CanonicalSourcePackage)
            report = self._read(assembly_report_digest, AssemblyReport)
            candidate = self._read(report.candidate_draft_digest, CandidateDraft)
            findings, residual_evidence, validated_required_count = self._inspect(source, package, manifest, candidate)
            repeated_findings, repeated_evidence, repeated_required_count = self._inspect(source, package, manifest, candidate)
            first_probe = canonical_bytes((
                tuple(item.model_dump(mode="json") for item in findings),
                tuple(item.model_dump(mode="json") for item in residual_evidence),
                validated_required_count,
            ))
            second_probe = canonical_bytes((
                tuple(item.model_dump(mode="json") for item in repeated_findings),
                tuple(item.model_dump(mode="json") for item in repeated_evidence),
                repeated_required_count,
            ))
            if first_probe != second_probe:
                findings.append(self._finding(
                    "validation-nondeterministic", "validation", "repeatable-validation-probe",
                    sha256_digest(first_probe), sha256_digest(second_probe),
                ))
            findings = tuple(sorted(findings, key=lambda item: (item.code, item.subject, item.rule, item.observed)))
            residual_evidence = tuple(sorted(
                residual_evidence,
                key=lambda item: (item.source_unit_id, item.detector.implementation, item.matched_terms),
            ))
            blocked = any(item.severity == "blocking-error" for item in findings)
            structural_codes = {
                "accessibility-focus-order-changed", "anchor-target-invalid", "candidate-html-invalid", "heading-hierarchy-invalid",
                "heading-order-changed", "landmark-order-changed", "placement-inventory-mismatch",
                "preserved-content-mismatch", "projection-value-mismatch", "structure-not-preserved",
            }
            structurally_incomplete = any(item.code in structural_codes for item in findings)
            status = StatusVector(
                processing=StatusValue.COMPLETE,
                completeness=StatusValue.INCOMPLETE if structurally_incomplete else StatusValue.COMPLETE,
                compliance=StatusValue.FAILED if blocked else StatusValue.CLEAN,
                review=StatusValue.NOT_STARTED,
                publication=StatusValue.NOT_READY,
            )
            validation_report = ValidationReport(
                manifest_digest=package.manifest_digest, findings=findings, status=status,
                source_package_digest=package.source_package_digest, prepare_package_digest=package_digest,
                assembly_report_digest=assembly_report_digest, candidate_draft_digest=report.candidate_draft_digest,
                component=report.lineage.component,
                residual_language_evidence=residual_evidence,
                residual_exempt_unit_ids=package.validation_controls.residual_language.exempt_unit_ids,
                limitations=tuple(sorted({item.limitation for item in residual_evidence})),
                required_unit_count=sum(unit.eligibility is Eligibility.REQUIRED for unit in manifest.units),
                validated_required_unit_count=validated_required_count,
            )
            validation_report_digest = self._put(validation_report)
            references = [
                ("assembly-report", assembly_report_digest),
                ("validation-report", validation_report_digest),
            ]
            draft: TranslationDraft | None = None
            if not blocked:
                draft = TranslationDraft(
                    source_package_digest=package.source_package_digest, manifest_digest=package.manifest_digest,
                    candidate_draft_digest=report.candidate_draft_digest, validation_report_digest=validation_report_digest,
                    eligible=True, status=status,
                )
                references.append(("translation-draft", self._put(draft)))
            summary = TranslationRunSummary(
                manifest_digest=package.manifest_digest, status=status,
                report_references=tuple(ArtifactReference(kind=kind, digest=digest) for kind, digest in references),
                finding_count=len(findings), blocker_count=sum(item.severity == "blocking-error" for item in findings),
            )
            self._put(summary)
            return ValidationExecutionResult(value=ValidationResult(report=validation_report, summary=summary, draft=draft))
        except KernelValidationError as failure:
            return ValidationExecutionResult(error=failure.error)
        except Exception as error:
            return ValidationExecutionResult(error=self._error("validation-failure", "validate", f"{type(error).__name__}: {error}", retryable=True))

    def _assert_graph(self, package_digest: str, package: PreparePackage, confirmation: ConfirmationReceipt, assembly_report_digest: str) -> None:
        if confirmation.package_digest != package_digest:
            raise KernelValidationError(self._error("confirmation-package-mismatch", "confirmation", "receipt does not bind supplied package"))
        signature = self._read(confirmation.signature_digest, SignatureRecord)
        verified = self._signer.verify(signature, package_digest, confirmation.key_id)
        if verified.error is not None or not verified.verified:
            raise KernelValidationError(verified.error or self._error("signature-invalid", "confirmation", "trusted signer declined signature"))
        manifest = self._read(package.manifest_digest, UnitManifest)
        source = self._read(package.source_package_digest, CanonicalSourcePackage)
        if manifest.source_package_digest != package.source_package_digest or manifest.source_package_digest != sha256_digest(canonical_bytes(source)):
            raise KernelValidationError(self._error("manifest-source-mismatch", "manifest", "manifest does not bind exact canonical source"))
        report = self._read(assembly_report_digest, AssemblyReport)
        if report.manifest_digest != package.manifest_digest or report.candidate_draft_digest is None or report.application_evidence_digest is None:
            raise KernelValidationError(self._error("assembly-report-lineage-invalid", "assembly-report", "candidate/evidence pair does not bind package manifest"))
        if (
            report.lineage is None
            or report.lineage.source_package_digest != package.source_package_digest
            or report.lineage.prepare_package_digest != package_digest
            or report.lineage.confirmation_digest != sha256_digest(canonical_bytes(confirmation))
            or report.lineage.confirmation_signature_digest != confirmation.signature_digest
            or report.lineage.component != source.converter_identity
        ):
            raise KernelValidationError(self._error("assembly-report-lineage-invalid", "assembly-report", "persisted assembly lineage is missing or cross-wired"))
        candidate = self._read(report.candidate_draft_digest, CandidateDraft)
        evidence = self._read(report.application_evidence_digest, ApplicationEvidence)
        if candidate.source_package_digest != package.source_package_digest or candidate.manifest_digest != package.manifest_digest or evidence.manifest_digest != package.manifest_digest or evidence.candidate_html_digest != candidate.html_digest:
            raise KernelValidationError(self._error("assembly-artifact-mismatch", "assembly-output", "candidate/evidence do not bind exact prepared graph"))
        expected = tuple(unit.source_unit_id for unit in manifest.units if unit.eligibility is Eligibility.REQUIRED and (unit.projection_group_id is None or next(group for group in manifest.projection_groups if group.group_id == unit.projection_group_id).canonical_source_unit_id == unit.source_unit_id))
        if evidence.applied_source_unit_ids != expected:
            raise KernelValidationError(self._error("application-evidence-inventory-mismatch", "assembly-evidence", "required canonical unit inventory differs"))
        expected_members: list[str] = []
        for canonical in (unit for unit in manifest.units if unit.source_unit_id in expected):
            if canonical.projection_group_id is None:
                expected_members.append(canonical.source_unit_id)
            else:
                expected_members.extend(
                    unit.source_unit_id for unit in manifest.units
                    if unit.projection_group_id == canonical.projection_group_id
                )
        if evidence.applied_member_ids != tuple(expected_members):
            raise KernelValidationError(self._error("application-evidence-member-mismatch", "assembly-evidence", "applied projection members differ from the exact manifest order"))
        control = package.validation_controls.residual_language
        if control.detector is not None and (self._residual_detector is None or self._residual_detector.identity != control.detector):
            raise KernelValidationError(self._error("residual-detector-mismatch", "residual-language", "frozen detector is unavailable or has a different identity"))

    def _inspect(
        self,
        source: CanonicalSourcePackage,
        package: PreparePackage,
        manifest: UnitManifest,
        candidate: CandidateDraft,
    ) -> tuple[list[Finding], list[ResidualLanguageEvidence], int]:
        source_observation = self._document.observe(source, source.source_html)
        candidate_observation = self._document.observe(source, candidate.html)
        if source_observation.error is not None:
            raise KernelValidationError(source_observation.error)
        if candidate_observation.error is not None:
            error = candidate_observation.error
            return ([self._finding(
                "candidate-html-invalid", "candidate-draft", "readable-secured-html",
                error.expected, f"{error.code}: {error.observed}",
            )], [], 0)
        findings: list[Finding] = []
        residual_evidence: list[ResidualLanguageEvidence] = []
        source_view, candidate_view = source_observation.observation, candidate_observation.observation
        controls = package.validation_controls
        expected_source_locale = controls.source_locale
        if (
            source_view.root_language != expected_source_locale.language
            or source_view.root_direction != expected_source_locale.direction
        ):
            findings.append(self._finding(
                "source-locale-mismatch", "canonical-source", "frozen-source-locale-direction",
                f"{expected_source_locale.language}/{expected_source_locale.direction}",
                f"{source_view.root_language!r}/{source_view.root_direction!r}",
            ))
        if source_view.structure_digest != candidate_view.structure_digest:
            findings.append(self._finding("structure-not-preserved", "candidate-draft", "structure", source_view.structure_digest, candidate_view.structure_digest))
        expected_locale = controls.target_locale
        if candidate_view.root_language != expected_locale.language or candidate_view.root_direction != expected_locale.direction:
            findings.append(self._finding("root-locale-mismatch", "candidate-draft", "locale-direction", f"{expected_locale.language}/{expected_locale.direction}", f"{candidate_view.root_language!r}/{candidate_view.root_direction!r}"))
        expected_locations = {unit.structural_location: unit for unit in manifest.units if unit.structural_location is not None}
        source_values = {slot.location: slot.text for slot in source_view.slots}
        candidate_values = {slot.location: slot.text for slot in candidate_view.slots}
        if set(source_values) != set(candidate_values) or set(candidate_values) != set(expected_locations):
            findings.append(self._finding("placement-inventory-mismatch", "candidate-draft", "declared-required-replacements", repr(tuple(expected_locations)), repr(tuple(candidate_values))))
        required = {unit.structural_location for unit in manifest.units if unit.eligibility is Eligibility.REQUIRED}
        validated_required_count = len(required.intersection(candidate_values))
        for location, original in source_values.items():
            if location not in required and candidate_values.get(location) != original:
                findings.append(self._finding("preserved-content-mismatch", str(location), "excluded-content-exact", original, repr(candidate_values.get(location))))
        for group in manifest.projection_groups:
            members = tuple(unit for unit in manifest.units if unit.projection_group_id == group.group_id)
            values = tuple(candidate_values.get(unit.structural_location) for unit in members)
            if len(set(values)) != 1:
                findings.append(self._finding(
                    "projection-value-mismatch", group.group_id, "declared-projection-members-equal",
                    repr(values[0] if values else None), repr(values),
                ))
        for control in package.validation_controls.terminology:
            locations = tuple(unit.structural_location for unit in manifest.units if unit.source_unit_id in control.required_unit_ids)
            values = "\n".join(candidate_values.get(location, "") for location in locations)
            for term in control.required_terms:
                if term not in values:
                    findings.append(self._finding("terminology-control-failed", control.rule_id, "explicit-terminology", term, values or "missing scoped candidate value"))

        if source_view.heading_levels != candidate_view.heading_levels:
            findings.append(self._finding("heading-order-changed", "candidate-draft", "preserved-heading-hierarchy", repr(source_view.heading_levels), repr(candidate_view.heading_levels)))
        for previous, current in zip(candidate_view.heading_levels, candidate_view.heading_levels[1:]):
            if current > previous + 1:
                findings.append(self._finding("heading-hierarchy-invalid", "candidate-draft", "no-skipped-heading-level", f"at most h{previous + 1}", f"h{current}"))
        if source_view.landmarks != candidate_view.landmarks:
            findings.append(self._finding("landmark-order-changed", "candidate-draft", "preserved-landmarks-and-reading-order", repr(source_view.landmarks), repr(candidate_view.landmarks)))
        if source_view.focus_order != candidate_view.focus_order:
            findings.append(self._finding("accessibility-focus-order-changed", "candidate-draft", "preserved-keyboard-focus-order", repr(source_view.focus_order), repr(candidate_view.focus_order)))
        if source_view.fragment_references != candidate_view.fragment_references:
            findings.append(self._finding("anchor-target-invalid", "candidate-draft", "preserved-anchor-and-footnote-links", repr(source_view.fragment_references), repr(candidate_view.fragment_references)))
        candidate_ids = set(candidate_view.element_ids)
        if len(candidate_ids) != len(candidate_view.element_ids):
            findings.append(self._finding("anchor-target-invalid", "candidate-draft", "unique-fragment-identifiers", "unique element IDs", repr(candidate_view.element_ids)))
        for path, target in candidate_view.fragment_references:
            if not target or target not in candidate_ids:
                findings.append(self._finding("anchor-target-invalid", path, "resolvable-fragment-target", "an existing unique element ID", target or "empty fragment"))

        for path, language, direction in candidate_view.language_metadata:
            effective_language = language or candidate_view.root_language
            effective_direction = direction or candidate_view.root_direction
            try:
                LocaleMetadata(language=effective_language, direction=effective_direction)
            except Exception as error:
                findings.append(self._finding(
                    "passage-locale-invalid", path, "canonical-programmatic-language-direction",
                    "canonical BCP-47 metadata with matching direction", f"{language!r}/{direction!r}: {error}",
                ))
        residual = package.validation_controls.residual_language
        if residual.detector is not None and self._residual_detector is not None:
            for unit in manifest.units:
                if unit.eligibility is not Eligibility.REQUIRED or unit.structural_location is None or unit.source_unit_id in residual.exempt_unit_ids:
                    continue
                result = self._residual_detector.inspect(source_unit_id=unit.source_unit_id, source_text=source_values.get(unit.structural_location, ""), target_text=candidate_values.get(unit.structural_location, ""))
                if result.error is not None:
                    raise KernelValidationError(result.error)
                if result.evidence.source_unit_id != unit.source_unit_id or result.evidence.detector != residual.detector:
                    raise KernelValidationError(self._error(
                        "residual-detector-evidence-mismatch", unit.source_unit_id,
                        "detector evidence does not bind the inspected unit and frozen detector",
                    ))
                residual_evidence.append(result.evidence)
                if result.evidence.residual_count > residual.tolerance:
                    findings.append(self._finding("residual-language-detected", unit.source_unit_id, "fixture-residual-language", f"at most {residual.tolerance}", repr(result.evidence.matched_terms)))
        return findings, residual_evidence, validated_required_count

    @staticmethod
    def _finding(code: str, subject: str, rule: str, expected: str, observed: str) -> Finding:
        return Finding(code=code, severity="blocking-error", subject=subject, rule=rule, expected=expected, observed=observed, retryability=Retryability.NOT_RETRYABLE, next_action="Repair the immutable candidate or frozen controls and rerun validation.")

    def _read(self, digest: str, model):
        result = self._store.read_object(digest, model)
        if result.error is not None or result.value is None:
            raise KernelValidationError(result.error or self._error("artifact-read-failed", "artifact", "store returned no value", retryable=True))
        return result.value

    def _put(self, value) -> str:
        result = self._store.put_object(value)
        if result.error is not None or result.digest is None:
            raise KernelValidationError(result.error or self._error("artifact-write-failed", "artifact", "store returned no digest", retryable=True))
        return result.digest

    @staticmethod
    def _error(code: str, subject: str, observed: str, *, retryable: bool = False) -> ActionableError:
        return actionable_error(code=code, workflow="validate", subject=subject, rule="frozen-read-only-validation", expected="a complete compatible immutable assembled graph", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Repair the persisted graph or candidate and restart validation.")
