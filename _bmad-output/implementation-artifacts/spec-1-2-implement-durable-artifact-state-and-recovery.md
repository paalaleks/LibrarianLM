---
title: '1.2 Implement Durable Artifact State and Recovery'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 0
baseline_commit: '220bea90ca790c3749144885abd1a14aea098da6'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Workflow content and operational progress have no durable ledger, so interruption, retries, and concurrent publication can lose provenance or expose partial work as complete.

**Approach:** Add a filesystem-backed, content-addressed artifact store with immutable receipts, atomic manifest publication, deterministic conflict handling, exclusive per-run locking, and verified-chain recovery for the local Windows/NTFS deployment envelope.

## Boundaries & Constraints

**Always:** Keep all code and tests under `src/i18n-pipeline`; store canonical content immutably by the SHA-256 of its exact canonical bytes; keep timestamps, attempts, paths, lock ownership, and retry data in immutable receipts rather than deterministic content. A run reference binds both the current manifest digest and its completion-receipt digest and is the sole commit point. Publish successor object, then receipt, then atomically replace the reference under a run lock after rereading the expected predecessor. Rebase only legal, disjoint whole-`UnitRecord` advances over an identical base inventory and immutable manifest-level data, emitting units in ordinal order. Verify every object, reference, receipt link, and manifest predecessor before resume. Lock ownership includes local host, PID, and process-start identity; reclaim only after positively proving that exact local process is dead.

**Ask First:** Adding dependencies; changing canonical digest or identity rules; supporting non-local, non-NTFS, synchronized, removable, or network storage; broadening rebase beyond unit-record advances; changing public Story 1.1 contracts beyond adding the manifest predecessor link and Story 1.2 persistence contracts.

**Never:** Overwrite content-addressed objects or receipts; treat temporary, orphaned, unlinked, corrupt, or unverifiable files as committed; infer completion from object presence; silently resolve overlapping or manifest-level changes; reuse the provider-specific `GatewayReceipt`; expose uncaught filesystem, parsing, locking, or validation exceptions at the store boundary.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Object put/read | Valid canonical model, including repeat publication | Create-or-verify one digest object; read returns only hash-matching canonical bytes | Corrupt collision, missing object, tampering, or schema mismatch fails closed with an actionable error |
| Manifest commit | Genesis or successor with matching expected predecessor | Object and immutable receipt precede atomic reference replacement; receipt binds predecessor/successor | Torn ref or failure before replacement remains incomplete and recoverable |
| Concurrent successor | Current and proposed derive from the same base | Rebase disjoint legal unit advances deterministically | Overlap, illegal transition, inventory/order, provenance, status, or other manifest-level divergence returns `manifest-conflict` |
| Recovery/retry | Interrupted run or recoverable failure | Follow verified reference, receipt, and manifest chains; append a new attempt without rewriting history | Missing link, cycle, wrong predecessor, digest mismatch, or orphan state never appears complete |
| Lock contention | Live, dead, reused, or unverifiable owner identity | Exactly one writer; reclaim only a positively dead exact process | Live or ambiguous ownership fails closed without stealing the lock |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py:66` -- strict/frozen contract base; add generic operational receipt/reference contracts and nullable genesis `UnitManifest.previous_manifest_digest` without weakening inventory invariants at line 378.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/{canonical.py:42,identity.py:61,lifecycle.py:52,errors.py:15}` -- reuse exact canonical bytes and digests, legal unit transitions, and stable actionable failures.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/__init__.py:1` -- expose the authoritative Story 1.2 contract surface; keep `GatewayReceipt` provider-specific.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/` -- new persistence protocol separating store semantics from filesystem mechanics.
- `src/i18n-pipeline/src/librarianlm_i18n/adapters/` -- new local filesystem implementation for immutable objects/receipts, durable atomic refs, per-run locks, CAS/rebase, and recovery.
- `src/i18n-pipeline/tests/contracts/test_kernel.py:29` -- update manifest fixtures and public-inventory assertions; preserve the existing strict immutable test style.
- `src/i18n-pipeline/tests/` -- add tempfile-backed persistence, crash-window, conflict, chain-validation, retry, traversal, and lock-liveness matrices using stdlib `unittest`.
- `_bmad-output/planning-artifacts/architecture/architecture-LibrarianLM-2026-08-23/ARCHITECTURE-SPINE.md:51` -- read-only authority for CAS/recovery, receipt separation, local Windows/NTFS envelope, wire conventions, and artifact-root layout.

