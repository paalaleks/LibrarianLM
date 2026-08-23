"""The single, strict, immutable cross-workflow contract family."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator

from .identity import (
    ComponentId,
    DomLocator,
    ProjectionGroupId,
    Sha256Digest,
    SourceUnitId,
    TokenId,
)
from .lifecycle import UnitLifecycleState

__all__ = [
    "ArtifactReference",
    "AssemblyReport",
    "BookFinding",
    "CompatibilityMetadata",
    "ComponentIdentity",
    "ContentClass",
    "ContextArtifact",
    "ContextBundle",
    "ContextDecision",
    "ContextRole",
    "Eligibility",
    "Evaluation",
    "FailedUnit",
    "Finding",
    "GatewayReceipt",
    "HumanEditSet",
    "InlineBindingMap",
    "KernelModel",
    "MachineFinal",
    "ModelParameter",
    "ModelRequest",
    "ModelResponse",
    "ModelTool",
    "ModelUsage",
    "ProjectionMap",
    "ProjectionOwnership",
    "Proposal",
    "ProvenanceKind",
    "ProvenanceObject",
    "ProvenanceReference",
    "RecoveryCandidate",
    "RunComparison",
    "StatusValue",
    "StatusVector",
    "TokenEntry",
    "TranslationRunSummary",
    "TypedLocator",
    "UnitManifest",
    "UnitRecord",
    "UsefulnessEvaluationReport",
    "ValidationReport",
    "VersionedContract",
]


class KernelModel(BaseModel):
    """Shared policy: contracts reject coercion, extra data, and mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class VersionedContract(KernelModel):
    schema_version: StrictInt = Field(default=1, ge=1)


class ArtifactReference(VersionedContract):
    kind: StrictStr = Field(min_length=1)
    digest: Sha256Digest


class ProvenanceKind(StrEnum):
    PROPOSAL = "proposal"
    EVALUATION = "evaluation"
    RECOVERY_CANDIDATE = "recovery-candidate"
    MACHINE_FINAL = "machine-final"
    FAILED_UNIT = "failed-unit"
    HUMAN_EDIT_SET = "human-edit-set"
    BOOK_FINDING = "book-finding"
    GATEWAY_RECEIPT = "gateway-receipt"


class ProvenanceReference(VersionedContract):
    kind: ProvenanceKind
    digest: Sha256Digest


class TypedLocator(VersionedContract):
    locator: DomLocator
    kind: StrictStr = Field(min_length=1)


class Eligibility(StrEnum):
    REQUIRED = "required"
    EXCLUDED = "excluded"
    UNSUPPORTED = "unsupported"


class ContentClass(StrEnum):
    TEXT = "text"
    TAIL = "tail"
    ATTRIBUTE = "attribute"


class UnitRecord(VersionedContract):
    source_unit_id: SourceUnitId
    ordinal: StrictInt = Field(ge=0)
    locator: TypedLocator
    source_digest: Sha256Digest
    content_class: ContentClass
    eligibility: Eligibility
    eligibility_reason: StrictStr = Field(min_length=1)
    projection_group_id: ProjectionGroupId
    inline_binding_map_digest: Sha256Digest | None = None
    lifecycle_state: UnitLifecycleState
    proposal: ProvenanceReference | None = None
    evaluation: ProvenanceReference | None = None
    recovery_candidate: ProvenanceReference | None = None
    machine_final: ProvenanceReference | None = None
    failed_unit: ProvenanceReference | None = None

    @model_validator(mode="after")
    def eligibility_reason_is_meaningful(self) -> "UnitRecord":
        if not self.eligibility_reason.strip():
            raise ValueError("every eligibility value requires a nonempty reason")
        return self


class StatusValue(StrEnum):
    UNKNOWN = "unknown"
    NOT_STARTED = "not-started"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    BLOCKED = "blocked"
    CLEAN = "clean"
    NOT_READY = "not-ready"
    READY = "ready"


class StatusVector(VersionedContract):
    """Five facts, deliberately with no cross-field implications or validators."""

    processing: StatusValue
    completeness: StatusValue
    compliance: StatusValue
    review: StatusValue
    publication: StatusValue


