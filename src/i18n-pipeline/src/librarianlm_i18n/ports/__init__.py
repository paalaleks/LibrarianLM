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
from .html_document import HtmlDocument, HtmlSelectionResult, SelectedSourceSlot
from .package_signer import PackageSigner, SignatureResult, VerificationResult

__all__ = [
    "ArtifactStore",
    "ObjectReadResult",
    "ObjectWriteResult",
    "OutcomeResult",
    "PublicationResult",
    "RecoveryResult",
    "StoreResult",
    "HtmlDocument",
    "HtmlSelectionResult",
    "SelectedSourceSlot",
    "PackageSigner",
    "SignatureResult",
    "VerificationResult",
]
