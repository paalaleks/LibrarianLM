"""Explicit version acceptance checks shared by all workflow boundaries."""

from __future__ import annotations

import re

from .contracts import CompatibilityMetadata, VersionedContract
from .errors import KernelValidationError, actionable_error


def contract_type_name(artifact: VersionedContract) -> str:
    """Convert the authoritative Python type name to its wire contract name."""

    return re.sub(r"(?<!^)(?=[A-Z])", "-", type(artifact).__name__).lower()


def ensure_compatible(
    artifact: VersionedContract,
    metadata: CompatibilityMetadata,
    *,
    workflow: str,
    subject: str = "artifact",
) -> None:
    """Raise a stable internal error when the artifact version is unaccepted."""

    expected_name = contract_type_name(artifact)
    if metadata.contract_name != expected_name:
        raise KernelValidationError(
            actionable_error(
                code="incompatible-artifact-contract",
                workflow=workflow,
                subject=subject,
                rule="contract-name-match",
                expected=expected_name,
                observed=metadata.contract_name,
                next_action="Use compatibility metadata for this artifact contract.",
            )
        )
    if artifact.schema_version in metadata.accepted_versions:
        return
    accepted = ",".join(str(version) for version in metadata.accepted_versions)
    raise KernelValidationError(
        actionable_error(
            code="incompatible-artifact-version",
            workflow=workflow,
            subject=subject,
            rule="accepted-schema-version",
            expected=accepted,
            observed=str(artifact.schema_version),
            next_action="Provide an artifact with an accepted schema version.",
        )
    )
