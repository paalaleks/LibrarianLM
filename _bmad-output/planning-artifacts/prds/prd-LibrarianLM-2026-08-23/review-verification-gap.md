# Verification-Gap Review — Literary Translation Skill Workflow Suite

- **Reviewed:** `prd.md` and `addendum.md`
- **Review type:** behavioral-specification verification gap
- **Run date:** 2026-08-23
- **Scope:** observable acceptance evidence for deterministic round trip, artifact bindings, provider authorization, Translation Method and Context Policy, eligibility/completeness, recovery and failure, artifact-first review, and success-metric measurement.

## Gate verdict

**Gated — not ready to sign off the deterministic foundation or begin live generation.** The PRD now has clear phase gates and closes the earlier high-level policy gaps: live work is correctly blocked on a Pilot Profile, Provider Policy, Translation Method, Context Policy, and Prepare Package; review measurement is blocked on the Editor Evaluation Protocol and Baseline Method. The five gaps below are narrower: each leaves a failure mode that can satisfy the written acceptance consequences, so the relevant gate would not reliably catch it. No physical schema is prescribed; the proposed guards are product-level information and acceptance contracts.

## Critical and high findings

### [High] The eligibility proof has no closed source universe, so SM-1 can pass after silently never selecting book-owned content

- **Location:** `prd.md` §4.2 FR-4 (lines 166–173); §4.8 FR-31 (lines 459–467); §9 SM-1 (line 547)
- **Missing evidence:** FR-31 classifies every **selected** content location. It does not require a deterministic inventory of every book-owned text-bearing location in Canonical Source HTML, nor an assertion that every inventory member is classified Required, Excluded, or Unsupported. A preparer can fail to select a paragraph, caption, or metadata projection; it will have no Source Unit and therefore cannot appear missing or duplicated in SM-1. FR-4's requirement to identify book-owned content does not state the observable coverage comparison needed to prove it happened.
- **Downstream consumer:** Prepare Translation and Assemble/Validate; the Translation Operator relying on `ready-for-confirmation`, and SM-1 release evidence.
- **Proposed guard:** Require Prepare Translation to emit a deterministic source-content inventory/count by content class and an eligibility-coverage finding for every inventory member. `ready-for-confirmation` must require zero unclassified book-owned locations; the Assembly and Validation Reports must reconcile inventory, Required, Excluded, Unsupported, and generated Source Unit counts. This remains independent of locator or manifest serialization.

### [High] Context determinism is asserted from inputs that do not determine committed target-neighbor text

- **Location:** `prd.md` FR-9 (lines 223–231); FR-30 (lines 451–457); NFR-3 (lines 473–476); SM-4 (line 553)
- **Missing evidence:** FR-30 says identical Run Snapshots and policy versions produce identical request context regardless of runtime scheduling, while the Context Policy may include committed target neighbors. A Run Snapshot does not freeze those neighbors before live generation; independently generated predecessor text can differ even under the same snapshot and method. An implementation can therefore meet the wording in a mocked test but cannot demonstrate the claimed property in a real resumed/parallel run, and may attribute model-output drift to scheduling.
- **Downstream consumer:** Run Translation request construction, reproducibility claims (FR-24/SM-4), and Compare Translation Runs.
- **Proposed guard:** Define the acceptance condition in terms of a fixed committed-prefix state (or require source-only context until a declared deterministic commit boundary). For the same Run Snapshot, Context Policy, and committed-prefix artifact identities, every scheduled execution must emit the same ordered context identities and payload digest; a missing/changed predecessor must yield the declared blocked/failed state. Report those identities/digests in provenance so the condition is observable without freezing provider output.

### [High] Provider authorization can be recorded without proving that the exact transfer was permitted at the time it occurred

- **Location:** `prd.md` Prepare Package definition (line 98); FR-28 (lines 433–440); NFR-7 and NFR-9 (lines 483–487)
- **Missing evidence:** The contract requires verification of operator authorization and source-content rights, and records an authorization record plus policy identity. It does not require the authorization evidence to state its scope (operator/action, source or corpus, provider/model, permitted unit/context bounds), validity interval, and authoritative decision. A stale or broad boolean record could be attached to a package while a different book, provider, or later transfer is sent; the required transfer log then proves that a transfer happened, not that it was permitted.
- **Downstream consumer:** The provider adapter before external transmission; compliance reviewers and any source-rights audit.
- **Proposed guard:** Require the Prepare Package authorization record and each transfer record to bind the exact source identity or approved corpus membership, operator, permitted action, Provider Policy/version, eligible provider/model, permitted context scope, authorization decision identity, and validity time. The pre-transfer check must emit a blocking denial finding when any binding is absent, expired, or mismatched; audit evidence must retain the matched authorization decision identity.

