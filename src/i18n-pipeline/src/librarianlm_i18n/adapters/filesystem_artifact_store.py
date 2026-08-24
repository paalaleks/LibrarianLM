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
    KernelModel,
    InvocationReceipt,
    ManifestLink,
    OperationalOutcome,
    OperationalReceipt,
    ProvenanceKind,
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
    OutcomeResult,
    InvocationAppendResult,
    InvocationRecoveryResult,
    RecoveryResult,
)

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_RESERVED_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))})


class _StoreFailure(Exception):
    def __init__(self, error: ActionableError) -> None:
        self.error = error
        super().__init__(error.code)


class FilesystemArtifactStore:
    """Filesystem-backed ledger restricted to a single local host/root."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).absolute()
        self.objects = self.root / "objects" / "sha256"
        self.runs = self.root / "runs"
        self.locks = self.root / "locks"
        self._root_failure: _StoreFailure | None = None
        try:
            self._validate_root()
            for directory in (self.objects, self.runs, self.locks):
                self._safe_mkdir(directory)
        except _StoreFailure as failure:
            self._root_failure = failure

    @staticmethod
    def _error(code: str, subject: str, rule: str, expected: str, observed: str, *, retryable: bool = False) -> _StoreFailure:
        return _StoreFailure(actionable_error(
            code=code, workflow="artifact-store", subject=subject, rule=rule,
            expected=expected, observed=observed,
            retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Inspect the durable artifact ledger and retry only after the stated condition is corrected.",
        ))

    def _run_dir(self, run_id: str) -> Path:
        if (not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id)
                or run_id.rstrip(". ") != run_id
                or run_id.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES):
            raise self._error("invalid-run-id", "run", "safe-run-id", "an ASCII run ID without path traversal", repr(run_id))
        result = self.runs / run_id
        self._assert_safe_path(result, "run")
        return result

    def _object_path(self, digest: str) -> Path:
        if not isinstance(digest, str) or not is_sha256_digest(digest):
            raise self._error("invalid-digest", "object", "sha256-address", "a lowercase SHA-256 digest", repr(digest))
        result = self.objects / f"{digest}.json"
        self._assert_safe_path(result, "object")
        return result

    def _validate_root(self) -> None:
        root_text = str(self.root)
        if root_text.startswith("\\\\") or root_text.startswith("//"):
            raise self._error("unsafe-artifact-root", "artifact-root", "local-fixed-ntfs-root", "a local fixed NTFS directory", root_text)
        if self.root.exists() and self._is_redirect(self.root):
            raise self._error("unsafe-artifact-root", "artifact-root", "non-reparse-root", "a real directory", root_text)
        if os.name == "nt":
            try:
                import ctypes
                drive = self.root.anchor or self.root.drive or str(self.root)[:3]
                if ctypes.windll.kernel32.GetDriveTypeW(drive) != 3:  # DRIVE_FIXED
                    raise self._error("unsafe-artifact-root", "artifact-root", "fixed-local-volume", "a fixed local volume", drive)
                filesystem = ctypes.create_unicode_buffer(256)
                if not ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, None, None, None, filesystem, len(filesystem)) or filesystem.value.upper() != "NTFS":
                    raise self._error("unsafe-artifact-root", "artifact-root", "ntfs-volume", "an NTFS volume", filesystem.value or drive)
            except _StoreFailure:
                raise
            except (AttributeError, OSError) as error:
                raise self._error("unsafe-artifact-root", "artifact-root", "verified-local-ntfs-root", "a verifiable local NTFS root", str(error)) from error

    @staticmethod
    def _is_redirect(path: Path) -> bool:
        try:
            attributes = path.lstat().st_file_attributes  # type: ignore[attr-defined]
        except AttributeError:
            attributes = 0
        except OSError:
            return True
        return path.is_symlink() or bool(attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT

    def _assert_safe_path(self, path: Path, subject: str) -> None:
        try:
            relative = path.relative_to(self.root)
        except ValueError as error:
            raise self._error("unsafe-artifact-path", subject, "contained-artifact-path", str(self.root), str(path)) from error
        cursor = self.root
        if cursor.exists() and self._is_redirect(cursor):
            raise self._error("unsafe-artifact-path", subject, "non-reparse-path", "a path wholly inside the artifact root", str(cursor))
        for component in relative.parts:
            cursor /= component
            if cursor.exists() and self._is_redirect(cursor):
                raise self._error("unsafe-artifact-path", subject, "non-reparse-path", "a path wholly inside the artifact root", str(cursor))

    def _safe_mkdir(self, directory: Path) -> None:
        self._assert_safe_path(directory, "artifact-root")
        directory.mkdir(parents=True, exist_ok=True)
        self._assert_safe_path(directory, "artifact-root")

    def _ensure_root(self) -> None:
        if self._root_failure is not None:
            raise self._root_failure
        self._validate_root()
        for directory in (self.objects, self.runs, self.locks):
            self._safe_mkdir(directory)

    @staticmethod
    def _atomic_create_or_verify(path: Path, content: bytes, *, subject: str) -> None:
        """Install immutable bytes only after a same-directory durable temp write.

        A hard-link create is the no-overwrite atomic install primitive on both
        NTFS and the POSIX filesystems used by the portable test matrix.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=".immutable-", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            try:
                os.link(temp_path, path)
            except FileExistsError:
                try:
                    existing = path.read_bytes()
                except OSError as error:
                    raise FilesystemArtifactStore._error("artifact-read-failed", subject, "read-existing", "a readable immutable file", str(error)) from error
                if existing != content:
                    raise FilesystemArtifactStore._error("immutable-collision", subject, "create-or-verify", "identical canonical bytes at an existing address", "different bytes already exist")
        except OSError as error:
            raise FilesystemArtifactStore._error("artifact-write-failed", subject, "durable-write", "a flushed immutable file", str(error), retryable=True) from error
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

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
            if os.name == "nt":
                import ctypes
                # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
                if not ctypes.windll.kernel32.MoveFileExW(str(temp_path), str(path), 0x1 | 0x8):
                    raise OSError(ctypes.get_last_error(), "MoveFileExW write-through replacement failed")
            else:
                os.replace(temp_path, path)
                directory_fd = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except OSError as error:
            raise FilesystemArtifactStore._error("reference-write-failed", "run-reference", "same-directory-atomic-replace", "an atomically replaced, durable reference", str(error), retryable=True) from error
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _is_strict_kernel_model(value: object) -> bool:
        if not isinstance(value, KernelModel):
            return False
        config = value.__class__.model_config
        return config.get("frozen") is True and config.get("strict") is True and config.get("extra") == "forbid"

    def put_object(self, value: KernelModel) -> ObjectWriteResult:
        try:
            self._ensure_root()
            if not self._is_strict_kernel_model(value):
                raise self._error("invalid-content-model", "content-object", "strict-frozen-kernel-model", "a strict frozen KernelModel", type(value).__name__)
            content = canonical_bytes(value)
            digest = sha256_digest(content)
            self._atomic_create_or_verify(self._object_path(digest), content, subject="content-object")
            return ObjectWriteResult(digest=digest)
        except _StoreFailure as failure:
            return ObjectWriteResult(error=failure.error)
        except (TypeError, ValueError, OSError) as error:
            return ObjectWriteResult(error=self._unexpected("content-object", error))

    def read_object(self, digest: str, model: type[KernelModel] | None = None) -> ObjectReadResult:
        try:
            self._ensure_root()
            if model is not None and (not isinstance(model, type) or not issubclass(model, KernelModel)):
                raise self._error("object-schema-mismatch", "content-object", "strict-kernel-model-schema", "a KernelModel contract type", repr(model))
            path = self._object_path(digest)
            if not path.is_file():
                raise self._error("object-missing", "content-object", "immutable-object-present", "an object at its digest address", digest)
            content = path.read_bytes()
            if sha256_digest(content) != digest:
                raise self._error("object-integrity-failure", "content-object", "digest-address-match", digest, sha256_digest(content))
            # Parsing proves a stored object is canonical JSON, not merely hash-matching bytes.
            if canonical_bytes(load_strict_json(content)) != content:
                raise self._error("object-integrity-failure", "content-object", "canonical-json", "canonical JSON bytes", "non-canonical bytes")
            value: BaseModel | None = None
            if model is not None:
                try:
                    value = model.model_validate_json(content)
                except ValidationError as error:
                    raise self._error("object-schema-mismatch", "content-object", "expected-contract-schema", model.__name__, str(error)) from error
            return ObjectReadResult(canonical_bytes=content, value=value)
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
        path = self.locks / f"{run_id}.lock"
        self._assert_safe_path(path, "lock")
        return path

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

    def _acquire_owner_record(self, path: Path, owner: LockOwner, *, subject: str) -> None:
        """Exclusive durable owner acquisition with exact-identity reclamation."""
        try:
            descriptor, temp_name = tempfile.mkstemp(prefix=".owner-", suffix=".tmp", dir=path.parent)
            temp_path = Path(temp_name)
            try:
                with os.fdopen(descriptor, "wb") as target:
                    content = canonical_bytes(owner)
                    target.write(content)
                    target.flush()
                    os.fsync(target.fileno())
                try:
                    os.link(temp_path, path)
                    return
                except FileExistsError:
                    pass
            finally:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        except OSError as error:
            raise self._error("lock-write-failed", subject, "durable-owner-create", "a flushed immutable owner record", str(error), retryable=True) from error

        incumbent = self._read_lock_owner(path)
        if incumbent.host != socket.gethostname():
            raise self._error("lock-ambiguous", subject, "local-host-owner", socket.gethostname(), incumbent.host)
        actual = self._current_process_identity(incumbent.pid)
        reclaim = actual is not None and actual != incumbent.process_started_identity
        if actual is None:
            reclaim = self._process_is_positively_dead(incumbent.pid)
        if not reclaim:
            code = "lock-contended" if actual == incumbent.process_started_identity else "lock-ambiguous"
            raise self._error(code, subject, "positive-death-proof", "a provably dead exact process", "live or unverifiable owner", retryable=True)
        try:
            # Re-read exact canonical bytes before removing.  A mismatched
            # record means another actor won the handoff race.
            if self._read_lock_owner(path) != incumbent:
                raise self._error("lock-contended", subject, "exclusive-lock-acquisition", "an unchanged stale owner", "owner changed while reclaiming", retryable=True)
            path.unlink()
        except _StoreFailure:
            raise
        except (OSError, FileNotFoundError) as error:
            raise self._error("lock-contended", subject, "exclusive-lock-acquisition", "an unchanged stale owner", str(error), retryable=True) from error
        try:
            self._acquire_owner_record(path, owner, subject=subject)
        except RecursionError as error:
            raise self._error("lock-contended", subject, "exclusive-lock-acquisition", "a free owner record", "reclaim race", retryable=True) from error

    @contextmanager
    def _run_lock(self, run_id: str) -> Iterator[LockOwner]:
        path = self._lock_path(run_id)
        owner = self._owner()
        acquired = False
        gate = self.locks / f".{run_id}.acquire"
        self._assert_safe_path(gate, "lock-gate")
        gate_acquired = False
        try:
            self._acquire_owner_record(gate, owner, subject="lock-gate")
            gate_acquired = True
            self._acquire_owner_record(path, owner, subject="lock")
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
            if gate_acquired:
                try:
                    if gate.exists() and self._read_lock_owner(gate) == owner:
                        gate.unlink()
                except (OSError, _StoreFailure):
                    pass

    def _read_model(self, digest: str, model: type[KernelModel]) -> KernelModel:
        result = self.read_object(digest, model)
        if result.error is not None or result.canonical_bytes is None:
            raise _StoreFailure(result.error or self._unexpected("content-object", RuntimeError("missing object result")))
        if result.value is None:
            raise self._error("object-schema-mismatch", "content-object", "expected-contract-schema", model.__name__, "typed read returned no model")
        return result.value  # type: ignore[return-value]

    def _ref_path(self, run_id: str) -> Path:
        path = self._run_dir(run_id) / "refs" / "manifest.json"
        self._assert_safe_path(path, "run-reference")
        return path

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
    def _manifest_inventory_key(manifest: UnitManifest) -> dict[str, object]:
        data = manifest.model_dump()
        data.pop("units")
        data.pop("previous_manifest_digest")
        return data

    @staticmethod
    def _unit_advance_is_legal(base: UnitRecord, candidate: UnitRecord) -> bool:
        base_data, candidate_data = base.model_dump(), candidate.model_dump()
        base_state = base_data.pop("lifecycle_state")
        candidate_state = candidate_data.pop("lifecycle_state")
        current = UnitLifecycleState(base_state)
        target = UnitLifecycleState(candidate_state)
        if target not in legal_next_states(current):
            return False
        if target is UnitLifecycleState.FAILED:
            old_failure = base_data.pop("failed_unit")
            new_failure = candidate_data.pop("failed_unit")
            return (old_failure is None and new_failure is not None
                    and new_failure.get("kind") == ProvenanceKind.FAILED_UNIT
                    and base_data == candidate_data)
        return base_data == candidate_data

    def _validate_successor(self, base: UnitManifest, successor: UnitManifest, predecessor_digest: str) -> None:
        if successor.previous_manifest_digest != predecessor_digest:
            raise self._error("manifest-conflict", "manifest", "declared-predecessor", predecessor_digest, repr(successor.previous_manifest_digest))
        if self._manifest_inventory_key(base) != self._manifest_inventory_key(successor):
            raise self._error("manifest-conflict", "manifest", "immutable-manifest-level-data", "unchanged manifest-level data", "manifest-level divergence")
        if tuple(unit.source_unit_id for unit in base.units) != tuple(unit.source_unit_id for unit in successor.units):
            raise self._error("manifest-conflict", "manifest", "identical-ordered-inventory", "the current ordered unit inventory", "unit inventory or order changed")
        advanced = False
        for before, after in zip(base.units, successor.units, strict=True):
            if before != after and not self._unit_advance_is_legal(before, after):
                raise self._error("manifest-conflict", f"unit:{before.source_unit_id}", "single-legal-unit-advance", "exactly one declared lifecycle edge without immutable mutation", "illegal unit mutation or lifecycle skip")
            advanced = advanced or before != after
        if not advanced:
            raise self._error("manifest-conflict", "manifest", "nonempty-successor-advance", "at least one legal UnitRecord lifecycle advance", "zero unit advances")

    def _rebase(self, base: UnitManifest, current: UnitManifest, proposed: UnitManifest, current_digest: str) -> UnitManifest:
        if self._manifest_inventory_key(base) != self._manifest_inventory_key(current) or self._manifest_inventory_key(base) != self._manifest_inventory_key(proposed):
            raise self._error("manifest-conflict", "manifest", "immutable-manifest-level-data", "identical base inventory, provenance, and status", "manifest-level divergence")
        base_units = {unit.source_unit_id: unit for unit in base.units}
        current_units = {unit.source_unit_id: unit for unit in current.units}
        proposed_units = {unit.source_unit_id: unit for unit in proposed.units}
        if (tuple(unit.source_unit_id for unit in base.units) != tuple(unit.source_unit_id for unit in current.units)
                or tuple(unit.source_unit_id for unit in base.units) != tuple(unit.source_unit_id for unit in proposed.units)):
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
        self._assert_safe_path(path, "operational-receipt")
        self._atomic_create_or_verify(path, content, subject="operational-receipt")
        return digest

    def _invocation_dir(self, run_id: str) -> Path:
        path = self._run_dir(run_id) / "invocations"
        self._assert_safe_path(path, "invocation-receipt")
        self._safe_mkdir(path)
        return path

    def _write_invocation_receipt(self, receipt: InvocationReceipt) -> str:
        content = canonical_bytes(receipt)
        digest = sha256_digest(content)
        path = self._invocation_dir(receipt.run_id) / f"{digest}.json"
        self._assert_safe_path(path, "invocation-receipt")
        self._atomic_create_or_verify(path, content, subject="invocation-receipt")
        return digest

    def _read_invocation_receipt(self, run_id: str, digest: str) -> InvocationReceipt:
        path = self._invocation_dir(run_id) / f"{digest}.json"
        self._assert_safe_path(path, "invocation-receipt")
        try:
            content = path.read_bytes()
            if sha256_digest(content) != digest or canonical_bytes(load_strict_json(content)) != content:
                raise self._error("invocation-recovery-invalid", "invocation-receipt", "receipt-integrity", digest, "digest or canonical bytes mismatch")
            receipt = InvocationReceipt.model_validate_json(content)
            if receipt.run_id != run_id:
                raise self._error("invocation-recovery-invalid", "invocation-receipt", "receipt-run-binding", run_id, receipt.run_id)
            return receipt
        except _StoreFailure:
            raise
        except (OSError, HostileJsonError, ValidationError, TypeError, ValueError) as error:
            raise self._error("invocation-recovery-invalid", "invocation-receipt", "readable-strict-receipt", "a valid canonical invocation receipt", str(error)) from error

    def recover_invocation_receipts(self, run_id: str) -> InvocationRecoveryResult:
        """Recover the separate non-manifest invocation chain, oldest first."""
        try:
            self._ensure_root()
            directory = self._invocation_dir(run_id)
            paths = tuple(directory.glob("*.json"))
            if not paths:
                return InvocationRecoveryResult()
            records: dict[str, InvocationReceipt] = {}
            for path in paths:
                self._assert_safe_path(path, "invocation-receipt")
                if not is_sha256_digest(path.stem):
                    raise self._error("invocation-recovery-invalid", "invocation-receipt", "digest-named-receipt", "SHA-256 receipt names", path.name)
                records[path.stem] = self._read_invocation_receipt(run_id, path.stem)
            roots = [(digest, value) for digest, value in records.items() if value.predecessor_receipt_digest is None]
            if len(roots) != 1:
                raise self._error("invocation-recovery-invalid", "invocation-receipt", "single-genesis-receipt", "exactly one genesis receipt", str(len(roots)))
            receipt_digest, receipt = roots[0]
            if receipt.attempt != 1:
                raise self._error("invocation-recovery-invalid", "invocation-receipt", "genesis-attempt", "attempt 1 for genesis", str(receipt.attempt))
            snapshot_digest = receipt.snapshot_digest
            ordered = [receipt]
            visited = {receipt_digest}
            while True:
                children = [(digest, value) for digest, value in records.items() if value.predecessor_receipt_digest == receipt_digest]
                if not children:
                    break
                if len(children) != 1:
                    raise self._error("invocation-recovery-invalid", "invocation-receipt", "linear-receipt-history", "exactly one next receipt", str(len(children)))
                receipt_digest, receipt = children[0]
                if receipt_digest in visited:
                    raise self._error("invocation-recovery-invalid", "invocation-receipt", "acyclic-receipt-chain", "an acyclic receipt chain", "receipt cycle")
                prior = ordered[-1]
                if receipt.attempt != prior.attempt + 1 or receipt.attempt_ceiling != prior.attempt_ceiling:
                    raise self._error("invocation-recovery-invalid", "invocation-receipt", "strict-next-attempt", str(prior.attempt + 1), str(receipt.attempt))
                if receipt.snapshot_digest != snapshot_digest:
                    raise self._error("invocation-recovery-invalid", "invocation-receipt", "frozen-snapshot-digest", snapshot_digest, receipt.snapshot_digest)
                visited.add(receipt_digest)
                ordered.append(receipt)
            if len(visited) != len(records):
                raise self._error("invocation-recovery-invalid", "invocation-receipt", "single-linear-history", "every receipt linked into one chain", "orphaned or divergent receipt")
            return InvocationRecoveryResult(receipts=tuple(ordered))
        except _StoreFailure as failure:
            return InvocationRecoveryResult(error=failure.error)
        except (OSError, TypeError, ValueError, AttributeError) as error:
            return InvocationRecoveryResult(error=self._unexpected("invocation-recovery", error))

    def append_invocation_receipt(self, receipt: InvocationReceipt) -> InvocationAppendResult:
        try:
            self._ensure_root()
            if not isinstance(receipt, InvocationReceipt):
                raise self._error("invalid-invocation-receipt", "invocation-receipt", "strict-contract", "an InvocationReceipt", type(receipt).__name__)
            self._run_dir(receipt.run_id)
            with self._run_lock(receipt.run_id):
                recovered = self.recover_invocation_receipts(receipt.run_id)
                if recovered.error is not None:
                    raise _StoreFailure(recovered.error)
                history = recovered.receipts
                prior = history[-1] if history else None
                if prior is None:
                    if receipt.attempt != 1 or receipt.predecessor_receipt_digest is not None:
                        raise self._error("invocation-history-invalid", "invocation-receipt", "genesis-attempt", "attempt 1 without a predecessor", f"attempt={receipt.attempt}")
                else:
                    prior_digest = sha256_digest(canonical_bytes(prior))
                    if receipt.predecessor_receipt_digest != prior_digest or receipt.attempt != prior.attempt + 1 or receipt.attempt_ceiling != prior.attempt_ceiling or receipt.snapshot_digest != prior.snapshot_digest:
                        raise self._error("invocation-history-invalid", "invocation-receipt", "strict-next-receipt", f"attempt {prior.attempt + 1} with the current predecessor", f"attempt={receipt.attempt}")
                return InvocationAppendResult(receipt_digest=self._write_invocation_receipt(receipt))
        except _StoreFailure as failure:
            return InvocationAppendResult(error=failure.error)
        except (OSError, TypeError, ValueError, AttributeError) as error:
            return InvocationAppendResult(error=self._unexpected("invocation-receipt", error))

    def _latest_receipt(self, run_id: str, reference: RunReference | None) -> tuple[str, OperationalReceipt] | None:
        """Find the unique append-only receipt head, including failed attempts.

        The run reference still names only a completed manifest.  Receipts after
        it are operational history and become visible in recovery once a later
        completed receipt links them into the committed chain.
        """
        receipt_dir = self._run_dir(run_id) / "receipts"
        self._assert_safe_path(receipt_dir, "operational-receipt")
        if not receipt_dir.exists():
            return None
        records: dict[str, OperationalReceipt] = {}
        try:
            paths = tuple(receipt_dir.glob("*.json"))
        except OSError as error:
            raise self._error("recovery-invalid", "receipt", "readable-receipt-history", "a readable receipt directory", str(error)) from error
        for path in paths:
            self._assert_safe_path(path, "operational-receipt")
            digest = path.stem
            if not is_sha256_digest(digest):
                raise self._error("recovery-invalid", "receipt", "digest-named-receipt", "SHA-256 receipt names", path.name)
            records[digest] = self._read_receipt(run_id, digest)
        if not records:
            return None
        head_digest = reference.completion_receipt_digest if reference is not None else None
        if head_digest is not None and head_digest not in records:
            raise self._error("recovery-invalid", "receipt", "referenced-receipt-present", head_digest, "missing")
        if head_digest is None:
            roots = [
                (digest, receipt) for digest, receipt in records.items()
                if receipt.predecessor_receipt_digest is None and receipt.outcome is not OperationalOutcome.COMPLETED
            ]
            if not roots:
                return None
            if len(roots) != 1:
                raise self._error("retry-history-invalid", "receipt", "single-genesis-receipt", "exactly one genesis receipt", str(len(roots)))
            head_digest, head = roots[0]
        else:
            head = records[head_digest]
        while True:
            children = [
                (digest, receipt) for digest, receipt in records.items()
                if receipt.predecessor_receipt_digest == head_digest and receipt.outcome is not OperationalOutcome.COMPLETED
            ]
            if not children:
                return head_digest, head
            if len(children) != 1:
                raise self._error("retry-history-invalid", "receipt", "linear-receipt-history", "exactly one next receipt", str(len(children)))
            next_digest, next_receipt = children[0]
            if next_receipt.attempt != head.attempt + 1 or next_receipt.attempt_ceiling != head.attempt_ceiling:
                raise self._error("retry-history-invalid", "receipt", "strict-next-attempt", str(head.attempt + 1), str(next_receipt.attempt))
            head_digest, head = next_digest, next_receipt

    def _uncommitted_outcome_tail(self, run_id: str, reference: RunReference) -> list[OperationalReceipt]:
        """Return the linear non-completion history appended after ``reference``."""
        receipt_dir = self._run_dir(run_id) / "receipts"
        self._assert_safe_path(receipt_dir, "operational-receipt")
        records: dict[str, OperationalReceipt] = {}
        try:
            paths = tuple(receipt_dir.glob("*.json"))
        except OSError as error:
            raise self._error("recovery-invalid", "receipt", "readable-receipt-history", "a readable receipt directory", str(error)) from error
        for path in paths:
            self._assert_safe_path(path, "operational-receipt")
            digest = path.stem
            if not is_sha256_digest(digest):
                raise self._error("recovery-invalid", "receipt", "digest-named-receipt", "SHA-256 receipt names", path.name)
            records[digest] = self._read_receipt(run_id, digest)
        head_digest = reference.completion_receipt_digest
        if head_digest not in records:
            raise self._error("recovery-invalid", "receipt", "referenced-receipt-present", head_digest, "missing")
        head = records[head_digest]
        tail: list[OperationalReceipt] = []
        while True:
            children = [
                (digest, receipt) for digest, receipt in records.items()
                if receipt.predecessor_receipt_digest == head_digest and receipt.outcome is not OperationalOutcome.COMPLETED
            ]
            if not children:
                return tail
            if len(children) != 1:
                raise self._error("retry-history-invalid", "receipt", "linear-receipt-history", "exactly one next receipt", str(len(children)))
            next_digest, next_receipt = children[0]
            if next_receipt.attempt != head.attempt + 1 or next_receipt.attempt_ceiling != head.attempt_ceiling:
                raise self._error("retry-history-invalid", "receipt", "strict-next-attempt", str(head.attempt + 1), str(next_receipt.attempt))
            tail.append(next_receipt)
            head_digest, head = next_digest, next_receipt

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
            self._ensure_root()
            self._run_dir(run_id)
            if not isinstance(manifest, UnitManifest):
                raise self._error("invalid-manifest", "manifest", "unit-manifest-contract", "a UnitManifest", type(manifest).__name__)
            if expected_predecessor_digest is not None and not is_sha256_digest(expected_predecessor_digest):
                raise self._error("invalid-digest", "manifest", "expected-predecessor-digest", "a SHA-256 digest or null", repr(expected_predecessor_digest))
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
                latest = self._latest_receipt(run_id, prior_ref)
                if latest is not None:
                    _, prior_receipt = latest
                current_digest = prior_ref.manifest_digest if prior_ref else None
                # Identical republishes are deliberately idempotent: do not add a
                # self-predecessor receipt or mutate operational history.
                if current_digest == expected_predecessor_digest and current_digest is not None:
                    current = self._read_model(current_digest, UnitManifest)
                    if manifest == current:
                        if prior_ref is None or prior_receipt is None:
                            raise self._error("recovery-invalid", "run", "recoverable-current-reference", "a completed current receipt", "missing receipt")
                        return PublicationResult(reference=prior_ref, receipt=prior_receipt)
                    self._validate_successor(current, manifest, current_digest)
                elif current_digest is not None:
                    current = self._read_model(current_digest, UnitManifest)
                    if manifest == current:
                        if prior_ref is None or prior_receipt is None:
                            raise self._error("recovery-invalid", "run", "recoverable-current-reference", "a completed current receipt", "missing receipt")
                        return PublicationResult(reference=prior_ref, receipt=prior_receipt)
                if manifest.previous_manifest_digest != expected_predecessor_digest:
                    raise self._error("manifest-conflict", "manifest", "declared-predecessor", repr(expected_predecessor_digest), repr(manifest.previous_manifest_digest))
                self._validate_next_attempt(prior_receipt, attempt, attempt_ceiling)
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
                predecessor_receipt = latest[0] if latest is not None else None
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
        except (OSError, TypeError, ValueError, AttributeError) as error:
            return PublicationResult(error=self._unexpected("manifest", error))

    def record_outcome(
        self,
        run_id: str,
        *,
        stage_id: str,
        outcome: OperationalOutcome,
        attempt: int,
        attempt_ceiling: int,
        error: ActionableError | None = None,
        findings: tuple = (),
        retry_guidance: str,
        produced_artifact_digests: tuple[str, ...] = (),
    ) -> OutcomeResult:
        try:
            self._ensure_root()
            self._run_dir(run_id)
            if not isinstance(outcome, OperationalOutcome):
                raise self._error("invalid-outcome", "receipt", "operational-outcome", "an OperationalOutcome", repr(outcome))
            if outcome is OperationalOutcome.COMPLETED:
                raise self._error("invalid-outcome", "receipt", "completion-via-publication", "publish_manifest for completed manifests", outcome.value)
            with self._run_lock(run_id) as owner:
                reference = self._read_reference(run_id)
                if reference is not None:
                    recovered = self.recover(run_id)
                    if recovered.error is not None:
                        raise _StoreFailure(recovered.error)
                latest = self._latest_receipt(run_id, reference)
                prior_digest, prior = latest if latest is not None else (None, None)
                self._validate_next_attempt(prior, attempt, attempt_ceiling)
                now = datetime.now(UTC)
                receipt = OperationalReceipt(
                    run_id=run_id, stage_id=stage_id, attempt=attempt, attempt_ceiling=attempt_ceiling,
                    started_at=now, completed_at=now, outcome=outcome, retry_guidance=retry_guidance,
                    lock_owner=owner, predecessor_receipt_digest=prior_digest, findings=findings,
                    failure=error, produced_artifact_digests=produced_artifact_digests,
                )
                self._write_receipt(run_id, receipt)
                return OutcomeResult(receipt=receipt)
        except _StoreFailure as failure:
            return OutcomeResult(error=failure.error)
        except (OSError, TypeError, ValueError, AttributeError) as exception:
            return OutcomeResult(error=self._unexpected("receipt", exception))

    def _read_receipt(self, run_id: str, digest: str) -> OperationalReceipt:
        path = self._run_dir(run_id) / "receipts" / f"{digest}.json"
        self._assert_safe_path(path, "receipt")
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
            self._ensure_root()
            reference = self._read_reference(run_id)
            if reference is None:
                raise self._error("recovery-not-found", "run", "committed-run-reference", "an atomically published run reference", "no reference exists")
            receipts: list[OperationalReceipt] = []
            seen_receipts: set[str] = set()
            receipt_digest: str | None = reference.completion_receipt_digest
            while receipt_digest is not None:
                if receipt_digest in seen_receipts:
                    raise self._error("recovery-invalid", "receipt", "acyclic-receipt-chain", "an acyclic receipt chain", "receipt cycle")
                seen_receipts.add(receipt_digest)
                receipt = self._read_receipt(run_id, receipt_digest)
                receipts.append(receipt)
                receipt_digest = receipt.predecessor_receipt_digest
            chronological = list(reversed(receipts))
            # The reference remains the sole manifest commit point, while a
            # linear tail of failed/reconciliation outcomes remains visible
            # operational history for resume and retry.
            chronological.extend(self._uncommitted_outcome_tail(run_id, reference))
            self._validate_receipt_attempt_history(list(reversed(chronological)))
            current_manifest_digest: str | None = None
            for receipt in chronological:
                if receipt.outcome is not OperationalOutcome.COMPLETED:
                    continue
                if receipt.manifest_link is None:
                    raise self._error("recovery-invalid", "receipt", "completion-link", "a completed manifest link", "missing")
                link = receipt.manifest_link
                if link.predecessor_manifest_digest != current_manifest_digest:
                    raise self._error("recovery-invalid", "receipt", "completion-predecessor-link", repr(current_manifest_digest), repr(link.predecessor_manifest_digest))
                if link.successor_manifest_digest == link.predecessor_manifest_digest:
                    raise self._error("recovery-invalid", "receipt", "non-self-successor-link", "different predecessor and successor digests", link.successor_manifest_digest)
                cursor = self._read_model(link.successor_manifest_digest, UnitManifest)
                if cursor.previous_manifest_digest != current_manifest_digest:
                    raise self._error("recovery-invalid", "manifest", "manifest-predecessor-link", repr(current_manifest_digest), repr(cursor.previous_manifest_digest))
                current_manifest_digest = link.successor_manifest_digest
            if current_manifest_digest != reference.manifest_digest:
                raise self._error("recovery-invalid", "run-reference", "reference-completion-alignment", reference.manifest_digest, repr(current_manifest_digest))
            manifest = self._read_model(reference.manifest_digest, UnitManifest)
            return RecoveryResult(reference=reference, manifest=manifest, receipts=tuple(reversed(chronological)))
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
