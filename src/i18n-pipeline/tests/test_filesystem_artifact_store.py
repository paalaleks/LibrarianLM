from __future__ import annotations

import os
import socket
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from pydantic import BaseModel, ValidationError

from librarianlm_i18n.adapters import FilesystemArtifactStore
from librarianlm_i18n import kernel
from librarianlm_i18n.ports import ObjectReadResult, ObjectWriteResult, OutcomeResult, PublicationResult, RecoveryResult


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
UNIT_A = f"source-unit:{DIGEST_A}"
UNIT_B = f"source-unit:{DIGEST_B}"
GROUP_A = f"projection-group:{DIGEST_A}"
GROUP_B = f"projection-group:{DIGEST_B}"


def statuses() -> kernel.StatusVector:
    return kernel.StatusVector(
        processing=kernel.StatusValue.NOT_STARTED,
        completeness=kernel.StatusValue.UNKNOWN,
        compliance=kernel.StatusValue.UNKNOWN,
        review=kernel.StatusValue.NOT_STARTED,
        publication=kernel.StatusValue.NOT_READY,
    )


def unit(unit_id: str, ordinal: int, group_id: str, state: kernel.UnitLifecycleState = kernel.UnitLifecycleState.PREPARED) -> kernel.UnitRecord:
    return kernel.UnitRecord(
        source_unit_id=unit_id, ordinal=ordinal,
        locator=kernel.TypedLocator(locator=f"dom:body/p[{ordinal + 1}]", kind="text"),
        source_digest=DIGEST_A, content_class=kernel.ContentClass.TEXT,
        eligibility=kernel.Eligibility.REQUIRED, eligibility_reason="fixture text",
        projection_group_id=group_id, lifecycle_state=state,
    )


def manifest(*, previous: str | None = None, first: kernel.UnitLifecycleState = kernel.UnitLifecycleState.PREPARED, second: kernel.UnitLifecycleState = kernel.UnitLifecycleState.PREPARED) -> kernel.UnitManifest:
    first_unit, second_unit = unit(UNIT_A, 0, GROUP_A, first), unit(UNIT_B, 1, GROUP_B, second)
    groups = (
        kernel.ProjectionMap(group_id=GROUP_A, canonical_source_unit_id=UNIT_A, member_locators=(first_unit.locator,), ownership=kernel.ProjectionOwnership.WORKFLOW, cardinality=1, transformation_rule="replace-text"),
        kernel.ProjectionMap(group_id=GROUP_B, canonical_source_unit_id=UNIT_B, member_locators=(second_unit.locator,), ownership=kernel.ProjectionOwnership.WORKFLOW, cardinality=1, transformation_rule="replace-text"),
    )
    return kernel.UnitManifest(source_package_digest=DIGEST_A, run_snapshot_digest=DIGEST_B,
        segmentation_profile_id="component:segmenter-v1", profile_id="component:profile-v1",
        units=(first_unit, second_unit), projection_groups=groups, status=statuses(), provenance=(), previous_manifest_digest=previous)


class FilesystemArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = FilesystemArtifactStore(self.temp.name)

    def _replace_reference(self, run_id: str, reference: kernel.RunReference) -> None:
        path = Path(self.temp.name) / "runs" / run_id / "refs" / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(kernel.canonical_bytes(reference))

    def test_object_create_verify_read_and_tamper_fail_closed(self) -> None:
        value = manifest()
        first = self.store.put_object(value)
        second = self.store.put_object(value)
        self.assertIsNone(first.error)
        self.assertEqual(first.digest, second.digest)
        read = self.store.read_object(first.digest)
        self.assertEqual(read.canonical_bytes, kernel.canonical_bytes(value))
        object_path = Path(self.temp.name) / "objects" / "sha256" / f"{first.digest}.json"
        object_path.write_bytes(b"{}\n")
        self.assertEqual(self.store.read_object(first.digest).error.code, "object-integrity-failure")

    def test_genesis_successor_and_retry_recovery_are_fully_linked(self) -> None:
        genesis = manifest()
        initial = self.store.publish_manifest("run-1", genesis, expected_predecessor_digest=None, attempt=1, attempt_ceiling=3)
        self.assertIsNone(initial.error)
        successor = manifest(previous=initial.reference.manifest_digest, first=kernel.UnitLifecycleState.PROPOSED)
        published = self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=2, attempt_ceiling=3)
        self.assertIsNone(published.error)
        recovered = self.store.recover("run-1")
        self.assertIsNone(recovered.error)
        self.assertEqual(recovered.reference, published.reference)
        self.assertEqual(tuple(receipt.attempt for receipt in recovered.receipts), (2, 1))
        self.assertEqual(recovered.manifest.units[0].lifecycle_state, kernel.UnitLifecycleState.PROPOSED)

    def test_orphan_and_torn_reference_never_recover_as_complete(self) -> None:
        self.store.put_object(manifest())
        self.assertEqual(self.store.recover("run-1").error.code, "recovery-not-found")
        ref = Path(self.temp.name) / "runs" / "run-1" / "refs" / "manifest.json"
        ref.parent.mkdir(parents=True)
        ref.write_bytes(b"{not-json}\n")
        self.assertEqual(self.store.recover("run-1").error.code, "reference-invalid")

    def test_disjoint_unit_advances_rebase_in_ordinal_order_and_overlap_conflicts(self) -> None:
        base = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=4)
        base_digest = base.reference.manifest_digest
        left = self.store.publish_manifest("run-1", manifest(previous=base_digest, first=kernel.UnitLifecycleState.PROPOSED), expected_predecessor_digest=base_digest, attempt=2, attempt_ceiling=4)
        self.assertIsNone(left.error)
        right = self.store.publish_manifest("run-1", manifest(previous=base_digest, second=kernel.UnitLifecycleState.PROPOSED), expected_predecessor_digest=base_digest, attempt=3, attempt_ceiling=4)
        self.assertIsNone(right.error)
        self.assertTrue(right.rebased)
        recovered = self.store.recover("run-1")
        self.assertEqual([record.ordinal for record in recovered.manifest.units], [0, 1])
        self.assertEqual([record.lifecycle_state for record in recovered.manifest.units], [kernel.UnitLifecycleState.PROPOSED, kernel.UnitLifecycleState.PROPOSED])
        overlap = self.store.publish_manifest("run-1", manifest(previous=base_digest, first=kernel.UnitLifecycleState.PROPOSED), expected_predecessor_digest=base_digest, attempt=4, attempt_ceiling=4)
        self.assertEqual(overlap.error.code, "manifest-conflict")

    def test_rebase_rejects_manifest_level_and_illegal_lifecycle_divergence(self) -> None:
        base = self.store.publish_manifest("run-1", manifest(first=kernel.UnitLifecycleState.COMMITTED), expected_predecessor_digest=None, attempt=1, attempt_ceiling=3)
        base_digest = base.reference.manifest_digest
        current = self.store.publish_manifest("run-1", manifest(previous=base_digest, first=kernel.UnitLifecycleState.COMMITTED, second=kernel.UnitLifecycleState.PROPOSED), expected_predecessor_digest=base_digest, attempt=2, attempt_ceiling=3)
        altered_status = manifest(previous=base_digest, first=kernel.UnitLifecycleState.PREPARED)
        illegal = self.store.publish_manifest("run-1", altered_status, expected_predecessor_digest=base_digest, attempt=3, attempt_ceiling=3)
        self.assertEqual(illegal.error.code, "manifest-conflict")
        manifest_level = altered_status.model_copy(update={"status": statuses().model_copy(update={"processing": kernel.StatusValue.COMPLETE})})
        rejected = self.store.publish_manifest("run-1", manifest_level, expected_predecessor_digest=base_digest, attempt=3, attempt_ceiling=3)
        self.assertEqual(rejected.error.code, "manifest-conflict")

    def test_hostile_run_ids_and_live_or_ambiguous_lock_owners_fail_closed(self) -> None:
        self.assertEqual(self.store.publish_manifest("../escape", manifest(), expected_predecessor_digest=None).error.code, "invalid-run-id")
        lock = Path(self.temp.name) / "locks" / "run-1.lock"
        owner = kernel.LockOwner(host=socket.gethostname(), pid=__import__("os").getpid(), process_started_identity=self.store._current_process_identity(__import__("os").getpid()), acquired_at=datetime.now(UTC))
        lock.write_bytes(kernel.canonical_bytes(owner))
        self.assertEqual(self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None).error.code, "lock-contended")
        lock.unlink()
        stale = owner.model_copy(update={"pid": 99999999, "process_started_identity": "stale"})
        lock.write_bytes(kernel.canonical_bytes(stale))
        reclaimed = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None)
        self.assertIsNone(reclaimed.error)

    def test_reused_and_remote_lock_owners_are_reclaimed_or_rejected_safely(self) -> None:
        lock = Path(self.temp.name) / "locks" / "run-1.lock"
        current_identity = self.store._current_process_identity(__import__("os").getpid())
        reused = kernel.LockOwner(host=socket.gethostname(), pid=__import__("os").getpid(), process_started_identity=f"not-{current_identity}", acquired_at=datetime.now(UTC))
        lock.write_bytes(kernel.canonical_bytes(reused))
        self.assertIsNone(self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None).error)
        lock.write_bytes(kernel.canonical_bytes(reused.model_copy(update={"host": "another-host"})))
        self.assertEqual(self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None).error.code, "lock-ambiguous")

    def test_corrupt_receipt_and_predecessor_chain_fail_recovery(self) -> None:
        publication = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None)
        receipt = Path(self.temp.name) / "runs" / "run-1" / "receipts" / f"{publication.reference.completion_receipt_digest}.json"
        receipt.write_bytes(b"{}\n")
        self.assertEqual(self.store.recover("run-1").error.code, "recovery-invalid")

    def test_existing_history_must_recover_before_a_new_publication(self) -> None:
        initial = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=2)
        receipt = Path(self.temp.name) / "runs" / "run-1" / "receipts" / f"{initial.reference.completion_receipt_digest}.json"
        receipt.write_bytes(b"{}\n")
        rejected = self.store.publish_manifest("run-1", manifest(previous=initial.reference.manifest_digest), expected_predecessor_digest=initial.reference.manifest_digest, attempt=2, attempt_ceiling=2)
        self.assertEqual(rejected.error.code, "recovery-invalid")

    def test_cross_run_reference_is_rejected_for_recovery_and_publication(self) -> None:
        published = self.store.publish_manifest("run-a", manifest(), expected_predecessor_digest=None)
        self._replace_reference("run-b", published.reference)
        self.assertEqual(self.store.recover("run-b").error.code, "reference-invalid")
        result = self.store.publish_manifest("run-b", manifest(), expected_predecessor_digest=None)
        self.assertEqual(result.error.code, "reference-invalid")

    def test_retry_history_is_strict_and_recovery_detects_hash_valid_rewrite(self) -> None:
        initial = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=3)
        successor = manifest(previous=initial.reference.manifest_digest, first=kernel.UnitLifecycleState.PROPOSED)
        self.assertEqual(self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=1, attempt_ceiling=3).error.code, "retry-history-invalid")
        self.assertEqual(self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=2, attempt_ceiling=2).error.code, "retry-history-invalid")
        second = self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=2, attempt_ceiling=3)
        self.assertIsNone(second.error)
        rewritten = second.receipt.model_copy(update={"attempt": 1})
        rewritten_digest = self.store._write_receipt("run-1", rewritten)
        self._replace_reference("run-1", second.reference.model_copy(update={"completion_receipt_digest": rewritten_digest}))
        self.assertEqual(self.store.recover("run-1").error.code, "recovery-invalid")

    def test_recovery_rejects_hash_valid_truncated_and_non_genesis_receipt_histories(self) -> None:
        initial = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=2)
        successor = manifest(previous=initial.reference.manifest_digest, first=kernel.UnitLifecycleState.PROPOSED)
        second = self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=2, attempt_ceiling=2)
        truncated = second.receipt.model_copy(update={"predecessor_receipt_digest": None})
        truncated_digest = self.store._write_receipt("run-1", truncated)
        self._replace_reference("run-1", second.reference.model_copy(update={"completion_receipt_digest": truncated_digest}))
        self.assertEqual(self.store.recover("run-1").error.code, "recovery-invalid")

        genesis = self.store.publish_manifest("run-2", manifest(), expected_predecessor_digest=None)
        extended_genesis = genesis.receipt.model_copy(update={"predecessor_receipt_digest": genesis.reference.completion_receipt_digest})
        extended_digest = self.store._write_receipt("run-2", extended_genesis)
        self._replace_reference("run-2", genesis.reference.model_copy(update={"completion_receipt_digest": extended_digest}))
        self.assertEqual(self.store.recover("run-2").error.code, "recovery-invalid")

    def test_crash_before_reference_replacement_leaves_only_orphans(self) -> None:
        with mock.patch.object(self.store, "_atomic_replace", side_effect=OSError("simulated crash before commit")):
            result = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None)
        self.assertIsNotNone(result.error)
        self.assertTrue(list((Path(self.temp.name) / "runs" / "run-1" / "receipts").glob("*.json")))
        self.assertEqual(self.store.recover("run-1").error.code, "recovery-not-found")

    def test_lock_owner_requires_canonical_bytes_and_reclaim_race_is_contention(self) -> None:
        lock = Path(self.temp.name) / "locks" / "run-1.lock"
        owner = kernel.LockOwner(host=socket.gethostname(), pid=__import__("os").getpid(), process_started_identity=self.store._current_process_identity(__import__("os").getpid()), acquired_at=datetime.now(UTC))
        lock.write_bytes(kernel.canonical_bytes(owner) + b"\n")
        self.assertEqual(self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None).error.code, "lock-owner-unverifiable")

        stale = owner.model_copy(update={"process_started_identity": f"stale-{owner.process_started_identity}"})
        replacement = owner.model_copy(update={"acquired_at": datetime.now(UTC)})
        lock.write_bytes(kernel.canonical_bytes(stale))
        original_unlink = Path.unlink

        def contender_wins(target: Path, *args: object, **kwargs: object) -> None:
            original_unlink(target, *args, **kwargs)
            if target == lock:
                lock.write_bytes(kernel.canonical_bytes(replacement))

        with mock.patch.object(Path, "unlink", contender_wins):
            result = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None)
        self.assertEqual(result.error.code, "lock-contended")
        self.assertEqual(lock.read_bytes(), kernel.canonical_bytes(replacement))

    def _retryable_error(self) -> kernel.ActionableError:
        return kernel.ActionableError(
            code="fixture-retry", workflow="fixture", subject="fixture", rule="fixture-rule",
            expected="a retry", observed="failure", retryability=kernel.Retryability.RETRYABLE,
            next_action="retry fixture",
        )

    def test_direct_current_successor_rejects_skips_mutations_and_inventory_changes(self) -> None:
        base = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=4)
        digest = base.reference.manifest_digest
        skipped = manifest(previous=digest, first=kernel.UnitLifecycleState.EVALUATED)
        self.assertEqual(self.store.publish_manifest("run-1", skipped, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=4).error.code, "manifest-conflict")
        changed = manifest(previous=digest, first=kernel.UnitLifecycleState.PROPOSED)
        mutable_unit = changed.units[0].model_copy(update={"eligibility_reason": "rewritten"})
        mutable = changed.model_copy(update={"units": (mutable_unit, changed.units[1])})
        self.assertEqual(self.store.publish_manifest("run-1", mutable, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=4).error.code, "manifest-conflict")
        reordered = changed.model_copy(update={"units": tuple(reversed(changed.units))})
        self.assertEqual(self.store.publish_manifest("run-1", reordered, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=4).error.code, "manifest-conflict")
        zero_advance = manifest().model_copy(update={"previous_manifest_digest": digest})
        self.assertEqual(self.store.publish_manifest("run-1", zero_advance, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=4).error.code, "manifest-conflict")

    def test_failed_edge_requires_new_typed_failure_and_republication_is_idempotent(self) -> None:
        base = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=3)
        digest = base.reference.manifest_digest
        invalid_failed = manifest(previous=digest, first=kernel.UnitLifecycleState.FAILED)
        self.assertEqual(self.store.publish_manifest("run-1", invalid_failed, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=3).error.code, "manifest-conflict")
        failed_unit = invalid_failed.units[0].model_copy(update={
            "failed_unit": kernel.ProvenanceReference(kind=kernel.ProvenanceKind.FAILED_UNIT, digest=DIGEST_B),
        })
        valid_failed = invalid_failed.model_copy(update={"units": (failed_unit, invalid_failed.units[1])})
        published = self.store.publish_manifest("run-1", valid_failed, expected_predecessor_digest=digest, attempt=2, attempt_ceiling=3)
        self.assertIsNone(published.error)
        repeat = self.store.publish_manifest("run-1", valid_failed, expected_predecessor_digest=published.reference.manifest_digest, attempt=3, attempt_ceiling=3)
        self.assertIsNone(repeat.error)
        self.assertEqual(repeat.reference, published.reference)
        self.assertEqual(repeat.receipt, published.receipt)
        self.assertNotEqual(repeat.receipt.manifest_link.predecessor_manifest_digest, repeat.receipt.manifest_link.successor_manifest_digest)

    def test_failed_attempts_append_before_completion_and_are_recovered(self) -> None:
        recorded = self.store.record_outcome(
            "run-1", stage_id="translate", outcome=kernel.OperationalOutcome.RETRYABLE_FAILURE,
            attempt=1, attempt_ceiling=3, error=self._retryable_error(),
            retry_guidance="retry after fixture repair", produced_artifact_digests=(DIGEST_A,),
        )
        self.assertIsNone(recorded.error)
        reused = self.store.record_outcome(
            "run-1", stage_id="translate", outcome=kernel.OperationalOutcome.RETRYABLE_FAILURE,
            attempt=1, attempt_ceiling=3, error=self._retryable_error(), retry_guidance="retry",
        )
        self.assertEqual(reused.error.code, "retry-history-invalid")
        completed = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=2, attempt_ceiling=3)
        self.assertIsNone(completed.error)
        recovered = self.store.recover("run-1")
        self.assertEqual(tuple(receipt.attempt for receipt in recovered.receipts), (2, 1))
        self.assertEqual(recovered.receipts[1].outcome, kernel.OperationalOutcome.RETRYABLE_FAILURE)

    def test_recovery_exposes_post_reference_failure_then_retry_without_advancing_manifest(self) -> None:
        initial = self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None, attempt=1, attempt_ceiling=3)
        failure = self.store.record_outcome(
            "run-1", stage_id="translate", outcome=kernel.OperationalOutcome.RETRYABLE_FAILURE,
            attempt=2, attempt_ceiling=3, error=self._retryable_error(), retry_guidance="retry fixture",
        )
        self.assertIsNone(failure.error)
        pending = self.store.recover("run-1")
        self.assertEqual(pending.reference, initial.reference)
        self.assertEqual(pending.manifest, manifest())
        self.assertEqual(tuple(receipt.attempt for receipt in pending.receipts), (2, 1))
        self.assertEqual(pending.receipts[0].outcome, kernel.OperationalOutcome.RETRYABLE_FAILURE)
        successor = manifest(previous=initial.reference.manifest_digest, first=kernel.UnitLifecycleState.PROPOSED)
        retried = self.store.publish_manifest("run-1", successor, expected_predecessor_digest=initial.reference.manifest_digest, attempt=3, attempt_ceiling=3)
        self.assertIsNone(retried.error)
        recovered = self.store.recover("run-1")
        self.assertEqual(tuple(receipt.attempt for receipt in recovered.receipts), (3, 2, 1))
        self.assertEqual(recovered.manifest.units[0].lifecycle_state, kernel.UnitLifecycleState.PROPOSED)

    def test_result_models_are_exclusive_and_typed_reads_require_kernel_contracts(self) -> None:
        for factory in (ObjectWriteResult, ObjectReadResult, OutcomeResult, PublicationResult, RecoveryResult):
            with self.subTest(factory=factory.__name__), self.assertRaises(ValidationError):
                factory()
        written = self.store.put_object(manifest())
        typed = self.store.read_object(written.digest, kernel.UnitManifest)
        self.assertIsInstance(typed.value, kernel.UnitManifest)
        class ArbitraryModel(BaseModel):
            value: str
        self.assertEqual(self.store.put_object(ArbitraryModel(value="no")).error.code, "invalid-content-model")
        self.assertEqual(self.store.read_object(written.digest, ArbitraryModel).error.code, "object-schema-mismatch")
        self.assertEqual(self.store.read_object(written.digest, kernel.RunReference).error.code, "object-schema-mismatch")
        with self.assertRaises(ValidationError):
            PublicationResult(error=self._retryable_error(), reference=kernel.RunReference(run_id="run", manifest_digest=DIGEST_A, completion_receipt_digest=DIGEST_B))

    def test_malformed_runtime_input_stale_gate_partial_install_and_windows_aliases_fail_closed(self) -> None:
        self.assertEqual(self.store.publish_manifest("run-1", object(), expected_predecessor_digest=None).error.code, "invalid-manifest")
        self.assertEqual(self.store.publish_manifest("CON", manifest(), expected_predecessor_digest=None).error.code, "invalid-run-id")
        gate = Path(self.temp.name) / "locks" / ".run-1.acquire"
        owner = kernel.LockOwner(host=socket.gethostname(), pid=99999999, process_started_identity="dead", acquired_at=datetime.now(UTC))
        gate.write_bytes(kernel.canonical_bytes(owner))
        self.assertIsNone(self.store.publish_manifest("run-1", manifest(), expected_predecessor_digest=None).error)
        failure_store = FilesystemArtifactStore(Path(self.temp.name) / "partial")
        with mock.patch("librarianlm_i18n.adapters.filesystem_artifact_store.os.link", side_effect=OSError("injected install failure")):
            failed = failure_store.put_object(manifest())
        self.assertEqual(failed.error.code, "artifact-write-failed")
        self.assertFalse(list((Path(self.temp.name) / "partial" / "objects" / "sha256").glob("*.json")))

    def test_reparse_or_symlink_artifact_root_is_rejected(self) -> None:
        target = Path(self.temp.name) / "real-root"
        target.mkdir()
        redirect = Path(self.temp.name) / "redirect-root"
        try:
            os.symlink(target, redirect, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")
        redirected = FilesystemArtifactStore(redirect)
        self.assertEqual(redirected.put_object(manifest()).error.code, "unsafe-artifact-root")
