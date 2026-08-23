"""Exception-safe validation gates for workflow adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Generic, TypeVar

from pydantic import ValidationError

from .canonical import HostileJsonError, load_strict_json, reject_floats
from .compatibility import contract_type_name, ensure_compatible
from .contracts import CompatibilityMetadata, KernelModel, VersionedContract
from .errors import ActionableError, KernelValidationError, actionable_error
from .identity import is_sha256_digest, source_text_digest

T = TypeVar("T", bound=KernelModel)
R = TypeVar("R")


class BoundaryResult(KernelModel, Generic[T]):
    value: T | None = None
    error: ActionableError | None = None


class BoundaryExecutionResult(KernelModel, Generic[R]):
    value: R | None = None
    error: ActionableError | None = None


def _error_from_exception(error: Exception, workflow: str, subject: str) -> ActionableError:
    if isinstance(error, KernelValidationError):
        return error.error
    if isinstance(error, HostileJsonError):
        code, rule = "malformed-artifact", "hostile-json"
    elif isinstance(error, ValidationError):
        code, rule = "malformed-artifact", "strict-schema"
    else:
        code, rule = "malformed-artifact", "boundary-validation"
    return actionable_error(
        code=code,
        workflow=workflow,
        subject=subject,
        rule=rule,
        expected="a strict, compatible versioned artifact",
        observed=str(error) or type(error).__name__,
        next_action="Correct the artifact and submit it again.",
    )


def _ensure_nested_initial_versions(value: object, *, workflow: str, subject: str) -> None:
    """Reject stale child contracts too; a valid envelope cannot hide one."""

    if isinstance(value, VersionedContract):
        ensure_compatible(
            value,
            CompatibilityMetadata(
                contract_name=contract_type_name(value), accepted_versions=(1,)
            ),
            workflow=workflow,
            subject=subject,
        )
        for field_name in type(value).model_fields:
            _ensure_nested_initial_versions(
                getattr(value, field_name), workflow=workflow, subject=subject
            )
    elif isinstance(value, tuple):
        for item in value:
            _ensure_nested_initial_versions(item, workflow=workflow, subject=subject)


def validate_boundary(
    raw: str | bytes | bytearray | Mapping[str, Any] | None,
    model_type: type[T],
    *,
    workflow: str,
    subject: str = "artifact",
    compatibility: CompatibilityMetadata | None = None,
) -> BoundaryResult[T]:
    """Validate hostile raw input without letting exceptions escape a workflow gate."""

    if raw is None:
        return BoundaryResult(
            error=actionable_error(
                code="missing-artifact",
                workflow=workflow,
                subject=subject,
                rule="required-input",
                expected="a versioned artifact",
                observed="missing",
                next_action="Provide the required artifact.",
            )
        )
    try:
        if isinstance(raw, (str, bytes, bytearray)):
            # Inspect pairs before Pydantic sees JSON, then let its JSON mode retain tuples.
            load_strict_json(raw)
            value = model_type.model_validate_json(raw)
        else:
            reject_floats(raw)
            value = model_type.model_validate(raw)
        if compatibility is not None:
            ensure_compatible(value, compatibility, workflow=workflow, subject=subject)
        elif isinstance(value, VersionedContract):
            # Every initial kernel contract is explicitly version 1.  A workflow
            # that accepts another version must declare that compatibility instead.
            ensure_compatible(
                value,
                CompatibilityMetadata(
                    contract_name=contract_type_name(value), accepted_versions=(1,)
                ),
                workflow=workflow,
                subject=subject,
            )
        if isinstance(value, VersionedContract):
            for field_name in type(value).model_fields:
                _ensure_nested_initial_versions(
                    getattr(value, field_name), workflow=workflow, subject=subject
                )
        return BoundaryResult(value=value)
    except Exception as error:  # Boundary APIs intentionally convert every validation error.
        return BoundaryResult(error=_error_from_exception(error, workflow, subject))


def guard_source_text(
    source_text: str,
    expected_digest: str,
    *,
    workflow: str,
    subject: str = "source-text",
) -> BoundaryResult[VersionedContract]:
    """Return a stable terminal error when exact source text no longer matches."""

    if not isinstance(source_text, str):
        return BoundaryResult(
            error=actionable_error(
                code="malformed-source-text",
                workflow=workflow,
                subject=subject,
                rule="source-text-type",
                expected="a UTF-8 encodable string",
                observed=type(source_text).__name__,
                next_action="Provide exact source text as a string.",
            )
        )
    if not isinstance(expected_digest, str) or not is_sha256_digest(expected_digest):
        return BoundaryResult(
            error=actionable_error(
                code="malformed-source-text-digest",
                workflow=workflow,
                subject=subject,
                rule="lowercase-sha256-digest",
                expected="a lowercase SHA-256 digest",
                observed=repr(expected_digest),
                next_action="Provide the expected canonical source digest.",
            )
        )
    try:
        observed = source_text_digest(source_text)
    except UnicodeError as error:
        return BoundaryResult(
            error=actionable_error(
                code="malformed-source-text",
                workflow=workflow,
                subject=subject,
                rule="source-text-utf8",
                expected="UTF-8 encodable source text",
                observed=str(error) or type(error).__name__,
                next_action="Remove invalid Unicode surrogate data from source text.",
            )
        )
    if observed == expected_digest:
        # No content object is introduced only for a guard; success has no payload.
        return BoundaryResult()
    return BoundaryResult(
        error=actionable_error(
            code="source-text-digest-mismatch",
            workflow=workflow,
            subject=subject,
            rule="exact-source-digest",
            expected=expected_digest,
            observed=observed,
            next_action="Restart from the matching canonical source package.",
        )
    )


def run_boundary(
    raw: str | bytes | bytearray | Mapping[str, Any] | None,
    model_type: type[T],
    feature: Callable[[T], R],
    *,
    workflow: str,
    subject: str = "artifact",
    compatibility: CompatibilityMetadata | None = None,
) -> BoundaryExecutionResult[R]:
    """Only invoke feature logic after validation; convert feature failure as well."""

    validated = validate_boundary(
        raw, model_type, workflow=workflow, subject=subject, compatibility=compatibility
    )
    if validated.error is not None:
        return BoundaryExecutionResult(error=validated.error)
    try:
        return BoundaryExecutionResult(value=feature(validated.value))  # type: ignore[arg-type]
    except KernelValidationError as error:
        return BoundaryExecutionResult(error=error.error)
    except Exception as error:
        return BoundaryExecutionResult(
            error=actionable_error(
                code="workflow-feature-failure",
                workflow=workflow,
                subject=subject,
                rule="feature-execution",
                expected="feature logic to complete",
                observed=str(error) or type(error).__name__,
                next_action="Inspect the workflow failure and retry only if safe.",
            )
        )
