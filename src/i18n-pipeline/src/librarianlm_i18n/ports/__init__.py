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
from .html_document import HtmlCloneResult, HtmlDocument, HtmlMutationResult, HtmlObservation, HtmlObservationResult, HtmlSelectionResult, HtmlSerializationResult, ProtectedBlockResult, SelectedSourceSlot
from .package_signer import PackageSigner, SignatureResult, VerificationResult
from .residual_language import ResidualLanguageDetector, ResidualLanguageResult

__all__ = [
    "ArtifactStore",
    "ObjectReadResult",
    "ObjectWriteResult",
    "OutcomeResult",
    "PublicationResult",
    "RecoveryResult",
    "StoreResult",
    "HtmlDocument",
    "HtmlCloneResult",
    "HtmlMutationResult",
    "HtmlObservation",
    "HtmlObservationResult",
    "HtmlSelectionResult",
    "HtmlSerializationResult",
    "ProtectedBlockResult",
    "SelectedSourceSlot",
    "PackageSigner",
    "SignatureResult",
    "VerificationResult",
    "ResidualLanguageDetector",
    "ResidualLanguageResult",
]
