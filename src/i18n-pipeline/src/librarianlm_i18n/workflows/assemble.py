"""Fail-closed fixture assembly for confirmed Prepare graphs."""

from __future__ import annotations

import re

from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.kernel.contracts import (
    ApplicationEvidence, AssemblyReport, AssemblyResult, CandidateDraft, CanonicalSourcePackage,
    ConfirmationReceipt, FixtureTargets, InlineBindingMap, PreparePackage,
    ProtectedBlockSegments, SignatureRecord, StatusValue, UnitManifest,
)
from librarianlm_i18n.kernel.errors import ActionableError, KernelValidationError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import sha256_digest, source_text_digest
from librarianlm_i18n.kernel.contracts import Eligibility
from librarianlm_i18n.ports.artifact_store import ArtifactStore
from librarianlm_i18n.ports.html_document import HtmlDocument
from librarianlm_i18n.ports.package_signer import PackageSigner


class AssemblyExecutionResult:
    def __init__(self, *, value: AssemblyResult | None = None, error: ActionableError | None = None) -> None:
        if (value is None) == (error is None):
            raise ValueError("assembly execution results require exactly one value or error")
        self.value = value
        self.error = error


class AssemblyWorkflow:
    """Assemble only confirmed fixture values into a secured source clone."""

    def __init__(self, *, store: ArtifactStore, document: HtmlDocument, signer: PackageSigner) -> None:
        self._store = store
        self._document = document
        self._signer = signer

    def assemble(self, *, package_digest: str, confirmation: ConfirmationReceipt, fixture_targets: FixtureTargets) -> AssemblyExecutionResult:
        try:
            package = self._read(package_digest, PreparePackage)
            if confirmation.package_digest != package_digest:
                raise KernelValidationError(self._error("confirmation-package-mismatch", "confirmation", "receipt does not bind supplied package"))
            signature = self._read(confirmation.signature_digest, SignatureRecord)
            verified = self._signer.verify(signature, package_digest, confirmation.key_id)
            if verified.error is not None or not verified.verified:
                raise KernelValidationError(verified.error or self._error("signature-invalid", "confirmation", "trusted signer declined signature"))
            manifest = self._read(package.manifest_digest, UnitManifest)
            if manifest.source_package_digest != package.source_package_digest:
                raise KernelValidationError(self._error("manifest-source-mismatch", "manifest", "manifest does not bind the package canonical source"))
            self._assert_ready_manifest(manifest)
            source = self._read(package.source_package_digest, CanonicalSourcePackage)
            expected = tuple(unit for unit in manifest.units if unit.eligibility is Eligibility.REQUIRED and self._is_canonical(unit, manifest))
            supplied = {target.source_unit_id: target.value for target in fixture_targets.targets}
            expected_ids = {unit.source_unit_id for unit in expected}
            if tuple(target.source_unit_id for target in fixture_targets.targets) != tuple(unit.source_unit_id for unit in expected) or set(supplied) != expected_ids:
                missing = tuple(unit.source_unit_id for unit in expected if unit.source_unit_id not in supplied)
                unused = tuple(target.source_unit_id for target in fixture_targets.targets if target.source_unit_id not in expected_ids)
                raise KernelValidationError(self._error("fixture-target-inventory-mismatch", "fixture-targets", f"missing={missing!r}; unused={unused!r}"))
            cloned = self._document.clone(source)
            if cloned.error is not None:
                raise KernelValidationError(cloned.error)
            applied: list[str] = []
            applied_members: list[str] = []
            map_cache: dict[str, InlineBindingMap] = {}
            for canonical in expected:
                members = self._members(canonical, manifest)
                canonical_map = self._load_protected(canonical, map_cache)
                value = supplied[canonical.source_unit_id]
                for member in members:
                    member_value = value
                    member_map = self._load_protected(member, map_cache)
                    if canonical_map is not None:
                        if member_map is None:
                            raise KernelValidationError(self._error("projection-binding-mismatch", "projection", "protected canonical has an unprotected member"))
                        member_value = self._remap_tokens(value, canonical_map, member_map)
                        result = self._document.rebind(cloned.document, member, member_map, member_value)
                    else:
                        if member_map is not None:
                            raise KernelValidationError(self._error("projection-binding-mismatch", "projection", "plain canonical has a protected member"))
                        result = self._document.apply_plain(cloned.document, member, member_value)
                    if result.error is not None:
                        raise KernelValidationError(result.error)
                    applied_members.append(member.source_unit_id)
                applied.append(canonical.source_unit_id)
            rendered = self._document.serialize(cloned.document)
            if rendered.error is not None:
                raise KernelValidationError(rendered.error)
            html_digest = sha256_digest(rendered.html.encode("utf-8"))
            draft = CandidateDraft(source_package_digest=package.source_package_digest, manifest_digest=package.manifest_digest, html=rendered.html, html_digest=html_digest)
            projection_digest = sha256_digest(canonical_bytes(tuple(group.model_dump(mode="json") for group in manifest.projection_groups))) if manifest.projection_groups else None
            evidence = ApplicationEvidence(manifest_digest=package.manifest_digest, applied_source_unit_ids=tuple(applied), candidate_html_digest=html_digest, target_digest=sha256_digest(canonical_bytes(fixture_targets)), projection_map_digest=projection_digest, applied_member_ids=tuple(applied_members))
            draft_digest = self._put(draft)
            evidence_digest = self._put(evidence)
            report = AssemblyReport(manifest_digest=package.manifest_digest, candidate_draft_digest=draft_digest, application_evidence_digest=evidence_digest)
            self._put(report)
            return AssemblyExecutionResult(value=AssemblyResult(report=report, draft=draft))
        except KernelValidationError as failure:
            return AssemblyExecutionResult(error=failure.error)
        except Exception as error:
            return AssemblyExecutionResult(error=self._error("assembly-failure", "assemble", f"{type(error).__name__}: {error}", retryable=True))

    @staticmethod
    def _is_canonical(unit, manifest: UnitManifest) -> bool:
        if unit.projection_group_id is None:
            return True
        group = next(group for group in manifest.projection_groups if group.group_id == unit.projection_group_id)
        return group.canonical_source_unit_id == unit.source_unit_id

    @staticmethod
    def _members(canonical, manifest: UnitManifest):
        if canonical.projection_group_id is None:
            return (canonical,)
        group = next(group for group in manifest.projection_groups if group.group_id == canonical.projection_group_id)
        if group.transformation_rule != "replace-text":
            raise KernelValidationError(AssemblyWorkflow._error("unsupported-projection-transform", "projection", group.transformation_rule))
        return tuple(unit for unit in manifest.units if unit.projection_group_id == group.group_id)

    def _load_protected(self, unit, cache: dict[str, InlineBindingMap]) -> InlineBindingMap | None:
        if unit.inline_binding_map_digest is None or unit.protected_segments_digest is None:
            if unit.inline_binding_map_digest is not None or unit.protected_segments_digest is not None:
                raise KernelValidationError(self._error("protected-artifact-incomplete", "source-unit", unit.source_unit_id))
            return None
        binding = cache.get(unit.source_unit_id)
        if binding is None:
            binding = self._read(unit.inline_binding_map_digest, InlineBindingMap)
            segments = self._read(unit.protected_segments_digest, ProtectedBlockSegments)
            rendered_segments = "".join(item.value for item in segments.segments)
            expected_tokens = tuple(f"[[[LLM:BIND:{entry.token_id}]]]" for entry in binding.entries)
            actual_tokens = tuple(re.findall(r"\[\[\[LLM:BIND:[A-Z2-7]{26}\]\]\]", rendered_segments))
            if binding.source_unit_id != unit.source_unit_id or binding.source_digest != unit.source_text_digest or segments.source_unit_id != unit.source_unit_id or segments.binding_map_digest != binding.map_digest or segments.source_digest != binding.source_digest or source_text_digest(rendered_segments) != binding.source_digest or actual_tokens != expected_tokens:
                raise KernelValidationError(self._error("protected-artifact-mismatch", "protected-block", unit.source_unit_id))
            # The source digest binds the original token stream.  Segment text is
            # independently retained for exact reassembly evidence.
            cache[unit.source_unit_id] = binding
        return binding

    @staticmethod
    def _remap_tokens(value: str, canonical: InlineBindingMap, member: InlineBindingMap) -> str:
        def topology(binding: InlineBindingMap):
            positions = {entry.token_id: index for index, entry in enumerate(binding.entries)}
            return tuple((entry.kind, entry.source_node, positions.get(entry.pair_id)) for entry in binding.entries)
        if len(canonical.entries) != len(member.entries) or topology(canonical) != topology(member):
            raise KernelValidationError(AssemblyWorkflow._error("projection-binding-mismatch", "projection", "protected member topology differs"))
        for left, right in zip(canonical.entries, member.entries, strict=True):
            value = value.replace(f"[[[LLM:BIND:{left.token_id}]]]", f"[[[LLM:BIND:{right.token_id}]]]")
        return value

    @staticmethod
    def _assert_ready_manifest(manifest: UnitManifest) -> None:
        status = manifest.status
        if not (status.processing is StatusValue.COMPLETE and status.completeness is StatusValue.COMPLETE and status.compliance is StatusValue.CLEAN and status.publication is StatusValue.READY):
            raise KernelValidationError(AssemblyWorkflow._error("manifest-not-ready", "manifest", status.model_dump_json()))

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
    def _error(code: str, subject: str, observed: str, *, retryable: bool = False) -> ActionableError:
        return actionable_error(code=code, workflow="assemble", subject=subject, rule="confirmed-fixture-assembly", expected="a complete clean ready manifest with exact confirmed fixture inputs", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Repair the confirmed artifacts or fixture targets and restart assembly.")
