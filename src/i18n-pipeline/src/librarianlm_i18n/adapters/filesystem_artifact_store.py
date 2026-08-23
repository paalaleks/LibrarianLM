"""Local, append-only NTFS-style artifact store.

The adapter deliberately gives orphan files no semantic meaning.  A run becomes
visible only when its small reference file atomically names *both* a manifest
and the receipt that proves its publication.
"""

from __future__ import annotations

import os
import re
import socket
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, ValidationError

from librarianlm_i18n.kernel.canonical import HostileJsonError, canonical_bytes, load_strict_json
from librarianlm_i18n.kernel.contracts import (
    LockOwner,
    ManifestLink,
    OperationalOutcome,
    OperationalReceipt,
    RunReference,
    UnitManifest,
    UnitRecord,
)
from librarianlm_i18n.kernel.errors import ActionableError, Retryability, actionable_error
from librarianlm_i18n.kernel.identity import is_sha256_digest, sha256_digest
from librarianlm_i18n.kernel.lifecycle import UnitLifecycleState, legal_next_states
from librarianlm_i18n.ports.artifact_store import (
    ObjectReadResult,
    ObjectWriteResult,
    PublicationResult,
    RecoveryResult,
)

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class _StoreFailure(Exception):
    def __init__(self, error: ActionableError) -> None:
        self.error = error
        super().__init__(error.code)


