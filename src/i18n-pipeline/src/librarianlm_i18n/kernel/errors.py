"""Stable, serializable errors used at workflow boundaries."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class Retryability(StrEnum):
    RETRYABLE = "retryable"
    NOT_RETRYABLE = "not-retryable"


class ActionableError(BaseModel):
    """A complete error payload suitable for a workflow adapter to return."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: StrictStr = Field(min_length=1)
    workflow: StrictStr = Field(min_length=1)
    subject: StrictStr = Field(min_length=1)
    rule: StrictStr = Field(min_length=1)
    expected: StrictStr = Field(min_length=1)
    observed: StrictStr = Field(min_length=1)
    retryability: Retryability
    next_action: StrictStr = Field(min_length=1)


class KernelValidationError(ValueError):
    """Internal exception carrying the stable error that a boundary must return."""

    def __init__(self, error: ActionableError) -> None:
        self.error = error
        super().__init__(error.code)


def actionable_error(
    *,
    code: str,
    workflow: str,
    subject: str,
    rule: str,
    expected: str,
    observed: str,
    retryability: Retryability = Retryability.NOT_RETRYABLE,
    next_action: str,
) -> ActionableError:
    return ActionableError(
        code=code,
        workflow=workflow,
        subject=subject,
        rule=rule,
        expected=expected,
        observed=observed,
        retryability=retryability,
        next_action=next_action,
    )
