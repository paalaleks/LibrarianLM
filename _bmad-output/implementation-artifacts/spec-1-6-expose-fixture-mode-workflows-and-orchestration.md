---
title: '1.6 Expose Fixture-Mode Workflows and Orchestration'
type: 'feature'
created: '2026-08-24'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'e1d0adf58e8453c1cad34a46e31cd29114ae2339'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Prepare, Assembly, and Validation exist as deterministic filters, but callers lack strict public boundaries, a canonical run-input record, and resumable orchestration that does not depend on caller-held digests.

**Approach:** Add exception-safe Prepare and Assemble-and-Validate Python entrypoints, freeze fixture inputs in a Run Snapshot, and compose confirmed runs through receipts that verify and reuse completed stages.

## Boundaries & Constraints

**Always:** Work only under `src/i18n-pipeline`; declare workflow identity, purpose, inputs/versions, outputs, preconditions, confirmation, retry, failure, and terminal metadata. Before Prepare, freeze source, policy, editorial/validation controls, component identities, caller-supplied `FixtureTargets`, fixture mode, and attempt ceilings; keep the derived manifest outside the snapshot. Validate raw input before feature logic, compose through verified digests, append history, and return exact output references and validation statuses.

**Ask First:** Adding dependencies or console scripts; changing canonical serialization, Story 1.2 compatibility, existing filter rules, fixture semantics, or supported versions; confirming without explicit operator authorization.

**Never:** Resolve a live Model Gateway; allow mutable/environment-driven fixture behavior; bypass detached confirmation; alter prior artifacts; reuse invalid outputs; rewrite history; equate processing or readable reports with draft eligibility, review, or publication; expose exceptions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Independent Prepare | Valid request and explicit operator authorization | Persist snapshot, run Prepare, confirm an eligible package, and return typed references | Blocked preparation stays truthful; confirmation is never implied |
| Assemble and validate | Confirmed package and snapshot-bound targets | Verify, assemble, validate, and return exact output digests/statuses | Blockers retain reports/summary but suppress the eligible draft |
| Resume | Verified snapshot, references, receipts, and stage evidence | Reuse compatible verified outputs and append the next legal attempt | Invalid evidence stops early; retries obey the frozen ceiling |
| Invalid invocation | Missing, hostile, incompatible, or cross-wired input | Return a typed failed/reconciliation result with retry guidance | No exception or partial output is advertised as complete |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py:111-123,441-453,607-620,806-845,934-1024` -- add strict snapshot, workflow declaration, invocation receipt, and terminal result contracts.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/boundary.py:71-121,187-218` -- reuse hostile-input/version gates and exception-to-`ActionableError` conversion at every public boundary.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/artifact_store.py:87-116` and `adapters/filesystem_artifact_store.py:604-804` -- append/recover non-manifest stage evidence while preserving CAS, ceilings, and chain verification.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/{prepare.py:51,assemble.py:37,validate.py:38}` -- reuse filters, verify snapshot lineage, and expose persisted output digests.
- `src/i18n-pipeline/src/librarianlm_i18n/entrypoints/` and `workflows/{assemble_validate.py,orchestrate.py}` -- add/export thin Prepare/confirm, Assemble-and-Validate, and orchestration surfaces.
- `src/i18n-pipeline/tests/` -- add kernel/store and end-to-end entrypoint/orchestration coverage with real fixture adapters.

## Tasks & Acceptance

**Execution:**
- [x] `kernel/{contracts.py,__init__.py}` and boundary models -- define canonical snapshot, descriptor, invocation, and terminal-result invariants with strict compatibility and exclusive success/error states.
- [x] `ports/artifact_store.py` and `adapters/filesystem_artifact_store.py` -- append/recover receipts with exact inputs/outputs, versions, attempts/ceilings, timing, finding count, and outcome without altering manifest semantics.
- [x] `workflows/{prepare.py,validate.py,assemble_validate.py,orchestrate.py}`, `entrypoints/`, and exports -- verify snapshots, preserve explicit confirmation, compose artifact-only stages, return durable references, and resume with explicit terminal outcomes.
- [x] `tests/` -- cover the I/O matrix, declarations, boundary interruptions/reuse, hostile lineage, frozen ceilings/snapshot, exception containment, absent gateway seam, and byte-equivalent content artifacts.

**Acceptance Criteria:**
- Given an independent workflow request, when its descriptor and raw input are inspected, then metadata is complete and invalid input fails before feature logic with a typed error.
- Given a confirmed fixture snapshot, when orchestration runs or resumes, then it verifies lineage, executes only unfinished compatible stages, appends legal receipts, and never resolves a provider.
- Given clean validation, when orchestration completes, then it returns exact digests for the Unit Manifest, eligible Translation Draft, Assembly Report, Validation Report, and Translation Run Summary without implying approval.
- Given a blocker, interruption, invalid handoff, or exhausted ceiling, when the run stops, then outcome/recoverability are explicit, history is immutable, and no partial artifact appears complete.

## Spec Change Log

## Design Notes

Use a separate invocation-receipt chain instead of redefining Story 1.2 receipts or advancing the manifest for non-manifest stages. The snapshot freezes pre-Prepare inputs; `PreparePackage` binds snapshot and manifest digests separately. Public surfaces are importable Python adapters, with no new CLI.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` from `src/i18n-pipeline` -- expected: no lockfile change.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` from `src/i18n-pipeline` -- expected: all existing and Story 1.6 tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.entrypoints; import librarianlm_i18n.workflows"` from `src/i18n-pipeline` -- expected: public surfaces import successfully.

## Suggested Review Order

**Public workflow boundaries**

- Start with strict raw-input routing, explicit confirmation, and declared public contracts.
  [`fixture.py:57`](../../src/i18n-pipeline/src/librarianlm_i18n/entrypoints/fixture.py#L57)

- Follow artifact-only assembly and blocker-aware validation composition.
  [`assemble_validate.py:56`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble_validate.py#L56)

- Inspect dual-history recovery before cached output reuse.
  [`orchestrate.py:57`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/orchestrate.py#L57)

**Trust and lineage**

- Verify durable detached confirmation and cryptographic signature checks.
  [`assemble.py:37`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py#L37)

- Confirm completed output inventory and cross-object lineage enforcement.
  [`references.py:62`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/references.py#L62)

**Contracts and persistence**

- Review frozen snapshot, declarations, terminal states, and invocation receipt invariants.
  [`contracts.py:638`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L638)

- Trace canonical invocation-chain reconstruction and append guards.
  [`filesystem_artifact_store.py:549`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py#L549)

**Verification evidence**

- Begin with clean end-to-end execution and idempotent boundary reuse.
  [`test_fixture_entrypoints.py:95`](../../src/i18n-pipeline/tests/test_fixture_entrypoints.py#L95)

- Examine valid divergent-history rejection through public orchestration.
  [`test_fixture_entrypoints.py:337`](../../src/i18n-pipeline/tests/test_fixture_entrypoints.py#L337)

- Finish with exact-inventory cross-run lineage rejection.
  [`test_fixture_entrypoints.py:375`](../../src/i18n-pipeline/tests/test_fixture_entrypoints.py#L375)
