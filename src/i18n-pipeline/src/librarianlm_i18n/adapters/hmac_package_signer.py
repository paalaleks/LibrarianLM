"""Exception-safe detached HMAC signer with an in-memory fixture key ring."""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping

from librarianlm_i18n.kernel.contracts import SignatureRecord
from librarianlm_i18n.kernel.errors import Retryability, actionable_error
from librarianlm_i18n.kernel.identity import is_sha256_digest
from librarianlm_i18n.ports.package_signer import SignatureResult, VerificationResult


class HmacPackageSigner:
    """Keys remain private implementation state and are never returned."""

    def __init__(self, keys: Mapping[str, bytes], *, active_key_ids: frozenset[str], revoked_key_ids: frozenset[str] = frozenset()) -> None:
        self._keys = dict(keys)
        self._active = frozenset(active_key_ids)
        self._revoked = frozenset(revoked_key_ids)

    def sign(self, package_digest: str, key_id: str) -> SignatureResult:
        failure = self._key_failure(package_digest, key_id, signing=True)
        if failure is not None:
            return SignatureResult(error=failure)
        try:
            value = hmac.new(self._keys[key_id], package_digest.encode("ascii"), hashlib.sha256).digest()
            signature = base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
            return SignatureResult(signature=SignatureRecord(algorithm="hmac-sha256", key_id=key_id, package_digest=package_digest, signature=signature))
        except Exception as error:
            return SignatureResult(error=self._error("signer-unavailable", key_id, f"{type(error).__name__}: {error}", retryable=True))

    def verify(self, signature: SignatureRecord, package_digest: str, key_id: str) -> VerificationResult:
        if not isinstance(signature, SignatureRecord):
            return VerificationResult(error=self._error("invalid-signature", key_id, type(signature).__name__))
        failure = self._key_failure(package_digest, key_id, signing=False)
        if failure is not None:
            return VerificationResult(error=failure)
        if signature.algorithm != "hmac-sha256" or signature.key_id != key_id or signature.package_digest != package_digest:
            return VerificationResult(error=self._error("signature-key-mismatch", key_id, "signature metadata does not bind requested key and package"))
        try:
            expected = self.sign(package_digest, key_id)
            if expected.error is not None:
                return VerificationResult(error=expected.error)
            if not hmac.compare_digest(expected.signature.signature, signature.signature):
                return VerificationResult(error=self._error("signature-invalid", key_id, "HMAC mismatch"))
            return VerificationResult(verified=True)
        except Exception as error:
            return VerificationResult(error=self._error("signer-unavailable", key_id, f"{type(error).__name__}: {error}", retryable=True))

    def _key_failure(self, package_digest: str, key_id: str, *, signing: bool) -> object | None:
        if not isinstance(package_digest, str) or not is_sha256_digest(package_digest):
            return self._error("invalid-package-digest", key_id if isinstance(key_id, str) else "unknown", repr(package_digest))
        if not isinstance(key_id, str) or not key_id:
            return self._error("invalid-signing-key", "unknown", repr(key_id))
        if key_id in self._revoked:
            return self._error("signing-key-revoked", key_id, "key is revoked")
        if key_id not in self._keys:
            return self._error("signing-key-unknown", key_id, "key is unavailable")
        if signing and key_id not in self._active:
            return self._error("signing-key-untrusted", key_id, "key is not active")
        return None

    @staticmethod
    def _error(code: str, key_id: str, observed: str, *, retryable: bool = False):
        return actionable_error(code=code, workflow="prepare-confirmation", subject="signing-key", rule="trusted-detached-hmac-key", expected="an active non-revoked configured key", observed=observed, retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE, next_action="Use a configured active key or repair signer availability before retrying.")
