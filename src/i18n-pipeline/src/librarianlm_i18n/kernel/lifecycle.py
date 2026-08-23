"""The complete monotonic Source Unit lifecycle transition table."""

from __future__ import annotations

from enum import StrEnum

from .errors import KernelValidationError, actionable_error


class UnitLifecycleState(StrEnum):
    PREPARED = "prepared"
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    RECOVERY_PENDING = "recovery-pending"
    RECOVERY_PROPOSED = "recovery-proposed"
    RECOVERY_EVALUATED = "recovery-evaluated"
    COMMITTED = "committed"
    FAILED = "failed"


TERMINAL_STATES = frozenset({UnitLifecycleState.COMMITTED, UnitLifecycleState.FAILED})
_NORMAL_TRANSITIONS: dict[UnitLifecycleState, frozenset[UnitLifecycleState]] = {
    UnitLifecycleState.PREPARED: frozenset({UnitLifecycleState.PROPOSED}),
    UnitLifecycleState.PROPOSED: frozenset({UnitLifecycleState.EVALUATED}),
    UnitLifecycleState.EVALUATED: frozenset(
        {UnitLifecycleState.COMMITTED, UnitLifecycleState.RECOVERY_PENDING}
    ),
    UnitLifecycleState.RECOVERY_PENDING: frozenset({UnitLifecycleState.RECOVERY_PROPOSED}),
    UnitLifecycleState.RECOVERY_PROPOSED: frozenset({UnitLifecycleState.RECOVERY_EVALUATED}),
    UnitLifecycleState.RECOVERY_EVALUATED: frozenset({UnitLifecycleState.COMMITTED}),
    UnitLifecycleState.COMMITTED: frozenset(),
    UnitLifecycleState.FAILED: frozenset(),
}


def _require_state(value: object, *, label: str) -> UnitLifecycleState:
    if isinstance(value, UnitLifecycleState):
        return value
    raise KernelValidationError(
        actionable_error(
            code="illegal-transition",
            workflow="kernel",
            subject="source-unit-lifecycle",
            rule="lifecycle-state-type",
            expected=f"a UnitLifecycleState for {label}",
            observed=type(value).__name__,
            next_action="Use a declared UnitLifecycleState value.",
        )
    )


def legal_next_states(current: UnitLifecycleState) -> frozenset[UnitLifecycleState]:
    """Return declared normal edges plus the typed-failure edge when eligible."""

    current = _require_state(current, label="current state")
    if current in TERMINAL_STATES:
        return _NORMAL_TRANSITIONS[current]
    return _NORMAL_TRANSITIONS[current] | frozenset({UnitLifecycleState.FAILED})


def validate_transition(
    current: UnitLifecycleState,
    target: UnitLifecycleState,
    *,
    failure_code: str | None = None,
) -> UnitLifecycleState:
    """Validate one edge, requiring a typed terminal finding for ``failed``."""

    current = _require_state(current, label="current state")
    target = _require_state(target, label="target state")
    failure_is_typed = isinstance(failure_code, str) and bool(failure_code.strip())
    legal = target in _NORMAL_TRANSITIONS[current]
    if target is UnitLifecycleState.FAILED:
        legal = current not in TERMINAL_STATES and failure_is_typed
    if legal:
        return target
    detail = "a typed terminal failure code" if target is UnitLifecycleState.FAILED else "a declared next state"
    raise KernelValidationError(
        actionable_error(
            code="illegal-transition",
            workflow="kernel",
            subject="source-unit-lifecycle",
            rule="declared-monotonic-transition",
            expected=detail,
            observed=f"{current.value} -> {target.value}",
            next_action="Use a declared lifecycle edge or record a typed terminal failure.",
        )
    )
