"""Path-independent durable artifact ledger protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from librarianlm_i18n.kernel.contracts import OperationalReceipt, RunReference, UnitManifest
from librarianlm_i18n.kernel.errors import ActionableError
from librarianlm_i18n.kernel.identity import Sha256Digest

ModelT = TypeVar("ModelT", bound=BaseModel)


class StoreResult(BaseModel):
    """A store boundary never exposes parser, filesystem, or lock exceptions."""

    model_config = {"extra": "forbid", "frozen": True, "strict": True}
    error: ActionableError | None = None


class ObjectWriteResult(StoreResult):
    digest: Sha256Digest | None = None


class ObjectReadResult(StoreResult):
    canonical_bytes: bytes | None = None


class PublicationResult(StoreResult):
    reference: RunReference | None = None
    receipt: OperationalReceipt | None = None
    rebased: bool = False


class RecoveryResult(StoreResult):
    reference: RunReference | None = None
    manifest: UnitManifest | None = None
    receipts: tuple[OperationalReceipt, ...] = ()


class ArtifactStore(Protocol):
    def put_object(self, value: BaseModel) -> ObjectWriteResult: ...

    def read_object(self, digest: Sha256Digest) -> ObjectReadResult: ...

    def publish_manifest(
        self,
        run_id: str,
        manifest: UnitManifest,
        *,
        expected_predecessor_digest: Sha256Digest | None,
        attempt: int = 1,
        attempt_ceiling: int = 1,
    ) -> PublicationResult: ...

    def recover(self, run_id: str) -> RecoveryResult: ...
