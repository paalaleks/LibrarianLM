"""Detached package-signing boundary.  No key material crosses this API."""

from __future__ import annotations

from typing import Protocol

from librarianlm_i18n.kernel.contracts import SignatureRecord
from librarianlm_i18n.kernel.errors import ActionableError
from librarianlm_i18n.kernel.identity import Sha256Digest


class SignatureResult:
    def __init__(self, *, signature: SignatureRecord | None = None, error: ActionableError | None = None) -> None:
        if (signature is None) == (error is None):
            raise ValueError("signature results require exactly one of signature or error")
        self.signature = signature
        self.error = error


class VerificationResult:
    def __init__(self, *, verified: bool = False, error: ActionableError | None = None) -> None:
        if verified and error is not None:
            raise ValueError("verified results cannot carry an error")
        self.verified = verified
        self.error = error


class PackageSigner(Protocol):
    def sign(self, package_digest: Sha256Digest, key_id: str) -> SignatureResult: ...
    def verify(self, signature: SignatureRecord, package_digest: Sha256Digest, key_id: str) -> VerificationResult: ...
