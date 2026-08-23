"""Storage-facing contracts; implementations belong in adapters."""

from .artifact_store import (
    ArtifactStore,
    ObjectReadResult,
    ObjectWriteResult,
    PublicationResult,
    RecoveryResult,
    StoreResult,
)

__all__ = [
    "ArtifactStore",
    "ObjectReadResult",
    "ObjectWriteResult",
    "PublicationResult",
    "RecoveryResult",
    "StoreResult",
]