## Tasks & Acceptance

**Execution:**
- [x] `src/i18n-pipeline/src/librarianlm_i18n/kernel/{contracts.py,__init__.py}` -- define and export strict immutable manifest-link, run-reference, finding/error, lock-owner, and operational/completion receipt contracts with validated UTC time ordering, attempts/ceilings, outcomes, retry guidance, and digest links.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/ports/{__init__.py,artifact_store.py}` -- specify typed object, publication, history, and recovery operations independent of storage paths.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/adapters/{__init__.py,filesystem_artifact_store.py}` -- implement safe run-ID mapping, create-or-verify objects, append-only receipts, lock ownership/liveness, durable same-directory atomic refs, narrow three-way rebase, and verified recovery.
- [x] `src/i18n-pipeline/tests/contracts/test_kernel.py` and focused persistence tests under `src/i18n-pipeline/tests/` -- cover every matrix row, deterministic ordering, genesis/successor chains, crash stages, same-predecessor contention, retry observability, hostile paths, and ambiguous stale locks.

**Acceptance Criteria:**
- Given identical valid canonical content, when published and read repeatedly, then one immutable digest object is returned and every read verifies exact canonical bytes against its address.
- Given a matching expected predecessor under exclusive lock, when publication completes, then the atomic run reference binds the successor manifest and completion receipt whose immutable history records all required operational fields.
- Given concurrent successors, when only disjoint units legally advance, then the store deterministically rebases them in Source Unit order; when any change overlaps or falls outside that envelope, then it returns `manifest-conflict`.
- Given interruption, corruption, or retry, when recovery runs, then only a fully verified linked chain is resumable, incomplete state is not complete, and retry history is appended with stable identity and actionable outcome data.

## Spec Change Log

## Design Notes

The atomic run reference is a small canonical pointer containing both manifest and completion-receipt digests. Genesis uses a null manifest predecessor and a null receipt predecessor. Rebase is a three-way comparison of base/current/proposed manifests: identity, inventory, ordinals, and all manifest-level fields must match; each side may only replace whole unit records through legal lifecycle edges; a unit changed on both sides conflicts. Object/receipt files use create-or-verify, while reference updates use a same-directory temporary file, file flush, atomic replace, and supported directory durability handling. Pre-reference artifacts are harmless orphans and never become committed history.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` -- expected: locked environment installs without lockfile changes.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` from `src/i18n-pipeline` -- expected: all kernel and persistence tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.ports; import librarianlm_i18n.adapters"` from `src/i18n-pipeline` -- expected: authoritative package surfaces import successfully.

## Suggested Review Order

**Commit protocol and recovery**

- Centralizes immutable object, receipt, lock, CAS, and chain-verification semantics.
  [`filesystem_artifact_store.py:50`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py#L50)

- Publishes only after validated history and an exclusive per-run lock.
  [`filesystem_artifact_store.py:407`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py#L407)

- Reconstructs only a complete, aligned manifest and receipt history.
  [`filesystem_artifact_store.py:489`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py#L489)

**Strict contract boundary**

- Defines immutable linkage, retry, lock-owner, and completion-receipt contracts.
  [`contracts.py:339`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L339)

- Adds the nullable predecessor link required for genesis manifests.
  [`contracts.py:454`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L454)

**Storage abstraction**

- Keeps caller-visible persistence outcomes independent of filesystem paths.
  [`artifact_store.py:43`](../../src/i18n-pipeline/src/librarianlm_i18n/ports/artifact_store.py#L43)

**Verification matrix**

- Exercises immutable storage, CAS/rebase, recovery, retries, crash windows, and locks.
  [`test_filesystem_artifact_store.py:53`](../../src/i18n-pipeline/tests/test_filesystem_artifact_store.py#L53)
