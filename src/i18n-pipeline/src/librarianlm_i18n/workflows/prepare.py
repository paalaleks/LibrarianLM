"""Fixture-v1 preparation and detached confirmation workflow."""

from __future__ import annotations

from collections.abc import Iterable

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    CanonicalSourcePackage, ConfirmationReceipt, ContentClass, EditorialSheet,
    EditorialSheetKind, EditorialSheetState, Eligibility, OperationalFinding,
    OperationalOutcome, PreparePackage, PreparePolicy, PrepareResult,
    PreparationFinding, PreparationFindings, PreparationOutcome, ProjectionMap,
    ProjectionOwnership, SignatureRecord, StatusValue, StatusVector, UnitManifest,
    UnitRecord,
)
from librarianlm_i18n.kernel.errors import ActionableError, KernelValidationError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import derive_typed_id, is_sha256_digest, sha256_digest
from librarianlm_i18n.kernel.lifecycle import UnitLifecycleState
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from librarianlm_i18n.ports.html_document import HtmlDocument, SelectedSourceSlot
from librarianlm_i18n.ports.package_signer import PackageSigner


class PrepareExecutionResult:
    def __init__(self, *, value: PrepareResult | None = None, error: ActionableError | None = None) -> None:
        if (value is None) == (error is None):
            raise ValueError("prepare execution results require exactly one value or error")
        self.value = value
        self.error = error


class ConfirmationResult:
    def __init__(self, *, signature: SignatureRecord | None = None, receipt: ConfirmationReceipt | None = None, error: ActionableError | None = None) -> None:
        successful = signature is not None and receipt is not None
        if (error is None) != successful:
            raise ValueError("confirmation results require signature and receipt or an error")
        self.signature = signature
        self.receipt = receipt
        self.error = error


