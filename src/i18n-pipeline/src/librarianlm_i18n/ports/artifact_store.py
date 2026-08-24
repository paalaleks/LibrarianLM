"""Path-independent durable artifact ledger protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

from librarianlm_i18n.kernel.contracts import InvocationReceipt, OperationalFinding, OperationalOutcome, OperationalReceipt, RunReference, UnitManifest
from librarianlm_i18n.kernel.errors import ActionableError
from librarianlm_i18n.kernel.identity import Sha256Digest
from librarianlm_i18n.kernel.contracts import KernelModel

ModelT = TypeVar("ModelT", bound=KernelModel)


class StoreResult(BaseModel):
    """A store boundary never exposes parser, filesystem, or lock exceptions."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    error: ActionableError | None = None


class ObjectWriteResult(StoreResult):
    digest: Sha256Digest | None = None

    @model_validator(mode="after")
    def exclusive_result(self) -> "ObjectWriteResult":
        if (self.error is None) != (self.digest is not None):
            raise ValueError("object write results require exactly one of digest or error")
        return self


class ObjectReadResult(StoreResult):
    canonical_bytes: bytes | None = None
    value: BaseModel | None = None

    @model_validator(mode="after")
    def exclusive_result(self) -> "ObjectReadResult":
        if (self.error is None) != (self.canonical_bytes is not None):
            raise ValueError("object read results require canonical bytes on success and no bytes on error")
        if self.error is not None and self.value is not None:
            raise ValueError("object read errors cannot carry a parsed value")
        return self


class PublicationResult(StoreResult):
    reference: RunReference | None = None
    receipt: OperationalReceipt | None = None
    rebased: bool = False

    @model_validator(mode="after")
    def exclusive_result(self) -> "PublicationResult":
        successful = self.reference is not None and self.receipt is not None
        if (self.error is None) != successful:
            raise ValueError("publication results require both reference and receipt on success, or only error")
        if self.error is not None and (self.reference is not None or self.receipt is not None or self.rebased):
            raise ValueError("failed publication cannot carry success payload")
        return self


class RecoveryResult(StoreResult):
    reference: RunReference | None = None
    manifest: UnitManifest | None = None
    receipts: tuple[OperationalReceipt, ...] = ()

    @model_validator(mode="after")
    def exclusive_result(self) -> "RecoveryResult":
        successful = self.reference is not None and self.manifest is not None and bool(self.receipts)
        if (self.error is None) != successful:
            raise ValueError("recovery results require complete state on success, or only error")
        if self.error is not None and (self.reference is not None or self.manifest is not None or self.receipts):
            raise ValueError("failed recovery cannot carry recovered state")
        return self


class OutcomeResult(StoreResult):
    receipt: OperationalReceipt | None = None

    @model_validator(mode="after")
    def exclusive_result(self) -> "OutcomeResult":
        if (self.error is None) != (self.receipt is not None):
            raise ValueError("outcome results require exactly one of receipt or error")
        return self


class InvocationAppendResult(StoreResult):
    receipt_digest: Sha256Digest | None = None

    @model_validator(mode="after")
    def exclusive_result(self) -> "InvocationAppendResult":
        if (self.error is None) != (self.receipt_digest is not None):
            raise ValueError("invocation append results require exactly one digest or error")
        return self


class InvocationRecoveryResult(StoreResult):
    receipts: tuple[InvocationReceipt, ...] = ()

    @model_validator(mode="after")
    def exclusive_result(self) -> "InvocationRecoveryResult":
        if self.error is not None and self.receipts:
            raise ValueError("failed invocation recovery cannot carry receipt history")
        return self


class ArtifactStore(Protocol):
    def put_object(self, value: KernelModel) -> ObjectWriteResult: ...

    def read_object(self, digest: Sha256Digest, model: type[ModelT] | None = None) -> ObjectReadResult: ...

    def publish_manifest(
        self,
        run_id: str,
        manifest: UnitManifest,
        *,
        expected_predecessor_digest: Sha256Digest | None,
        attempt: int = 1,
        attempt_ceiling: int = 1,
    ) -> PublicationResult: ...

    def record_outcome(
        self,
        run_id: str,
        *,
        stage_id: str,
        outcome: OperationalOutcome,
        attempt: int,
        attempt_ceiling: int,
        error: ActionableError | None = None,
        findings: tuple[OperationalFinding, ...] = (),
        retry_guidance: str,
        produced_artifact_digests: tuple[Sha256Digest, ...] = (),
    ) -> OutcomeResult: ...

    def append_invocation_receipt(self, receipt: InvocationReceipt) -> InvocationAppendResult: ...

    def recover_invocation_receipts(self, run_id: str) -> InvocationRecoveryResult: ...

    def recover(self, run_id: str) -> RecoveryResult: ...
