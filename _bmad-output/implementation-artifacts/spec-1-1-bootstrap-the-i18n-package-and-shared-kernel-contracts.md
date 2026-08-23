---
title: '1.1 Bootstrap the i18n Package and Shared Kernel Contracts'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'NO_VCS'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The i18n pipeline has no package or authoritative domain kernel, so later workflows cannot exchange deterministic, version-compatible artifacts or reject bad inputs before processing.

**Approach:** Bootstrap the pinned Python package and implement one strict shared kernel for identities, contracts, canonical bytes, lifecycle legality, status orthogonality, and typed boundary failures.

## Boundaries & Constraints

**Always:** Keep all code, locks, and tests under `src/i18n-pipeline`; use Python 3.14.4, uv 0.11.19, Pydantic 2.13.4, and lxml 6.1.2 exactly. Kernel models are strict, deeply immutable, extra-forbid, explicitly versioned, and solely owned by `librarianlm_i18n.kernel`. Canonical JSON is UTF-8/LF with sorted keys and compact separators; versions/counts are integers and non-integral scores are decimal strings. Reject duplicate keys and every float, including NaN, before model validation. Keep paths, timestamps, attempts, and execution metadata outside deterministic content.

**Ask First:** Adding a dependency beyond the pinned runtime packages and test tooling; changing any public contract field required by the architecture seed; defining new semantic implications between status dimensions; placing i18n code outside the mandated package tree.

**Never:** Add workflow feature logic, persistence, live providers, services, databases, mutable manifest history, competing workflow-owned schemas, path/random/database identities, or uncaught boundary exceptions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid artifact | Strict versioned content with typed IDs and lowercase SHA-256 digests | Frozen model and repeatable canonical bytes | N/A |
| Hostile JSON | Duplicate member, unknown field, coercible value, float/NaN, or invalid version | Rejected before feature logic | Stable error names workflow, subject, rule, expected/observed, retryability, and next action |
| Lifecycle update | Legal happy, recovery, or typed-failure edge | Monotonic next state; five status dimensions remain independent | Skipped, backward, or post-terminal edge returns stable illegal-transition code |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/` -- currently empty; exclusive location for this vertical per root `AGENTS.md`.
- `_bmad-output/planning-artifacts/architecture/architecture-LibrarianLM-2026-08-23/ARCHITECTURE-SPINE.md:181` -- naming, digest, JSON, error, and terminal wire conventions; contract seed is at lines 189-202 and mandated layout at 215-230.
- `_bmad-output/planning-artifacts/epics.md:229` -- Story 1.1 requirements and acceptance criteria; exact toolchain pins begin at line 239.
- `src/epub-html/tests/test_convert.py:1` -- existing stdlib `unittest`, synthetic-fixture, subprocess, and repeatability patterns; reuse conventions only, never imports or placement.
- `src/epub-html/scripts/convert.py:715` -- read-only evidence for caught CLI boundaries and sorted JSON; the new canonical format remains kernel-owned.

## Tasks & Acceptance

**Execution:**
- [x] `src/i18n-pipeline/pyproject.toml`, `.python-version`, and `uv.lock` -- create the src-layout package, exact Python/dependency/tool pins, build metadata, and locked development test command; enforce uv 0.11.19 and commit the generated cross-platform lockfile.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/kernel/{errors,identity,canonical,lifecycle}.py` -- implement typed IDs/digests, recursive hostile-JSON rejection, canonical serialization, actionable errors, and the complete legal unit-transition table.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/kernel/{contracts,compatibility,boundary}.py` -- define the single public strict/frozen contract family, accepted-version checks, source-text mismatch guard, and exception-safe workflow-boundary validation.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/kernel/__init__.py` and `src/librarianlm_i18n/__init__.py` -- expose the authoritative contract surface without workflow-local alternatives.
- [x] `src/i18n-pipeline/tests/contracts/` -- add inventory, identity, hostile-input, canonical-byte, transition-table, status-independence, compatibility, and boundary short-circuit tests using immutable fixtures.

**Acceptance Criteria:**
- Given a clean checkout, when `uv sync --locked --python 3.14.4` runs under uv 0.11.19, then the exact pinned environment installs from `uv.lock` and all i18n files remain under `src/i18n-pipeline`.
- Given the kernel public API, when schemas are inspected, then it exposes Unit Manifest/Record, Inline Binding Map, Context Bundle, Projection Map, Model Request/Response, provenance objects, Component Identity, required reports, compatibility metadata, typed identities, lifecycle, and five independent statuses from one package.
- Given identical valid content, when serialized repeatedly, then bytes are identical and satisfy every canonical JSON rule while operational metadata is structurally excluded.
- Given each invalid matrix input or incompatible/missing/stale artifact, when the boundary validates it, then feature logic is not called and a complete stable actionable error is returned without an exception escaping.
- Given every possible unit-state edge, when transition validation runs, then only declared happy/recovery/typed-failure edges pass and committed/failed states remain terminal.

## Spec Change Log

## Design Notes

Pydantic's JSON validation accepts duplicate keys, so `boundary` must inspect raw JSON pairs before constructing models. `frozen=True` is shallow: public collections use tuples/frozen nested models, and canonical serialization accepts only the deliberately normalized JSON domain. Do not invent status coupling or a richer lifecycle than the architecture defines.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` -- expected: lock remains unchanged and exact runtime/test dependencies install.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` -- expected: all contract and boundary tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.kernel"` -- expected: authoritative public package imports successfully.

## Suggested Review Order

**Authoritative contract surface**

- Start with the single public kernel API consumed by every later workflow.
  [`kernel/__init__.py:19`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/__init__.py#L19)

**Domain invariants**

- Manifest validation enforces deterministic order, uniqueness, and cross-reference integrity.
  [`contracts.py:378`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L378)

- Unit records bind eligibility reasons, lifecycle state, and immutable provenance references.
  [`contracts.py:114`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L114)

- Context bundles preserve typed roles and canonical source ordering.
  [`contracts.py:197`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L197)

- Protected-token rendering implements the architecture's exact ASCII binding contract.
  [`identity.py:85`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/identity.py#L85)

**Boundary safety and deterministic bytes**

- Boundary validation rejects hostile or incompatible artifacts before feature execution.
  [`boundary.py:71`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/boundary.py#L71)

- Strict JSON parsing detects ambiguity before Pydantic can normalize it away.
  [`canonical.py:42`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/canonical.py#L42)

- Lifecycle validation centralizes monotonic transitions and typed terminal failure.
  [`lifecycle.py:61`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/lifecycle.py#L61)

- Compatibility checks bind contract identity before accepting schema versions.
  [`compatibility.py:17`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/compatibility.py#L17)

**Verification and reproducibility**

- Contract tests cover hostile inputs, invariants, lifecycle edges, and public inventory.
  [`test_kernel.py:93`](../../src/i18n-pipeline/tests/contracts/test_kernel.py#L93)

- Project metadata enforces the exact Python, uv, Pydantic, and lxml toolchain.
  [`pyproject.toml:1`](../../src/i18n-pipeline/pyproject.toml#L1)
