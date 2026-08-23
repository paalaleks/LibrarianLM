"""Canonical JSON and hostile-input checks for deterministic content."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class HostileJsonError(ValueError):
    """Raised before model validation for non-canonical or ambiguous JSON."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HostileJsonError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise HostileJsonError(f"non-finite JSON number: {value}")


def reject_floats(value: object) -> None:
    """Reject every float recursively, including values produced from JSON numbers."""

    if isinstance(value, float):
        raise HostileJsonError("floating-point values are not allowed")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise HostileJsonError("JSON object keys must be strings")
            reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_floats(item)


def load_strict_json(raw: str | bytes | bytearray) -> object:
    """Parse JSON after rejecting duplicate members, NaN, and all floats."""

    if isinstance(raw, bytearray):
        raw = bytes(raw)
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HostileJsonError("JSON must be UTF-8") from error
    if not isinstance(raw, str):
        raise HostileJsonError("JSON input must be text or UTF-8 bytes")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as error:
        raise HostileJsonError("invalid JSON") from error
    reject_floats(value)
    return value


def normalized_json_value(value: object) -> object:
    """Return JSON-domain data, rejecting mutable/non-deterministic values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("canonical JSON forbids floats")
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            normalized[key] = normalized_json_value(item)
        return normalized
    if isinstance(value, (tuple, list)):
        return [normalized_json_value(item) for item in value]
    raise TypeError(f"canonical JSON does not accept {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Serialize the deliberately small JSON domain as UTF-8/LF canonical bytes."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    normalized = normalized_json_value(value)
    return (
        json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
