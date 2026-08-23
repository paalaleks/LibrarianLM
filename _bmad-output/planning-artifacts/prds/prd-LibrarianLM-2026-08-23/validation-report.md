# Validation Report — Literary Translation Skill Workflow Suite

- **PRD:** `_bmad-output/planning-artifacts/prds/prd-LibrarianLM-2026-08-23/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-08-23T08:55:00+02:00
- **Grade:** Poor

## Overall verdict

The PRD has a real product thesis, named trade-offs, and integrity invariants that architecture can use as a spine: structure stays independent of generated language, extra generation hits weak units only, and fluent output is never publication readiness. It is **not ready for development of the MVP as a buildable product**. `status: final` overclaims planning completeness while the Pilot Profile, Baseline Method, language pair, evaluation pass/fail, neighbor-context policy, required editorial inputs, and review-surface sufficiency remain unfrozen.

Adversarial and verification-gap reviews agree and add three development-blocking product holes the rubric only partially named: there is no operable copyright/provider transfer policy, Machine Final “plain value” vs HTML emphasis/placeholders is unresolved, and SM-3 / editor protocol / evaluation circularity cannot be observed. Integrity work (dummy round-trip, manifests, honest failure) can start; generation, provider calls, and usefulness measurement cannot.

## Dimension verdicts
- Decision-readiness — adequate
- Substance over theater — strong
- Strategic coherence — strong
- Done-ness clarity — thin
- Scope honesty — thin
- Downstream usability — adequate
- Shape fit — adequate

## Findings by severity

### Critical (8 unique themes)

**[Done-ness]** — Evaluation and routing have no testable pass/fail (§4.3 FR-10–FR-11, §6)
No hard-rule catalog, score scale, or gate definition while the contract forbids fixing thresholds.
Fix: Require a versioned Translation Method freeze (hard-rule categories, scales, routing, composition, stop rules) before FR-10–FR-14 are implementable.

**[Scope honesty]** — `final` with a blocker-density backlog (frontmatter, §12, §13, FR-26)
Unfrozen: Pilot Profile, Baseline Method, language pair, neighbor context, translation-specific governance, review-surface sufficiency, SM-3 target.
Fix: Set status to draft/gated; add a Development Readiness split so FR-8–FR-15 and provider transfer are not implied go-build.

**[Adversarial]** — Certification-gated Pilot Profile is treated as a build contract (§0, FR-26, §8.1)
FR-26 binds certification, not coding start; language pair is chosen “during implementation planning.”
Fix: Make an approved Pilot Profile a start-of-implementation gate. Until it exists, only the deterministic dummy loop (FR-17) is in scope.

**[Adversarial]** — No operable copyright/provider transfer policy (NFR-9 vs FR-26, §10)
Inherited “until defined” policy collides with “approved before any transfer.” Literary MVP is copyrighted books sent to multiple models.
Fix: Translation-specific data-handling FR approved with the Pilot Profile before any model call: providers, no-train/retention, corpus licenses, prompt-context bounds, logging, destruction.

**[Adversarial]** — Machine Final purity vs HTML reassembly has no markup contract (glossary, FR-14, FR-16, FR-18)
Plain-value finals cannot carry moved emphasis/placeholders; HTML fragments are not “only the target-language value.”
Fix: Specify payload type (plain text + annotation map, or constrained fragment + tokens assembly rebinds). Models never emit document IDs or structural wrappers.

**[Verification-gap]** — SM-3 has a 30% target without a measurement system (§9, FR-27, §13)
Missing baseline identity, n, clocks, critical-residual definition, uncertainty, owner.
Fix: Freeze Baseline Method card and protocol; treat 30% as a hypothesis that can fail a dry run — not an implementation acceptance number.

**[Verification-gap]** — Human-editor protocol is unspecified (UJ-2, FR-22, FR-27, SM-3, SM-6)
No qualification, blinding, magnitude formula, or severity rubric.
Fix: Publish editor protocol as a release-qualification artifact alongside the Pilot Profile.

**[Verification-gap]** — Evaluation circularity: model scores stand in for literary done (FR-8/10/11/13/14 vs SM-C2)
The only automated observers of faithfulness/naturalness are model evaluators that SM-C2 forbids treating as quality.
Fix: Human-rated gold subset; scores remain routing telemetry; forbid evaluator averages as ship evidence.

### High (development blockers)

**[Decision-readiness]** — Implementation start vs certification is fudged (§0, FR-26, frontmatter)
Fix: Explicit workstreams that may start on the generic contract vs what is blocked.

**[Decision-readiness]** — Neighbor-context policy is open under a required FR (§12 Q1, FR-9)
Fix: Freeze a default (source-only neighbors until committed targets exist; never mix in-flight targets) or mark FR-8–FR-12 blocked.

**[Done-ness]** — FR-8 states literary quality as a system duty
Fix: Bound FR-8 to produced artifacts; move quality to evaluator checklists / human residual-error measurement.

**[Done-ness]** — Supported content is a tautology (FR-4, FR-17, FR-26)
Fix: Minimum included set for MVP, or empty matrix = no generation.

**[Done-ness]** — Required vs optional editorial inputs unnamed (FR-6)
Fix: Name blocking vs recorded-optional for Terminology Sheet, Style Sheet, locked terms, confirmation.

**[Scope honesty]** — Review MVP rests on unvalidated “existing surfaces” (§8.2, FR-21–FR-22)
Fix: Name surfaces and minimum inspect/edit/export operations, or a files-plus-checklist procedure that still captures FR-27.

**[Scope honesty]** — Authorization is a non-user, not a requirement (§2.2 vs §5.3)
Fix: Translation Run may start only under authorization for that Canonical Source HTML.

**[Downstream usability]** — Five outcomes vs many Skill Workflows (§1.1 vs §4)
Fix: Glossary inventory of invocable outcomes vs substeps.

**[Adversarial]** — “Required Source Unit” undefined (SM-1, FR-4, FR-15)
Fix: required / optional / excluded / unsupported states with terminal effects on Draft eligibility.

**[Adversarial]** — Failed Units have no resolution path (FR-15, FR-21, FR-3)
Fix: Retry bounds, diagnostic artifacts, whether a new run is the only fix, editor-salvage without minting a Machine Final.

**[Adversarial]** — Skill/artifact contracts promised then refused (FR-1, FR-2, §6, §11)
Fix: MVP skill inventory and field-level information contracts (not storage layout).

**[Adversarial]** — Pre-run editorial confirmation is an undesigned human gate (FR-6, FR-3)
Fix: Prepare-Translation terminal state with required vs optional inputs and the artifact the operator signs.

**[Verification-gap]** — Language-pair/corpus freeze too late (FR-26, §8.1)
Fix: Freeze pair, corpus list, include/exclude matrix before generation and detectors.

**[Verification-gap]** — Provider, recovery, and cost unbounded (FR-8, FR-12, NFR-11)
Fix: Per-unit and per-run caps before any live provider call.

**[Verification-gap]** — Passing/weak/compliant unobservable without method freeze
Fix: Pilot stub Translation Method as test fixture.

**[Verification-gap]** — Data-governance inheritance untestable (NFR-9)
Fix: Cite the runtime policy artifact or make translation-specific policy a Pilot Profile blocker.

### Medium (22 across reviewers)
Plus findings on: Pilot sizing, missing `[NOTE FOR PM]`, thesis metric as assumption, emphasis-rule conflict, unnamed review quantities, accessibility pointer, skill packaging, vendor-independence used to skip method freeze, glossary drift, UX without extractable surface, reader chrome inventory, residual-language vs code-switching, overclaimed LLM reproducibility, undefined HTML class, FR-23 vacuous completeness, safe composition bypass, incomplete §12 stop-list, incomparable SM-5/SM-6 dictionaries. Full text in reviewer files.

### Low (6)
Plus: undefined “actionable” errors; §8.2 assumption tag lacks inline sentence; status vs prior rubric disagreement; counter-metrics have no owner; NFR-2/NFR-10 lack resume thresholds; FR-1 weakly observable without per-skill contracts.

## Mechanical notes
- Assumptions Index: five index rows and five inline tags; §8.2 tag lacks the assumption sentence.
- IDs FR-1–FR-27, UJ-1–UJ-3, SM-1–SM-6, SM-C1–C3, NFR-1–NFR-11 are contiguous.
- Glossary drift: Reader Artifact, five quality states, hard rules, content class, role titles unused as entries; rescue rate vs Recovery yield.
- Zero `[NOTE FOR PM]` callouts.
- Required chain-top sections are present.

## Reviewer files
- `review-rubric.md`
- `review-adversarial-general.md`
- `review-verification-gap.md`