class FilesystemArtifactStore:
    """Filesystem-backed ledger restricted to a single local host/root."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.objects = self.root / "objects" / "sha256"
        self.runs = self.root / "runs"
        self.locks = self.root / "locks"
        for directory in (self.objects, self.runs, self.locks):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _error(code: str, subject: str, rule: str, expected: str, observed: str, *, retryable: bool = False) -> _StoreFailure:
        return _StoreFailure(actionable_error(
            code=code, workflow="artifact-store", subject=subject, rule=rule,
            expected=expected, observed=observed,
            retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Inspect the durable artifact ledger and retry only after the stated condition is corrected.",
        ))

    def _run_dir(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            raise self._error("invalid-run-id", "run", "safe-run-id", "an ASCII run ID without path traversal", repr(run_id))
        return self.runs / run_id

    def _object_path(self, digest: str) -> Path:
        if not isinstance(digest, str) or not is_sha256_digest(digest):
            raise self._error("invalid-digest", "object", "sha256-address", "a lowercase SHA-256 digest", repr(digest))
        return self.objects / f"{digest}.json"

    @staticmethod
    def _atomic_create_or_verify(path: Path, content: bytes, *, subject: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_BINARY)
        except FileExistsError:
            try:
                existing = path.read_bytes()
            except OSError as error:
                raise FilesystemArtifactStore._error("artifact-read-failed", subject, "read-existing", "a readable immutable file", str(error)) from error
            if existing != content:
                raise FilesystemArtifactStore._error("immutable-collision", subject, "create-or-verify", "identical canonical bytes at an existing address", "different bytes already exist")
            return
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
        except OSError as error:
            raise FilesystemArtifactStore._error("artifact-write-failed", subject, "durable-write", "a flushed immutable file", str(error), retryable=True) from error

    @staticmethod
    def _atomic_replace(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temp_path, path)
            # NTFS does not expose portable directory handles. The ref file was
            # flushed before replace; a best-effort directory flush is used where supported.
            try:
                directory_fd = os.open(str(path.parent), os.O_RDONLY)
            except OSError:
                return
            try:
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                os.close(directory_fd)
        except OSError as error:
            raise FilesystemArtifactStore._error("reference-write-failed", "run-reference", "same-directory-atomic-replace", "an atomically replaced, durable reference", str(error), retryable=True) from error
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def put_object(self, value: BaseModel) -> ObjectWriteResult:
        try:
            content = canonical_bytes(value)
            digest = sha256_digest(content)
            self._atomic_create_or_verify(self._object_path(digest), content, subject="content-object")
            return ObjectWriteResult(digest=digest)
        except _StoreFailure as failure:
            return ObjectWriteResult(error=failure.error)
        except (TypeError, ValueError, OSError) as error:
            return ObjectWriteResult(error=self._unexpected("content-object", error))

    def read_object(self, digest: str) -> ObjectReadResult:
        try:
            path = self._object_path(digest)
            if not path.is_file():
                raise self._error("object-missing", "content-object", "immutable-object-present", "an object at its digest address", digest)
            content = path.read_bytes()
            if sha256_digest(content) != digest:
                raise self._error("object-integrity-failure", "content-object", "digest-address-match", digest, sha256_digest(content))
            # Parsing proves a stored object is canonical JSON, not merely hash-matching bytes.
            if canonical_bytes(load_strict_json(content)) != content:
                raise self._error("object-integrity-failure", "content-object", "canonical-json", "canonical JSON bytes", "non-canonical bytes")
            return ObjectReadResult(canonical_bytes=content)
        except _StoreFailure as failure:
            return ObjectReadResult(error=failure.error)
        except (OSError, UnicodeError, HostileJsonError, TypeError, ValueError) as error:
            return ObjectReadResult(error=self._unexpected("content-object", error))

    @staticmethod
    def _current_process_identity(pid: int) -> str | None:
        """Return an identity that changes on PID reuse, or None when unprovable."""
        if pid <= 0:
            return None
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                if not process:
                    return None
                try:
                    created = wintypes.FILETIME()
                    exited = wintypes.FILETIME()
                    kernel = wintypes.FILETIME()
                    user = wintypes.FILETIME()
                    if not ctypes.windll.kernel32.GetProcessTimes(process, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
                        return None
                    return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
                finally:
                    ctypes.windll.kernel32.CloseHandle(process)
            except (AttributeError, OSError):
                return None
        stat = Path(f"/proc/{pid}/stat")
        try:
            # The start tick is field 22; a comm field can contain spaces in parens.
            fields = stat.read_text(encoding="utf-8").rsplit(") ", 1)[1].split()
            return fields[19]
        except (OSError, IndexError):
            return None

    @staticmethod
    def _process_is_positively_dead(pid: int) -> bool:
        """Only a definite OS 'no such process' result permits lock reclamation."""
        if pid <= 0:
            return False
        if os.name != "nt":
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            return False
        try:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            ctypes.set_last_error(0)
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return False
            return ctypes.get_last_error() == 87  # ERROR_INVALID_PARAMETER: PID does not exist.
        except (AttributeError, OSError):
            return False

    def _owner(self) -> LockOwner:
        identity = self._current_process_identity(os.getpid())
        if identity is None:
            raise self._error("lock-owner-unverifiable", "lock", "process-start-identity", "a provable local process identity", "unavailable")
        return LockOwner(host=socket.gethostname(), pid=os.getpid(), process_started_identity=identity, acquired_at=datetime.now(UTC))

    def _lock_path(self, run_id: str) -> Path:
        self._run_dir(run_id)  # validates before composing the separate lock path
        return self.locks / f"{run_id}.lock"

    def _read_lock_owner(self, path: Path) -> LockOwner:
        try:
            raw = path.read_bytes()
            load_strict_json(raw)  # reject duplicates/non-canonical JSON before Pydantic's JSON mode.
            owner = LockOwner.model_validate_json(raw)
            if canonical_bytes(owner) != raw:
                raise self._error("lock-owner-unverifiable", "lock", "canonical-owner-record", "canonical LockOwner bytes", "non-canonical owner bytes")
            return owner
        except (OSError, HostileJsonError, ValidationError, TypeError, ValueError) as error:
            raise self._error("lock-owner-unverifiable", "lock", "valid-owner-record", "a valid immutable local owner record", str(error)) from error

    @contextmanager
    def _run_lock(self, run_id: str) -> Iterator[LockOwner]:
        path = self._lock_path(run_id)
        owner = self._owner()
        content = canonical_bytes(owner)
        acquired = False
        # All contenders take this short-lived gate before they inspect, reclaim,
        # or create the durable owner file.  The gate makes stale-owner reclamation
        # safe: no second cooperative contender can acquire a replacement lock in
        # the unlink/create window.
        gate = self.locks / f".{run_id}.acquire"
        try:
            gate_descriptor = os.open(str(gate), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_BINARY)
        except FileExistsError as error:
            raise self._error("lock-contended", "lock", "exclusive-lock-acquisition", "no simultaneous lock acquirer", "another acquirer is resolving this lock", retryable=True) from error
        try:
            try:
                with os.fdopen(gate_descriptor, "wb") as gate_file:
                    gate_file.write(b"acquiring\n")
                    gate_file.flush()
                descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_BINARY)
            except FileExistsError:
                incumbent = self._read_lock_owner(path)
                if incumbent.host != socket.gethostname():
                    raise self._error("lock-ambiguous", "lock", "local-host-owner", socket.gethostname(), incumbent.host)
                actual = self._current_process_identity(incumbent.pid)
                if actual is None:
                    if self._process_is_positively_dead(incumbent.pid):
                        try:
                            path.unlink()
                            descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_BINARY)
                        except FileNotFoundError as error:
                            raise self._error("lock-contended", "lock", "exclusive-lock-acquisition", "the stale owner to remain present until reclaimed", "lock changed while reclaiming", retryable=True) from error
                        except FileExistsError as error:
                            raise self._error("lock-contended", "lock", "exclusive-lock-acquisition", "no replacement owner", "a replacement owner acquired the lock", retryable=True) from error
                    else:
                        # A missing identity alone cannot distinguish dead from denied.
                        raise self._error("lock-ambiguous", "lock", "positive-death-proof", "a provably dead exact process", "process identity unavailable", retryable=True)
                elif actual == incumbent.process_started_identity:
                    raise self._error("lock-contended", "lock", "exclusive-run-writer", "no live owner", f"live pid {incumbent.pid}", retryable=True)
                else:
                    # PID exists but has a different creation identity: exact recorded process is dead.
                    try:
                        path.unlink()
                        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_BINARY)
                    except FileNotFoundError as error:
                        raise self._error("lock-contended", "lock", "exclusive-lock-acquisition", "the stale owner to remain present until reclaimed", "lock changed while reclaiming", retryable=True) from error
                    except FileExistsError as error:
                        raise self._error("lock-contended", "lock", "exclusive-lock-acquisition", "no replacement owner", "a replacement owner acquired the lock", retryable=True) from error
            finally:
                try:
                    gate.unlink()
                except FileNotFoundError:
                    pass
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            acquired = True
            yield owner
        finally:
            if acquired:
                try:
                    if path.exists() and self._read_lock_owner(path) == owner:
                        path.unlink()
                except (OSError, _StoreFailure):
                    # A stale lock is safer than removing a lock we cannot prove we own.
                    pass

    def _read_model(self, digest: str, model: type[BaseModel]) -> BaseModel:
        result = self.read_object(digest)
        if result.error is not None or result.canonical_bytes is None:
            raise _StoreFailure(result.error or self._unexpected("content-object", RuntimeError("missing object result")))
        try:
            load_strict_json(result.canonical_bytes)
            return model.model_validate_json(result.canonical_bytes)
        except (HostileJsonError, ValidationError, TypeError, ValueError) as error:
            raise self._error("object-schema-mismatch", "content-object", "expected-contract-schema", model.__name__, str(error)) from error

    def _ref_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "refs" / "manifest.json"

    def _read_reference(self, run_id: str) -> RunReference | None:
        path = self._ref_path(run_id)
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
            if canonical_bytes(load_strict_json(raw)) != raw:
                raise self._error("reference-invalid", "run-reference", "canonical-reference", "canonical run reference bytes", "non-canonical bytes")
            reference = RunReference.model_validate_json(raw)
            if reference.run_id != run_id:
                raise self._error("reference-invalid", "run-reference", "reference-run-binding", run_id, reference.run_id)
            return reference
        except _StoreFailure:
            raise
        except (OSError, HostileJsonError, ValidationError, TypeError, ValueError) as error:
            raise self._error("reference-invalid", "run-reference", "valid-run-reference", "a valid run reference", str(error)) from error

    @staticmethod
    def _manifest_inventory_key(manifest: UnitManifest) -> tuple[object, ...]:
        data = manifest.model_dump()
        data.pop("units")
        data.pop("previous_manifest_digest")
        return tuple(sorted(data.items(), key=lambda item: item[0]))

    @staticmethod
    def _unit_advance_is_legal(base: UnitRecord, candidate: UnitRecord) -> bool:
        base_data, candidate_data = base.model_dump(), candidate.model_dump()
        base_state = base_data.pop("lifecycle_state")
        candidate_state = candidate_data.pop("lifecycle_state")
        if base_data != candidate_data:
            return False
        current = UnitLifecycleState(base_state)
        target = UnitLifecycleState(candidate_state)
        visited: set[UnitLifecycleState] = set()
        pending = [current]
        while pending:
            state = pending.pop()
            if state == target:
                return True
            if state in visited:
                continue
            visited.add(state)
            pending.extend(legal_next_states(state))
        return False

    def _rebase(self, base: UnitManifest, current: UnitManifest, proposed: UnitManifest, current_digest: str) -> UnitManifest:
        if self._manifest_inventory_key(base) != self._manifest_inventory_key(current) or self._manifest_inventory_key(base) != self._manifest_inventory_key(proposed):
            raise self._error("manifest-conflict", "manifest", "immutable-manifest-level-data", "identical base inventory, provenance, and status", "manifest-level divergence")
        base_units = {unit.source_unit_id: unit for unit in base.units}
        current_units = {unit.source_unit_id: unit for unit in current.units}
        proposed_units = {unit.source_unit_id: unit for unit in proposed.units}
        if set(base_units) != set(current_units) or set(base_units) != set(proposed_units):
            raise self._error("manifest-conflict", "manifest", "identical-base-inventory", "the same unit inventory", "unit inventory changed")
        merged: list[UnitRecord] = []
        for unit_id, base_unit in base_units.items():
            left, right = current_units[unit_id], proposed_units[unit_id]
            left_changed, right_changed = left != base_unit, right != base_unit
            if left_changed and right_changed:
                raise self._error("manifest-conflict", f"unit:{unit_id}", "disjoint-unit-advance", "only one successor changes a unit", "overlapping unit advance")
            candidate = left if left_changed else right if right_changed else base_unit
            if candidate != base_unit and not self._unit_advance_is_legal(base_unit, candidate):
                raise self._error("manifest-conflict", f"unit:{unit_id}", "legal-lifecycle-advance", "a whole UnitRecord with only legal lifecycle advancement", "illegal unit mutation")
            merged.append(candidate)
        merged.sort(key=lambda unit: unit.ordinal)
        return current.model_copy(update={"units": tuple(merged), "previous_manifest_digest": current_digest})

    def _write_receipt(self, run_id: str, receipt: OperationalReceipt) -> str:
        content = canonical_bytes(receipt)
        digest = sha256_digest(content)
        path = self._run_dir(run_id) / "receipts" / f"{digest}.json"
        self._atomic_create_or_verify(path, content, subject="operational-receipt")
        return digest

    def _validate_next_attempt(self, prior_receipt: OperationalReceipt | None, attempt: int, attempt_ceiling: int) -> None:
        if isinstance(attempt, bool) or not isinstance(attempt, int) or isinstance(attempt_ceiling, bool) or not isinstance(attempt_ceiling, int):
            raise self._error("retry-history-invalid", "receipt", "integer-attempt-history", "integer attempt and attempt ceiling", f"attempt={attempt!r}, ceiling={attempt_ceiling!r}")
        if attempt < 1 or attempt_ceiling < 1 or attempt > attempt_ceiling:
            raise self._error("retry-history-invalid", "receipt", "bounded-attempt", "1 <= attempt <= attempt ceiling", f"attempt={attempt}, ceiling={attempt_ceiling}")
        if prior_receipt is None:
            if attempt != 1:
                raise self._error("retry-history-invalid", "receipt", "genesis-attempt", "attempt 1 for the first receipt", str(attempt))
            return
        if attempt != prior_receipt.attempt + 1:
            raise self._error("retry-history-invalid", "receipt", "strict-next-attempt", str(prior_receipt.attempt + 1), str(attempt))
        if attempt_ceiling != prior_receipt.attempt_ceiling:
            raise self._error("retry-history-invalid", "receipt", "immutable-attempt-ceiling", str(prior_receipt.attempt_ceiling), str(attempt_ceiling))

    def publish_manifest(self, run_id: str, manifest: UnitManifest, *, expected_predecessor_digest: str | None, attempt: int = 1, attempt_ceiling: int = 1) -> PublicationResult:
        try:
            self._run_dir(run_id)
            if expected_predecessor_digest is not None and not is_sha256_digest(expected_predecessor_digest):
                raise self._error("invalid-digest", "manifest", "expected-predecessor-digest", "a SHA-256 digest or null", repr(expected_predecessor_digest))
            if manifest.previous_manifest_digest != expected_predecessor_digest:
                raise self._error("manifest-conflict", "manifest", "declared-predecessor", repr(expected_predecessor_digest), repr(manifest.previous_manifest_digest))
            with self._run_lock(run_id) as owner:
                prior_ref = self._read_reference(run_id)
                prior_receipt: OperationalReceipt | None = None
                if prior_ref is not None:
                    # A reference is a commit point only if its entire history is
                    # recoverable.  Never extend a run whose current state cannot
                    # be proven from the linked immutable receipts and manifests.
                    recovered = self.recover(run_id)
                    if recovered.error is not None or recovered.reference is None or not recovered.receipts:
                        raise _StoreFailure(recovered.error or self._error("recovery-invalid", "run", "recoverable-history", "a complete current history", "missing recovered history").error)
                    prior_ref = recovered.reference
                    prior_receipt = recovered.receipts[0]
                self._validate_next_attempt(prior_receipt, attempt, attempt_ceiling)
                current_digest = prior_ref.manifest_digest if prior_ref else None
                proposed_result = self.put_object(manifest)
                if proposed_result.error is not None or proposed_result.digest is None:
                    raise _StoreFailure(proposed_result.error or self._unexpected("manifest", RuntimeError("object storage failed")))
                proposed_digest = proposed_result.digest
                successor, rebased = manifest, False
                if current_digest != expected_predecessor_digest:
                    if expected_predecessor_digest is None or current_digest is None:
                        raise self._error("manifest-conflict", "manifest", "expected-predecessor", repr(expected_predecessor_digest), repr(current_digest), retryable=True)
                    base = self._read_model(expected_predecessor_digest, UnitManifest)
                    current = self._read_model(current_digest, UnitManifest)
                    successor = self._rebase(base, current, manifest, current_digest)
                    successor_result = self.put_object(successor)
                    if successor_result.error is not None or successor_result.digest is None:
                        raise _StoreFailure(successor_result.error or self._unexpected("manifest", RuntimeError("rebase storage failed")))
                    proposed_digest, rebased = successor_result.digest, True
                predecessor_receipt = prior_ref.completion_receipt_digest if prior_ref else None
                now = datetime.now(UTC)
                receipt = OperationalReceipt(
                    run_id=run_id, attempt=attempt, attempt_ceiling=attempt_ceiling,
                    started_at=now, completed_at=now, outcome=OperationalOutcome.COMPLETED,
                    retry_guidance="No retry is required after a completed publication.", lock_owner=owner,
                    manifest_link=ManifestLink(predecessor_manifest_digest=current_digest, successor_manifest_digest=proposed_digest),
                    predecessor_receipt_digest=predecessor_receipt,
                )
                receipt_digest = self._write_receipt(run_id, receipt)
                reference = RunReference(run_id=run_id, manifest_digest=proposed_digest, completion_receipt_digest=receipt_digest)
                self._atomic_replace(self._ref_path(run_id), canonical_bytes(reference))
                return PublicationResult(reference=reference, receipt=receipt, rebased=rebased)
        except _StoreFailure as failure:
            return PublicationResult(error=failure.error)
        except (OSError, TypeError, ValueError) as error:
            return PublicationResult(error=self._unexpected("manifest", error))

    def _read_receipt(self, run_id: str, digest: str) -> OperationalReceipt:
        path = self._run_dir(run_id) / "receipts" / f"{digest}.json"
        try:
            content = path.read_bytes()
            if sha256_digest(content) != digest or canonical_bytes(load_strict_json(content)) != content:
                raise self._error("recovery-invalid", "receipt", "receipt-integrity", digest, "digest or canonical bytes mismatch")
            receipt = OperationalReceipt.model_validate_json(content)
            if receipt.run_id != run_id:
                raise self._error("recovery-invalid", "receipt", "receipt-run-binding", run_id, receipt.run_id)
            return receipt
        except _StoreFailure:
            raise
        except (OSError, HostileJsonError, ValidationError, TypeError, ValueError) as error:
            raise self._error("recovery-invalid", "receipt", "valid-immutable-receipt", "a valid receipt", str(error)) from error

    def _validate_receipt_attempt_history(self, receipts: list[OperationalReceipt]) -> None:
        prior: OperationalReceipt | None = None
        for receipt in reversed(receipts):
            if prior is None:
                if receipt.attempt != 1:
                    raise self._error("recovery-invalid", "receipt", "genesis-attempt", "attempt 1 for the first receipt", str(receipt.attempt))
            else:
                if receipt.attempt != prior.attempt + 1:
                    raise self._error("recovery-invalid", "receipt", "strict-next-attempt", str(prior.attempt + 1), str(receipt.attempt))
                if receipt.attempt_ceiling != prior.attempt_ceiling:
                    raise self._error("recovery-invalid", "receipt", "immutable-attempt-ceiling", str(prior.attempt_ceiling), str(receipt.attempt_ceiling))
            prior = receipt

    def recover(self, run_id: str) -> RecoveryResult:
        try:
            reference = self._read_reference(run_id)
            if reference is None:
                raise self._error("recovery-not-found", "run", "committed-run-reference", "an atomically published run reference", "no reference exists")
            manifest = self._read_model(reference.manifest_digest, UnitManifest)
            receipts: list[OperationalReceipt] = []
            seen_receipts: set[str] = set()
            receipt_digest: str | None = reference.completion_receipt_digest
            cursor_digest: str | None = reference.manifest_digest
            while receipt_digest is not None:
                if receipt_digest in seen_receipts:
                    raise self._error("recovery-invalid", "receipt", "acyclic-receipt-chain", "an acyclic receipt chain", "receipt cycle")
                seen_receipts.add(receipt_digest)
                receipt = self._read_receipt(run_id, receipt_digest)
                if cursor_digest is None or receipt.outcome is not OperationalOutcome.COMPLETED or receipt.manifest_link.successor_manifest_digest != cursor_digest:
                    raise self._error("recovery-invalid", "receipt", "completion-link", str(cursor_digest), "receipt does not complete expected manifest")
                cursor = self._read_model(cursor_digest, UnitManifest)
                if cursor.previous_manifest_digest != receipt.manifest_link.predecessor_manifest_digest:
                    raise self._error("recovery-invalid", "manifest", "manifest-predecessor-link", repr(cursor.previous_manifest_digest), repr(receipt.manifest_link.predecessor_manifest_digest))
                receipts.append(receipt)
                if cursor.previous_manifest_digest is None:
                    if receipt.predecessor_receipt_digest is not None:
                        raise self._error("recovery-invalid", "receipt", "genesis-receipt-predecessor", "no predecessor receipt for a genesis manifest", receipt.predecessor_receipt_digest)
                    break
                if receipt.predecessor_receipt_digest is None:
                    raise self._error("recovery-invalid", "receipt", "complete-receipt-chain", "a predecessor receipt for every predecessor manifest", "receipt chain ended early")
                cursor_digest = cursor.previous_manifest_digest
                receipt_digest = receipt.predecessor_receipt_digest
            self._validate_receipt_attempt_history(receipts)
            return RecoveryResult(reference=reference, manifest=manifest, receipts=tuple(receipts))
        except _StoreFailure as failure:
            return RecoveryResult(error=failure.error)
        except (OSError, TypeError, ValueError) as error:
            return RecoveryResult(error=self._unexpected("recovery", error))

    @staticmethod
    def _unexpected(subject: str, error: Exception) -> ActionableError:
        return actionable_error(
            code="artifact-store-failure", workflow="artifact-store", subject=subject,
            rule="handled-store-boundary", expected="a successful store operation", observed=f"{type(error).__name__}: {error}",
            retryability=Retryability.RETRYABLE,
            next_action="Inspect the artifact root and use the returned error before retrying.",
        )