### [High] Retry and recovery have no observable exactly-once boundary for committed artifacts or external transfers

- **Location:** `prd.md` FR-1 (lines 131–139); FR-3 (lines 151–160); FR-12 (lines 258–266); FR-15 (lines 288–295); NFR-2 and NFR-11 (lines 473–493); `addendum.md` §1 (lines 8, 11, 15)
- **Missing evidence:** The PRD calls writes recoverable, asks each skill to declare retry safety, and forbids changing the Run Snapshot. It does not require evidence that an interruption between request, response validation, manifest update, and final commitment cannot create duplicate provider transfers, duplicate candidates, or competing Machine Finals for one attempt. A resumed run can preserve the same snapshot yet double-spend recovery budget, make Recovery yield incomparable, or create ambiguous provenance while still reaching a nominal terminal state.
- **Downstream consumer:** Run Translation/resumption, provider-cost budgets, Unit Manifest provenance, SM-5, and Compare Translation Runs.
- **Proposed guard:** Require every invocable workflow to declare whether a retry resumes, replays, or starts a new attempt, and require the Unit Manifest/Run Summary to expose stable attempt identity, request/response disposition, commitment disposition, and whether a transfer was reused or newly made. Acceptance evidence must inject interruption at each externally visible boundary and show either one committed outcome and one accounted transfer, or an explicit indeterminate/blocked state that requires operator action.

### [High] Editor-evaluation evidence does not bind recorded edits to a qualified, assigned reviewer and the exact evaluation arm

- **Location:** `prd.md` FR-22 (lines 370–378); FR-25 (lines 400–406); FR-27 (lines 423–431); SM-3 and SM-6 (lines 547–555)
- **Missing evidence:** FR-27 now names protocol ingredients and requires a dry run, but the Review Package contract only requires unit-level time, magnitude, and severity. It does not require each measurement record to identify the protocol/baseline arm, assigned qualified editor, timing boundary, reviewed artifact identity, and applicable severity/magnitude-rubric version. Consequently a report can list editor count, assignment method, and median time without a reproducible linkage from its input edits to the frozen protocol; SM-3's 30% result and FR-25 comparisons are not independently auditable.
- **Downstream consumer:** Review Translation, the Editor Evaluation Protocol dry run, SM-3 release qualification, SM-6, and Compare Translation Runs.
- **Proposed guard:** Make the evaluation-mode Review Package retain, for every measured review session, the reviewed Translation Draft/Run identity, editor qualification/assignment reference, protocol and rubric versions, comparison arm, clock start/stop or an equivalent reproducible duration record, exclusions, and the linked unit/book-level edit records. The FR-27 dry run must reconstruct the reported median, residual-error count, and exclusions solely from those artifacts; ordinary editorial exports can remain less instrumented.

## Medium findings

### [Medium] The deterministic round-trip gate does not say how a Content Class is represented by acceptance fixtures

- **Location:** `prd.md` FR-17 (lines 314–322); FR-26 (lines 412–421); `addendum.md` §1 (lines 7–10, 17)
- **Missing evidence:** FR-17 correctly blocks model stages until a Content Class passes dummy round trip, and FR-26 supplies a supported-content matrix. Neither requires each included class and its declared combinations (for example, verse with inline emphasis or tables with footnotes) to map to representative Canonical Source HTML fixtures and a retained proof result. One happy-path document could be used to approve an expansive class while the complex structural combinations that consume the binding map never run.
- **Downstream consumer:** Pilot qualification, deterministic foundation, and the model-stage eligibility gate.
- **Proposed guard:** Require the Pilot Profile or associated round-trip evidence to name representative fixture identities for every included class/declared structural combination and report pass/fail findings for selection, placement, bindings, projections, and repeated canonical output. The PRD need not prescribe fixture files or a DOM scheme.

### [Medium] Artifact version acceptance is specified, but binding the Manifest to the exact canonical source at Assembly entry is implicit