class TokenEntry(VersionedContract):
    token_id: TokenId
    kind: StrictStr = Field(min_length=1)
    source_order_ordinal: StrictInt = Field(ge=0)
    locator: TypedLocator
    source_node: StrictStr = Field(min_length=1)
    source_attributes: tuple[StrictStr, ...] = ()
    pair_id: TokenId | None = None
    placement_rule: StrictStr = Field(min_length=1)


class InlineBindingMap(VersionedContract):
    source_unit_id: SourceUnitId
    source_digest: Sha256Digest
    entries: tuple[TokenEntry, ...]
    map_digest: Sha256Digest


class ContextRole(StrEnum):
    SOURCE = "source"
    TARGET = "target"


class ContextArtifact(VersionedContract):
    role: ContextRole
    source_order_ordinal: StrictInt = Field(ge=0)
    reference: ArtifactReference
    rendered_fragment: StrictStr


class ContextDecision(VersionedContract):
    subject: StrictStr = Field(min_length=1)
    decision: Literal["included", "truncated", "absent"]
    reason: StrictStr = Field(min_length=1)


class ContextBundle(VersionedContract):
    source_unit_id: SourceUnitId
    policy_digest: Sha256Digest
    artifacts: tuple[ContextArtifact, ...]
    token_budget: StrictInt = Field(ge=0)
    decisions: tuple[ContextDecision, ...]
    rendered_bytes_digest: Sha256Digest

    @model_validator(mode="after")
    def artifacts_follow_canonical_source_order(self) -> "ContextBundle":
        ordinals = tuple(artifact.source_order_ordinal for artifact in self.artifacts)
        if ordinals != tuple(sorted(ordinals)):
            raise ValueError("context artifacts must use nondecreasing source-order ordinals")
        return self


class ProjectionOwnership(StrEnum):
    BOOK = "book-owned"
    WORKFLOW = "workflow-owned"


class ProjectionMap(VersionedContract):
    group_id: ProjectionGroupId
    canonical_source_unit_id: SourceUnitId
    member_locators: tuple[TypedLocator, ...]
    ownership: ProjectionOwnership
    cardinality: StrictInt = Field(ge=1)
    transformation_rule: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def cardinality_matches_members(self) -> "ProjectionMap":
        if not self.member_locators:
            raise ValueError("projection maps require at least one member locator")
        if self.cardinality != len(self.member_locators):
            raise ValueError("projection cardinality must equal member locator count")
        return self


class ModelParameter(VersionedContract):
    name: StrictStr = Field(min_length=1)
    canonical_value: StrictStr


class ModelTool(VersionedContract):
    name: StrictStr = Field(min_length=1)
    canonical_definition: StrictStr


class ModelRequest(VersionedContract):
    rendered_input: StrictStr
    rendered_input_digest: Sha256Digest
    context_bundle_digest: Sha256Digest
    prompt_digest: Sha256Digest
    method_digest: Sha256Digest
    provider: StrictStr = Field(min_length=1)
    model_revision: StrictStr = Field(min_length=1)
    parameters: tuple[ModelParameter, ...]
    tools: tuple[ModelTool, ...]
    idempotency_key: StrictStr = Field(min_length=1)


class ModelUsage(VersionedContract):
    input_tokens: StrictInt = Field(ge=0)
    output_tokens: StrictInt = Field(ge=0)


class ModelResponse(VersionedContract):
    normalized_response: StrictStr
    usage: ModelUsage
    finish_reason: StrictStr = Field(min_length=1)
    provider_request_id: StrictStr = Field(min_length=1)
    gateway_receipt_digest: Sha256Digest


class GatewayReceipt(VersionedContract):
    request_digest: Sha256Digest
    response_digest: Sha256Digest


class ProvenanceObject(VersionedContract):
    source_unit_id: SourceUnitId
    references: tuple[ProvenanceReference, ...] = ()


class Proposal(ProvenanceObject):
    value: StrictStr
    request_digest: Sha256Digest
    response_digest: Sha256Digest


class Evaluation(ProvenanceObject):
    proposal_digest: Sha256Digest
    outcome: StrictStr = Field(min_length=1)


