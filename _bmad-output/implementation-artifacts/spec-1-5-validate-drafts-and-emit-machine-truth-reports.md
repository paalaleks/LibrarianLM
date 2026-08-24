---
title: '1.5 Validate Drafts and Emit Machine-Truth Reports'
type: 'feature'
created: '2026-08-24'
status: 'done'
review_loop_iteration: 0
baseline_commit: '4e1ffe65a7d874c6fe841584676c6b21de9ec442'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Assembly produces a structurally faithful candidate, but no independent authority verifies its lineage, coverage, policy compliance, accessibility, or eligibility. Existing policy and report contracts also lack the structured locale, terminology, detector, component, and persisted-lineage data required for deterministic validation.

**Approach:** Add frozen validation controls and a read-only validation filter that inspects the source and candidate graph, emits stable actionable findings and canonical machine-truth reports, and creates an eligible Translation Draft only when every blocking control passes.

## Boundaries & Constraints

**Always:** Work only under `src/i18n-pipeline`; validate immutable artifacts by digest before feature checks; inspect source and candidate independently without mutation; compare only declared Required replacements and locale metadata changes; preserve exact Excluded content, structure, anchors, footnotes, projections, protected bindings, order, and accessibility semantics. Keep processing, completeness, compliance, review, publication, and draft eligibility independent. Emit deterministic reports for a readable validated graph, including blockers, detector evidence/limitations, component identity, inputs, counts, and next actions.

**Ask First:** Adding dependencies; changing canonical serialization or Story 1.2 storage; widening supported HTML/locale profiles; introducing probabilistic or external language detection; changing Story 1.4 token/placement rules; or weakening an existing compatibility, signature, or lineage gate.

**Never:** Repair or normalize candidate HTML during validation; mutate or publish a Unit Manifest successor; infer terminology from prose; accept free-form rules as executable controls; use timestamps, paths, attempts, or runtime order in content artifacts; equate successful processing or eligibility with human review/publication approval; call a live gateway; or emit an eligible draft after any unresolved blocker or nondeterminism.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean candidate | Fully linked source, manifest, maps, assembly evidence, frozen controls, and conforming HTML | Persist byte-stable Validation Report, Run Summary, and eligible Translation Draft; leave inputs unchanged | No blocking findings; review/publication remain unapproved |
| Content blocker | Readable graph with structural, binding, projection, terminology, residue, locale, directionality, or accessibility failure | Persist ordered findings and truthful reports but no eligible draft | Stable code, subject, rule, expected/observed, retryability, and next action |
| Invalid graph | Missing, tampered, stale, incompatible, or cross-wired artifact | Stop before document inspection | Typed actionable failure; publish no partial validation outputs |
| Repeat run | Identical frozen inputs and component versions | Produce byte-equivalent reports and draft reference | Explicit nondeterminism blocker suppresses eligibility |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py:153-193,305-345,398-418,667-673,769-832,846-912` -- extend frozen preparation controls, actionable findings, assembly lineage, validation/draft/result reports, and exact inventory/status invariants without coupling status dimensions.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/html_document.py:74-80` and `adapters/lxml_html_document.py:24-64,194-401` -- add secured read-only observations using existing parse, path, fingerprint, protected-topology, and lexical-repair rules; mutation methods remain assembly-only.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/residual_language.py` and `adapters/fixture_residual_language.py` -- define deterministic versioned evidence, tolerance/exemption, and limitation reporting for fixture mode.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py:37-163` -- retain persisted report/package/confirmation/component lineage and project only frozen canonical root locale/direction metadata needed by validation.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/validate.py` -- load and cross-check the complete graph; run structural, semantic, locale/directionality, accessibility, determinism, eligibility, and canonical publication logic without manifest mutation.
- `src/i18n-pipeline/src/librarianlm_i18n/{kernel,ports,adapters,workflows}/__init__.py` -- export the new strict contracts and public workflow seams consistently.
- `src/i18n-pipeline/tests/{contracts/test_kernel.py,test_prepare.py,test_assemble.py,test_validate.py}` -- reuse the real filesystem store and unittest fixture builders for contract, lineage, preservation, blocker, status, no-mutation, and byte-equivalence matrices.

## Tasks & Acceptance

**Execution:**
- [x] `kernel/contracts.py` and exports -- model structured validation controls, evidence, actionable findings, persisted assembly lineage, Translation Draft, Validation Report/Result, and Run Summary with strict cross-object invariants.
- [x] `ports/`, `adapters/`, and exports -- expose read-only HTML observations plus a deterministic fixture residual-language detector with declared limitations.
- [x] `workflows/prepare.py` and `workflows/assemble.py` -- freeze/bind validation controls, canonical locale metadata, component identity, and persisted artifact references without weakening prior preparation or assembly gates.
- [x] `workflows/validate.py` and exports -- implement fail-fast graph verification, independent controls, deterministic finding order/status calculation, report persistence, and blocker-gated draft eligibility.
- [x] `tests/` -- cover the complete matrix, hostile lineage, scoped locked terms, residual tolerances/exemptions, BCP-47/RTL/passage language, headings/landmarks/focus/anchors/footnotes, truthful status vectors, input immutability, and repeated canonical bytes.

**Acceptance Criteria:**
- Given a valid assembled graph, when Validation runs, then it reads every input without mutation and deterministically checks complete placement, preserved structure/content, semantic controls, locale/directionality, and accessibility.
- Given a readable graph with any blocker, when eligibility is calculated, then canonical reports retain ordered actionable evidence and independent statuses while no Translation Draft is emitted.
- Given a clean complete graph, when validation finishes, then the eligible Translation Draft, Validation Report, Assembly Report, and Run Summary bind exact inputs and component versions without implying review or publication approval.
- Given identical frozen inputs, when validation repeats, then canonical outputs are byte-equivalent; detected nondeterminism becomes a blocker rather than a hidden success.

## Spec Change Log

## Design Notes

Validation resolves the source location using its stored fingerprint and the candidate location using the frozen typed path, then compares an explicit allowlist: Required values and policy-declared root locale metadata may differ; structural nodes, source-owned attributes, Excluded values, IDs, references, bindings, and order may not. Protected candidate topology is reconstructed through persisted binding maps, with projected members normalized to canonical topology before comparison. Content failures still produce machine truth; trust/schema/lineage failures occur before inspection and publish nothing.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` from `src/i18n-pipeline` -- expected: no lockfile change.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` from `src/i18n-pipeline` -- expected: all existing and Story 1.5 tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.workflows; import librarianlm_i18n.ports; import librarianlm_i18n.adapters"` from `src/i18n-pipeline` -- expected: public surfaces import successfully.