class PrepareWorkflow:
    """The only owner of fixture classification, segmentation, ordering and maps."""

    def __init__(self, *, store: ArtifactStore, document: HtmlDocument, signer: PackageSigner) -> None:
        self._store = store
        self._document = document
        self._signer = signer

    def prepare(
        self, *, run_id: str, source_package: CanonicalSourcePackage, policy: PreparePolicy,
        sheets: tuple[EditorialSheet, ...], run_snapshot_digest: str,
        prior_manifest: UnitManifest | None = None, attempt: int = 1, attempt_ceiling: int = 1,
    ) -> PrepareExecutionResult:
        try:
            findings = list(self._validate_inputs(source_package, policy, sheets, run_snapshot_digest))
            # Content objects are immutable evidence even for a blocked attempt.
            source_digest = self._put(source_package)
            policy_digest = self._put(policy)
            terminology, style = self._sheets(sheets)
            terminology_digest, style_digest = self._put(terminology), self._put(style)
            if not self._has_blocking_findings(policy, findings):
                selected = self._document.select(source_package)
                if selected.error is not None:
                    findings.append(self._finding_from_error(selected.error))
                    slots: tuple[SelectedSourceSlot, ...] = ()
                else:
                    slots = selected.slots
                    manifest, selection_findings = self._derive_manifest(source_package, run_snapshot_digest, slots, prior_manifest)
                    findings.extend(selection_findings)
            else:
                slots = ()
            if self._has_blocking_findings(policy, findings):
                return self._blocked(run_id, findings, attempt, attempt_ceiling)
            self._validate_sheet_scopes((terminology, style), manifest)
            findings_object = PreparationFindings(findings=tuple(findings))
            findings_digest = self._put(findings_object)
            manifest_digest = sha256_digest(canonical_bytes(manifest))
            package = PreparePackage(
                source_package_digest=source_digest, run_snapshot_digest=run_snapshot_digest,
                manifest_digest=manifest_digest, policy_digest=policy_digest,
                terminology_sheet_digest=terminology_digest, style_sheet_digest=style_digest,
                findings_digest=findings_digest, ownership_profile=source_package.ownership_profile,
                projection_profile=source_package.projection_profile,
                segmentation_profile=source_package.segmentation_profile,
                status="ready-for-confirmation",
            )
            published = self._store.publish_manifest(run_id, manifest, expected_predecessor_digest=None, attempt=attempt, attempt_ceiling=attempt_ceiling)
            if published.error is not None:
                return PrepareExecutionResult(error=published.error)
            if published.reference.manifest_digest != manifest_digest:
                return PrepareExecutionResult(error=self._error("manifest-integrity-failure", "manifest", "canonical manifest digest differs from publication", retryable=True))
            package_digest = self._put(package)
            return PrepareExecutionResult(value=PrepareResult(
                outcome=PreparationOutcome(status="ready-for-confirmation", findings=tuple(findings), package_digest=package_digest, manifest_digest=manifest_digest),
                manifest=manifest, package=package,
            ))
        except KernelValidationError as failure:
            return PrepareExecutionResult(error=failure.error)
        except Exception as error:
            return PrepareExecutionResult(error=self._error("prepare-failure", "prepare", f"{type(error).__name__}: {error}", retryable=True))

    def confirm(self, *, package_digest: str, requested_key_id: str, operator_id: str) -> ConfirmationResult:
        try:
            if not is_sha256_digest(package_digest):
                return ConfirmationResult(error=self._error("invalid-package-digest", "prepare-package", repr(package_digest)))
            package = self._read(package_digest, PreparePackage)
            if package.status != "ready-for-confirmation":
                return ConfirmationResult(error=self._error("package-not-ready", "prepare-package", package.status))
            source = self._read(package.source_package_digest, CanonicalSourcePackage)
            policy = self._read(package.policy_digest, PreparePolicy)
            terminology = self._read(package.terminology_sheet_digest, EditorialSheet)
            style = self._read(package.style_sheet_digest, EditorialSheet)
            persisted_findings = self._read(package.findings_digest, PreparationFindings)
            persisted_manifest = self._read(package.manifest_digest, UnitManifest)
            findings = list(self._validate_inputs(source, policy, (terminology, style), package.run_snapshot_digest))
            if self._has_blocking_findings(policy, findings):
                return ConfirmationResult(error=self._error("package-findings-block-signing", "prepare-package", "persisted source has blocking converter findings"))
            selected = self._document.select(source)
            if selected.error is not None:
                return ConfirmationResult(error=selected.error)
            rebuilt_manifest, selection_findings = self._derive_manifest(source, package.run_snapshot_digest, selected.slots, None)
            findings.extend(selection_findings)
            if self._has_blocking_findings(policy, findings):
                return ConfirmationResult(error=self._error("package-findings-block-signing", "prepare-package", "blocking findings present"))
            self._validate_sheet_scopes((terminology, style), rebuilt_manifest)
            rebuilt_findings = PreparationFindings(findings=tuple(findings))
            rebuilt_package = PreparePackage(
                source_package_digest=package.source_package_digest, run_snapshot_digest=package.run_snapshot_digest,
                manifest_digest=sha256_digest(canonical_bytes(rebuilt_manifest)), policy_digest=package.policy_digest,
                terminology_sheet_digest=package.terminology_sheet_digest, style_sheet_digest=package.style_sheet_digest,
                findings_digest=sha256_digest(canonical_bytes(rebuilt_findings)), ownership_profile=source.ownership_profile,
                projection_profile=source.projection_profile, segmentation_profile=source.segmentation_profile,
                status="ready-for-confirmation",
            )
            if canonical_bytes(rebuilt_manifest) != canonical_bytes(persisted_manifest):
                return ConfirmationResult(error=self._error("prepared-artifact-drift", "manifest", "recomputed manifest differs from persisted graph"))
            if canonical_bytes(rebuilt_findings) != canonical_bytes(persisted_findings):
                return ConfirmationResult(error=self._error("prepared-artifact-drift", "findings", "recomputed findings differ from persisted graph"))
            if canonical_bytes(rebuilt_package) != canonical_bytes(package):
                return ConfirmationResult(error=self._error("prepared-artifact-drift", "prepare-package", "recomputed package differs from persisted graph"))
            signed = self._signer.sign(package_digest, requested_key_id)
            if signed.error is not None:
                return ConfirmationResult(error=signed.error)
            verified = self._signer.verify(signed.signature, package_digest, requested_key_id)
            if verified.error is not None or not verified.verified:
                return ConfirmationResult(error=verified.error or self._error("signature-invalid", "signature", "signer did not verify emitted signature"))
            signature_digest = self._put(signed.signature)
            receipt = ConfirmationReceipt(package_digest=package_digest, signature_digest=signature_digest, key_id=requested_key_id, operator_id=operator_id)
            self._put(receipt)
            return ConfirmationResult(signature=signed.signature, receipt=receipt)
        except KernelValidationError as failure:
            return ConfirmationResult(error=failure.error)
        except Exception as error:
            return ConfirmationResult(error=self._error("confirmation-failure", "prepare-confirmation", f"{type(error).__name__}: {error}", retryable=True))

    def _validate_inputs(self, source: CanonicalSourcePackage, policy: PreparePolicy, sheets: tuple[EditorialSheet, ...], run_snapshot_digest: str) -> tuple[PreparationFinding, ...]:
        if not isinstance(source, CanonicalSourcePackage) or not isinstance(policy, PreparePolicy):
            raise KernelValidationError(self._error("invalid-prepare-input", "prepare", "source package and policy must be strict contracts"))
        if not is_sha256_digest(run_snapshot_digest):
            raise KernelValidationError(self._error("invalid-run-snapshot", "run-snapshot", repr(run_snapshot_digest)))
        self._assert_policy_compatible(source, policy)
        self._sheets(sheets)
        findings = list(source.converter_findings)
        return tuple(findings)

    @staticmethod
    def _has_blocking_findings(policy: PreparePolicy, findings: Iterable[PreparationFinding]) -> bool:
        return any(
            finding.severity == "blocking-error" or not policy.allow_warnings
            for finding in findings
        )

    @staticmethod
    def _assert_policy_compatible(source: CanonicalSourcePackage, policy: PreparePolicy) -> None:
        expected = (
            ("ownership", policy.accepted_ownership_profile_id, policy.accepted_ownership_profile_version, source.ownership_profile.profile_id, source.ownership_profile.profile_version),
            ("projection", policy.accepted_projection_profile_id, policy.accepted_projection_profile_version, source.projection_profile.profile_id, source.projection_profile.profile_version),
            ("segmentation", policy.accepted_segmentation_profile_id, policy.accepted_segmentation_profile_version, source.segmentation_profile.profile_id, source.segmentation_profile.profile_version),
        )
        mismatches = tuple(
            f"{name} policy={policy_id}@{policy_version} source={source_id}@{source_version}"
            for name, policy_id, policy_version, source_id, source_version in expected
            if (policy_id, policy_version) != (source_id, source_version)
        )
        if mismatches:
            raise KernelValidationError(PrepareWorkflow._error(
                "profile-incompatible", "prepare-policy", "; ".join(mismatches),
            ))

    @staticmethod
    def _sheets(sheets: tuple[EditorialSheet, ...]) -> tuple[EditorialSheet, EditorialSheet]:
        if len(sheets) != 2:
            raise KernelValidationError(PrepareWorkflow._error("editorial-sheet-cardinality", "editorial-sheets", "exactly one terminology and one style sheet are required"))
        by_kind = {sheet.kind: sheet for sheet in sheets}
        if len(by_kind) != 2 or set(by_kind) != {EditorialSheetKind.TERMINOLOGY, EditorialSheetKind.STYLE}:
            raise KernelValidationError(PrepareWorkflow._error("editorial-sheet-cardinality", "editorial-sheets", "unique terminology and style sheets are required"))
        if any(sheet.state is not EditorialSheetState.CONFIRMED for sheet in by_kind.values()):
            raise KernelValidationError(PrepareWorkflow._error("editorial-sheet-unconfirmed", "editorial-sheets", "all sheets must be confirmed"))
        return by_kind[EditorialSheetKind.TERMINOLOGY], by_kind[EditorialSheetKind.STYLE]

    def _derive_manifest(self, source: CanonicalSourcePackage, run_snapshot_digest: str, slots: tuple[SelectedSourceSlot, ...], prior_manifest: UnitManifest | None) -> tuple[UnitManifest, tuple[PreparationFinding, ...]]:
        records: list[UnitRecord] = []
        for ordinal, slot in enumerate(slots):
            unit_id = derive_typed_id("source-unit", {
                "source_html_digest": source.source_html_digest, "location": slot.location.model_dump(mode="json"),
                "segmentation_profile": {"id": source.segmentation_profile.profile_id, "version": source.segmentation_profile.profile_version},
                "ordinal": ordinal,
            })
            records.append(UnitRecord(
                source_unit_id=unit_id, ordinal=ordinal, locator=slot.locator, source_digest=source.source_html_digest,
                content_class=slot.content_class, eligibility=slot.eligibility, eligibility_reason=slot.eligibility_reason,
                lifecycle_state=UnitLifecycleState.PREPARED,
                structural_location=slot.location, structural_fingerprint=slot.structural_fingerprint, source_text_digest=slot.text_digest,
            ))
        self._assert_prior_integrity(source, records, prior_manifest)
        by_location = {record.structural_location: record for record in records}
        groups: list[ProjectionMap] = []
        changed_records = {record.source_unit_id: record for record in records}
        for declared in source.projection_profile.projections:
            members = tuple(by_location.get(location) for location in declared.member_locations)
            if any(member is None for member in members):
                return self._blocked_manifest(source, run_snapshot_digest, records, f"declared projection {declared.projection_key!r} has missing or blank members")
            typed_members = tuple(member for member in members if member is not None)
            if len({member.eligibility for member in typed_members}) != 1 or len({member.content_class for member in typed_members}) != 1:
                return self._blocked_manifest(source, run_snapshot_digest, records, f"declared projection {declared.projection_key!r} has incompatible members")
            group_id = derive_typed_id("projection-group", {"profile": source.projection_profile.model_dump(mode="json"), "key": declared.projection_key, "members": tuple(location.model_dump(mode="json") for location in declared.member_locations)})
            canonical = min(typed_members, key=lambda record: record.ordinal)
            groups.append(ProjectionMap(group_id=group_id, canonical_source_unit_id=canonical.source_unit_id, member_locators=tuple(member.locator for member in typed_members), ownership=ProjectionOwnership.BOOK, cardinality=len(typed_members), transformation_rule=declared.transformation_rule))
            for member in typed_members:
                changed_records[member.source_unit_id] = member.model_copy(update={"projection_group_id": group_id})
        units = tuple(sorted(changed_records.values(), key=lambda record: record.ordinal))
        findings: list[PreparationFinding] = []
        if any(record.eligibility is Eligibility.UNSUPPORTED for record in units):
            findings.append(self._finding("unsupported-book-owned-content", "inventory", "at least one selected book-owned slot is unsupported"))
        if not any(record.eligibility is Eligibility.REQUIRED for record in units):
            findings.append(self._finding("empty-required-inventory", "inventory", "no required source units were selected"))
        manifest = UnitManifest(source_package_digest=sha256_digest(canonical_bytes(source)), run_snapshot_digest=run_snapshot_digest, segmentation_profile_id=source.segmentation_profile.profile_id, segmentation_profile_version=source.segmentation_profile.profile_version, profile_id=source.ownership_profile.profile_id, units=units, projection_groups=tuple(groups), status=StatusVector(processing=StatusValue.COMPLETE if not findings else StatusValue.BLOCKED, completeness=StatusValue.COMPLETE if not findings else StatusValue.INCOMPLETE, compliance=StatusValue.CLEAN if not findings else StatusValue.FAILED, review=StatusValue.NOT_STARTED, publication=StatusValue.READY if not findings else StatusValue.NOT_READY), provenance=())
        return manifest, tuple(findings)

    def _blocked_manifest(self, source: CanonicalSourcePackage, run_snapshot_digest: str, records: list[UnitRecord], observed: str) -> tuple[UnitManifest, tuple[PreparationFinding, ...]]:
        manifest = UnitManifest(source_package_digest=sha256_digest(canonical_bytes(source)), run_snapshot_digest=run_snapshot_digest, segmentation_profile_id=source.segmentation_profile.profile_id, segmentation_profile_version=source.segmentation_profile.profile_version, profile_id=source.ownership_profile.profile_id, units=tuple(records), projection_groups=(), status=StatusVector(processing=StatusValue.BLOCKED, completeness=StatusValue.INCOMPLETE, compliance=StatusValue.FAILED, review=StatusValue.NOT_STARTED, publication=StatusValue.NOT_READY), provenance=())
        return manifest, (self._finding("invalid-declared-projection", "projection-profile", observed),)

    @staticmethod
    def _assert_prior_integrity(source: CanonicalSourcePackage, records: Iterable[UnitRecord], prior: UnitManifest | None) -> None:
        if prior is None or prior.segmentation_profile_id != source.segmentation_profile.profile_id or prior.segmentation_profile_version != source.segmentation_profile.profile_version:
            return
        old = {(record.structural_location, record.ordinal): record for record in prior.units if record.structural_location is not None}
        for record in records:
            previous = old.get((record.structural_location, record.ordinal))
            if previous is not None and previous.source_text_digest != record.source_text_digest:
                raise KernelValidationError(PrepareWorkflow._error("source-text-digest-mismatch", "source-unit", "prior locator/profile identity has changed exact source text"))

    @staticmethod
    def _validate_sheet_scopes(sheets: tuple[EditorialSheet, EditorialSheet], manifest: UnitManifest) -> None:
        required = {record.source_unit_id for record in manifest.units if record.eligibility is Eligibility.REQUIRED}
        for sheet in sheets:
            for rule in sheet.rules:
                if not set(rule.required_unit_ids).issubset(required):
                    raise KernelValidationError(PrepareWorkflow._error("editorial-scope-invalid", "editorial-sheet", f"rule {rule.rule_id!r} names a non-required or unknown unit"))

    def _blocked(self, run_id: str, findings: list[PreparationFinding], attempt: int, attempt_ceiling: int) -> PrepareExecutionResult:
        operational = tuple(OperationalFinding(code=finding.code, message=finding.observed) for finding in findings)
        recorded = self._store.record_outcome(run_id, stage_id="prepare", outcome=OperationalOutcome.RECONCILIATION_REQUIRED, attempt=attempt, attempt_ceiling=attempt_ceiling, findings=operational, retry_guidance="Resolve the preparation findings and rerun from the canonical source package.")
        if recorded.error is not None:
            return PrepareExecutionResult(error=recorded.error)
        return PrepareExecutionResult(value=PrepareResult(outcome=PreparationOutcome(status="blocked", findings=tuple(findings))))

    def _put(self, value) -> str:
        result = self._store.put_object(value)
        if result.error is not None or result.digest is None:
            raise KernelValidationError(result.error or self._error("artifact-write-failed", "artifact", "store returned no digest", retryable=True))
        return result.digest

    def _read(self, digest: str, model):
        result = self._store.read_object(digest, model)
        if result.error is not None or result.value is None:
            raise KernelValidationError(result.error or self._error("artifact-read-failed", "artifact", "store returned no value", retryable=True))
        return result.value

    @staticmethod
    def _finding(code: str, subject: str, observed: str) -> PreparationFinding:
        return PreparationFinding(code=code, severity="blocking-error", subject=subject, observed=observed, next_action="Repair the source or profile and restart preparation.")

    @staticmethod
    def _finding_from_error(error: ActionableError) -> PreparationFinding:
        return PreparationFinding(code=error.code, severity="blocking-error", subject=error.subject, observed=error.observed, next_action=error.next_action)

    @staticmethod
    def _error(code: str, subject: str, observed: str, *, retryable: bool = False) -> ActionableError:
        return actionable_error(code=code, workflow="prepare", subject=subject, rule="frozen-fixture-prepare", expected="a deterministic compatible preparation graph", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Correct the persisted preparation graph and restart from canonical source.")