class RecoveryCandidate(ProvenanceObject):
    value: StrictStr
    predecessor_evaluation_digest: Sha256Digest


class MachineFinal(ProvenanceObject):
    value: StrictStr
    proposal_digest: Sha256Digest
    evaluation_digest: Sha256Digest


class FailedUnit(ProvenanceObject):
    failure_code: StrictStr = Field(min_length=1)
    exhausted: StrictBool


class HumanEditSet(ProvenanceObject):
    selected_value_digest: Sha256Digest


class BookFinding(ProvenanceObject):
    rule: StrictStr = Field(min_length=1)
    severity: Literal["blocking-error", "warning"]


class Finding(VersionedContract):
    code: StrictStr = Field(min_length=1)
    severity: Literal["blocking-error", "warning"]
    subject: StrictStr = Field(min_length=1)
    rule: StrictStr = Field(min_length=1)
    observed: StrictStr = Field(min_length=1)


class AssemblyReport(VersionedContract):
    manifest_digest: Sha256Digest
    findings: tuple[Finding, ...]


class ValidationReport(VersionedContract):
    manifest_digest: Sha256Digest
    findings: tuple[Finding, ...]
    status: StatusVector


class TranslationRunSummary(VersionedContract):
    manifest_digest: Sha256Digest
    status: StatusVector
    report_references: tuple[ArtifactReference, ...]


class RunComparison(VersionedContract):
    left_run_digest: Sha256Digest
    right_run_digest: Sha256Digest
    outcome: Literal["equivalent", "non-equivalent"]


class UsefulnessEvaluationReport(VersionedContract):
    run_digest: Sha256Digest
    findings: tuple[Finding, ...]


class ComponentIdentity(VersionedContract):
    implementation: ComponentId
    implementation_version: StrictStr = Field(min_length=1)
    platform_abi: StrictStr = Field(min_length=1)
    uv_lock_digest: Sha256Digest
    package_versions: tuple[ModelParameter, ...]
    lxml_version: StrictStr = Field(min_length=1)
    libxml_version: StrictStr = Field(min_length=1)
    libxslt_version: StrictStr = Field(min_length=1)
    html_serialization_fixture_digest: Sha256Digest


class CompatibilityMetadata(VersionedContract):
    contract_name: StrictStr = Field(min_length=1)
    accepted_versions: tuple[StrictInt, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def accepted_versions_are_positive_and_unique(self) -> "CompatibilityMetadata":
        if any(version < 1 for version in self.accepted_versions):
            raise ValueError("accepted versions must be positive")
        if len(set(self.accepted_versions)) != len(self.accepted_versions):
            raise ValueError("accepted versions must be unique")
        return self


class UnitManifest(VersionedContract):
    source_package_digest: Sha256Digest
    run_snapshot_digest: Sha256Digest
    segmentation_profile_id: ComponentId
    profile_id: ComponentId
    units: tuple[UnitRecord, ...]
    projection_groups: tuple[ProjectionMap, ...]
    status: StatusVector
    provenance: tuple[ProvenanceReference, ...]

    @model_validator(mode="after")
    def references_form_one_consistent_inventory(self) -> "UnitManifest":
        ordinals = tuple(unit.ordinal for unit in self.units)
        source_unit_ids = tuple(unit.source_unit_id for unit in self.units)
        projection_group_ids = tuple(group.group_id for group in self.projection_groups)
        if ordinals != tuple(sorted(ordinals)) or len(set(ordinals)) != len(ordinals):
            raise ValueError("unit ordinals must be strictly increasing and unique")
        if len(set(source_unit_ids)) != len(source_unit_ids):
            raise ValueError("source unit IDs must be unique")
        if len(set(projection_group_ids)) != len(projection_group_ids):
            raise ValueError("projection group IDs must be unique")
        source_units = set(source_unit_ids)
        groups = set(projection_group_ids)
        if any(group.canonical_source_unit_id not in source_units for group in self.projection_groups):
            raise ValueError("projection canonical source units must exist in the manifest")
        if any(unit.projection_group_id not in groups for unit in self.units):
            raise ValueError("every unit projection group must resolve in the manifest")
        return self
