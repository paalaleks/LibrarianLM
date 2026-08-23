"""Authoritative public surface for all shared i18n contracts."""

from .boundary import (
    BoundaryExecutionResult,
    BoundaryResult,
    guard_source_text,
    run_boundary,
    validate_boundary,
)
from .canonical import HostileJsonError, canonical_bytes, load_strict_json
from .compatibility import ensure_compatible
from .contracts import *  # noqa: F403
from .contracts import __all__ as _CONTRACT_EXPORTS
from .errors import ActionableError, KernelValidationError, Retryability
from .identity import *  # noqa: F403
from .identity import __all__ as _IDENTITY_EXPORTS
from .lifecycle import TERMINAL_STATES, UnitLifecycleState, legal_next_states, validate_transition

__all__ = [
    "ActionableError",
    "BoundaryExecutionResult",
    "BoundaryResult",
    "HostileJsonError",
    "KernelValidationError",
    "Retryability",
    "TERMINAL_STATES",
    "UnitLifecycleState",
    "canonical_bytes",
    "ensure_compatible",
    "guard_source_text",
    "legal_next_states",
    "load_strict_json",
    "run_boundary",
    "validate_boundary",
    "validate_transition",
] + _CONTRACT_EXPORTS + _IDENTITY_EXPORTS
