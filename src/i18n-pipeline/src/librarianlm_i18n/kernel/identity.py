"""Typed, deterministic identities and SHA-256 digest helpers."""

from __future__ import annotations

import hashlib
import re
from typing import Annotated

from pydantic import Strict, StringConstraints

from .canonical import canonical_bytes

Sha256Digest = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^[0-9a-f]{64}$"),
]
SourceUnitId = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^source-unit:[0-9a-f]{64}$"),
]
ComponentId = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^component:[a-z0-9][a-z0-9._-]*$"),
]
ProjectionGroupId = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^projection-group:[0-9a-f]{64}$"),
]
TokenId = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^[A-Z2-7]{26}$"),
]
StructuralFingerprint = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^structural-fingerprint:[0-9a-f]{64}$"),
]
DomLocator = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^dom:[^\s]+$"),
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

__all__ = [
    "ComponentId",
    "DomLocator",
    "ProjectionGroupId",
    "Sha256Digest",
    "SourceUnitId",
    "StructuralFingerprint",
    "TokenId",
    "derive_typed_id",
    "is_sha256_digest",
    "render_protected_token",
    "sha256_digest",
    "source_text_digest",
]


def sha256_digest(content: bytes) -> str:
    """Return the lowercase SHA-256 digest for already canonical bytes."""

    return hashlib.sha256(content).hexdigest()


def source_text_digest(source_text: str) -> str:
    """Hash exact source text; text is not normalized before identity checks."""

    return sha256_digest(source_text.encode("utf-8"))


def derive_typed_id(prefix: str, identity_material: object) -> str:
    """Derive a cross-workflow identity without paths, random IDs, or database keys."""

    if not re.fullmatch(r"[a-z][a-z0-9-]*", prefix):
        raise ValueError("identity prefixes must be lowercase kebab-case")
    return f"{prefix}:{sha256_digest(canonical_bytes(identity_material))}"


def is_sha256_digest(value: str) -> bool:
    return bool(_SHA256_RE.fullmatch(value))


def render_protected_token(token_id: str) -> str:
    """Render the exact ASCII placeholder used for a validated inline binding ID."""

    if not isinstance(token_id, str) or not re.fullmatch(r"[A-Z2-7]{26}", token_id):
        raise ValueError("token ID must be 26 uppercase base32 characters")
    return f"[[[LLM:BIND:{token_id}]]]"
