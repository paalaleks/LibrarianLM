# Validation Feedback Digest — PRD Update Input

## Overall verdict

- **Grade:** Poor.
- **Readiness:** The PRD is not ready to develop as a buildable MVP. Its `status: final` overstates readiness.
- **What may proceed:** deterministic integrity work in isolation (identity, manifests, dummy assembly and validation).
- **What is blocked:** generation, provider transfer, evaluation/routing, review measurement, and usefulness claims, pending frozen product contracts.

## Critical decision gaps

| PRD location | Gap | Proposed PRD-level fix |
|---|---|---|
| §4.3 FR-10–FR-14; §6 | No hard-rule categories, score scale, routing/commit gates, or recovery stop rules; “weak,” “passing,” and “compliant” are untestable. | Require a versioned Translation Method freeze before FR-10–FR-15; list rule categories in the PRD and put values/configuration in the method artifact. |
| Frontmatter; §0; §12–§13; FR-26 | Marked final although Pilot Profile, Baseline Method, pair/corpus, context policy, governance, review surface, and SM-3 are unresolved. | Change to `draft` or `gated`; add Development Readiness that separates allowed deterministic work from blocked work. |
| §0; §8.1; FR-26 | Pilot Profile is only a certification gate despite determining implementation. | Make approved Pilot Profile a start-of-generation implementation gate; limit pre-profile work to deterministic dummy loop/contracts. |
| NFR-9; FR-26; §10 | No operable copyright/provider transfer rule for copyrighted literary source. | Add translation-specific data-handling FR: eligible providers, no-training/retention, licenses, context bounds, logging/destruction; approve before first model call. |
| Glossary; FR-14; FR-16; FR-18 | Machine Final “target value only” conflicts with moved emphasis/placeholders and HTML reassembly. | Choose payload: plain text plus annotation map, or constrained fragment plus token rebinding; prohibit model-emitted IDs/structural wrappers. |
| §9; FR-27; §13 SM-3 | 30% edit-time target has no protocol, baseline, owner, sample, clock, or uncertainty. | Freeze Baseline Method card and dry-run protocol; treat 30% as a falsifiable release hypothesis, not implementation acceptance. |
| UJ-2; FR-22/FR-27; SM-3/SM-6 | Editor qualification, blinding, severity, edit magnitude, and assignment protocol are absent. | Create required editor-protocol artifact alongside Pilot Profile. |
| FR-8/FR-10/FR-11/FR-13/FR-14; SM-C2 | Model evaluation effectively stands in for literary quality. | Add blinded human-rated gold subset; scores remain routing telemetry only and cannot support ship evidence. |

## High development blockers

- **Neighbor context unresolved:** §12 Q1, FR-9, FR-24, NFR-3. Freeze window, source-versus-target, batching, and failed-predecessor behavior before generation.
- **Language pair, corpus, and content matrix too late:** §0, §8.1, FR-26, FR-17/FR-19, NFR-6. Freeze pair/script/region, licensed corpus, include/exclude classes, and detector tolerances before detector, generation, or editor-protocol work.
- **Unbounded live model work:** §6, FR-8, FR-12, NFR-7/NFR-11, FR-26. Set per-unit/run candidate, recovery, token, time, and cost caps as preconditions.
- **Required Source Unit undefined:** Glossary, FR-4/FR-8/FR-15/FR-18, SM-1. Define required, optional, excluded, and unsupported states with their terminal effects on draft eligibility.
- **Failure lifecycle absent:** FR-15, FR-21, FR-3, SM-3/SM-C3. Specify retry limits, diagnostics, new-run rule, and whether editor salvage is possible without minting Machine Final.
- **Review capability unspecified:** §8.2, FR-21–FR-23, addendum §3. Name the surface or an explicit files/CLI interchange and operations for provenance, edit, severity, book finding, and export.
- **Skill/artifact contracts missing:** §1.1, FR-1/FR-2, §6, §11. Add invocable five-outcome inventory/subworkflow table and minimum information contracts without prescribing storage/provider/prompt.
- **Pre-run editorial gate underdesigned:** FR-6, FR-3. Make Prepare-Translation an explicit terminal state; identify required versus optional terminology/style inputs and signed artifact.
- **Authorization only a non-user statement:** §2.2 versus §5.3. Add authenticated, authorized-run and provider-transfer preconditions.
- **FR-8 overpromises literary quality:** Constrain it to produced artifacts and malformed/non-success behavior; place quality judgment in evaluator/human protocol.
- **Supported content tautological:** FR-4/FR-17/FR-26. Establish a minimum included matrix or state that an empty matrix permits no generation.

## Medium and low themes

- **Medium (22 across reviewers):** observability and definition gaps: emphasis mapping, residual-language/code-switch policy, byte-equivalence canonicalization, supported-content classes, safe composition, review-record fields, metric dictionaries, Reader Artifact accessibility reference, reader-chrome projections, LLM reproducibility, and incomplete stop-list in §12.
- **Low (6):** undefined “actionable” errors; missing inline wording for §8.2 assumption; counter-metric ownership; resume/log thresholds; weak per-skill observability; status inconsistency.

## Mechanical/editorial notes

- IDs are contiguous and required sections exist.
- Five assumption tags/index entries match, but §8.2 contains only a bare tag rather than the assumption sentence.
- Glossary drift: undefined Reader Artifact, five quality states, hard rules, content class, role titles; “rescue rate” conflicts with “Recovery yield.”
- No `[NOTE FOR PM]` callouts despite material decision gates.
- These are mostly product/decision gaps; mechanical issues are secondary and should be cleaned up while reopening the PRD.

## Reviewed source files

- `validation-report.md`
- `review-rubric.md`
- `review-adversarial-general.md`
- `review-verification-gap.md`