- **Location:** `prd.md` workflow inventory (lines 123–129); FR-2 (lines 141–149); FR-7 (lines 196–204); FR-16 (lines 301–312)
- **Missing evidence:** Assemble and Validate accepts Canonical Source HTML plus a completed Unit Manifest. The generic artifact contract carries a Run Snapshot identity and integrity digest, but the assembly entry condition never explicitly requires verification that the supplied source identity, manifest, and Run Snapshot are the same frozen preparation lineage. A caller can pair a valid completed manifest with a different canonical HTML whose locators coincidentally resolve, yielding a structurally plausible but wrongly sourced draft.
- **Downstream consumer:** Assemble and Validate Translation and provenance consumers of Translation Draft.
- **Proposed guard:** State that Assembly accepts inputs only when canonical-source identity/digest, Unit Manifest identity, and Run Snapshot identity form one verified lineage; otherwise it emits `assembly-failed` with the expected and observed identities. Include the verified lineage identities in the Assembly and Validation Reports.

### [Medium] Complete Translation Draft eligibility is not explicitly bound to a compliance-clean Validation Report at the success-artifact boundary

- **Location:** `prd.md` workflow inventory (lines 127–128); FR-18 (lines 324–334); FR-20 (lines 347–354); FR-21 (lines 360–368)
- **Missing evidence:** FR-18 says unresolved blocking errors prevent both compliance-clean status and Translation Draft eligibility, while the inventory lists Translation Draft as the Assemble skill's success artifact and FR-20 says it emits a draft “when complete.” The contract does not say whether a physically assembled but validation-failed HTML is named/stored as a Translation Draft, and FR-21 admits only a complete Translation Draft. That ambiguity can leak a failed candidate artifact into review or metrics despite the intended status separation.
- **Downstream consumer:** Review Translation entry gate, reviewed export, and release evidence.
- **Proposed guard:** Distinguish a non-eligible assembled candidate from a `Translation Draft`; only the latter may be emitted/accepted when the required-unit condition and a validation report with zero blocking errors both hold. Require Review Translation to verify that eligibility decision and validation-report identity before constructing a Review Package.

### [Medium] SM-5 and SM-6 have report requirements but no frozen metric dictionary to make compatible-run comparison falsifiable

- **Location:** `prd.md` FR-25 (lines 400–406); FR-27 (lines 423–431); SM-5 and SM-6 (lines 553–555)
- **Missing evidence:** The PRD names Recovery yield, stage outcome, Source Unit type, edit magnitude, and issue severity, but does not require the Translation Method or Editor Evaluation Protocol to define their numerator/denominator, category dictionary, aggregation, and missing-data treatment. Two valid reports can use different interpretations yet appear comparable, contrary to FR-25's purpose.
- **Downstream consumer:** Compare Translation Runs and SM-5/SM-6 reporting.
- **Proposed guard:** Require the frozen Translation Method and Editor Evaluation Protocol to carry versioned metric definitions, including inclusion/exclusion rules and category dictionaries. Compare Translation Runs must reject or label metrics non-comparable when those definitions differ, not merely when source/locale/editorial inputs differ.

## Low findings

### [Low] The five-component Run Status Vector lacks an acceptance truth table for legal terminal combinations

- **Location:** `prd.md` glossary (line 104); FR-3 (lines 153–160); FR-20 (lines 347–354); §6 (lines 495–504)
- **Missing evidence:** Separate states are well stated, but no contract shows which combinations are valid (for example, whether `processing-complete` plus `validation-failed` is allowed, and whether `human-review` can be `not-started` after a compliant draft). Consumers can invent contradictory status combinations while still emitting all five fields.
- **Downstream consumer:** Orchestration summary, Review Translation precondition, and dashboards/report readers.
- **Proposed guard:** Publish a product-level terminal-state compatibility table or validation rule for the Run Status Vector, with the allowed combinations and the artifact/event that changes each component.

### [Low] The destruction schedule in transfer provenance has no observable completion or exception outcome

- **Location:** `prd.md` FR-28 (lines 435–440); NFR-7 and NFR-9 (lines 483–487)
- **Missing evidence:** Every transfer records a destruction schedule, but there is no state or report for deletion confirmed, deletion pending, exception, or provider retention evidence unavailable. A scheduled date can remain forever without affecting the policy-compliance reading.
- **Downstream consumer:** Provider Policy audit and release compliance review.
- **Proposed guard:** Require Provider Policy compliance reporting to show each transfer's deletion/retention disposition or an explicit exception finding; unresolved required deletion evidence must remain visible to the applicable compliance gate.

## Summary

- **Critical:** 0
- **High:** 5
- **Medium:** 4
- **Low:** 2

The updated PRD is materially stronger than the prior validation report. Its phase gating is sound in intent, but the five high findings must be closed before the relevant readiness gates can be trusted as observable acceptance gates.