## Suggested Review Order

**Validation authority**

- Start with fail-fast graph verification, deterministic probes, status calculation, and artifact publication.
  [`validate.py:38`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/validate.py#L38)

- Follow exact persisted lineage, signature, inventory, projection, and detector identity gates.
  [`validate.py:118`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/validate.py#L118)

- Inspect structural, semantic, locale, accessibility, projection, and residual-language controls.
  [`validate.py:163`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/validate.py#L163)

**Frozen contracts and handoffs**

- Review executable locale, terminology, residual-language, and accessibility controls frozen during preparation.
  [`contracts.py:395`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L395)

- Confirm reports enforce canonical evidence ordering, truthful counts, statuses, and eligibility relationships.
  [`contracts.py:934`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L934)

- Verify invalid validation-control scopes fail before confirmation and assembly.
  [`prepare.py:311`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py#L311)

- Trace persisted source, package, confirmation, signature, and component lineage from assembly.
  [`assemble.py:102`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py#L102)

**Read-only document evidence**

- Examine precise mutable-slot masking and immutable DOM/accessibility observations.
  [`lxml_html_document.py:181`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L181)

- Confirm assembly projects only frozen root language and direction metadata.
  [`lxml_html_document.py:290`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L290)

- Review fixture-only residual detection and its explicit limitation evidence.
  [`fixture_residual_language.py:12`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/fixture_residual_language.py#L12)

**Verification evidence**

- Begin with clean eligibility, input immutability, status independence, and byte-equivalent repeats.
  [`test_validate.py:225`](../../src/i18n-pipeline/tests/test_validate.py#L225)

- Finish with structural, accessibility, binding, projection, and excluded-content tampering.
  [`test_validate.py:243`](../../src/i18n-pipeline/tests/test_validate.py#L243)
