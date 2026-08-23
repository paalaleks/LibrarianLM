"""Storage-facing contracts; implementations belong in adapters."""

from .artifact_store import (
    ArtifactStore,
    ObjectReadResult,
    ObjectWriteResult,
    OutcomeResult,
    PublicationResult,
    RecoveryResult,
    StoreResult,
)

__all__ = [
    "ArtifactStore",
    "ObjectReadResult",
    "ObjectWriteResult",
    "OutcomeResult",
    "PublicationResult",
    "RecoveryResult",
    "StoreResult",
]
