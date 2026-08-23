# Updated Input Reconciliation: `translation-principle-brief.md`

## Inputs Compared

- Source: `docs/brief-i18n/translation-principle-brief.md`
- Updated product requirements: `prd.md`
- Updated downstream design context: `addendum.md`

## Reconciliation Verdict

The update preserves the source principle and materially improves its enforceability. The new readiness gates do not fossilize the method: they require the Pilot Profile, Provider Policy, Translation Method, Context Policy, and human-evaluation protocol to be frozen before the corresponding work begins, while the generic Skill Workflow contracts remain independent of providers, prompts, thresholds, schemas, and storage. The invocable skill boundaries also preserve the source's automatic propose → evaluate → recover → commit trajectory through explicit artifact handoffs rather than inserting human taste gates into the run.

The earlier reconciliation findings are substantially closed. FR-8 now distinguishes the qualitative jobs of Literal Anchors and Idiomatic Candidates; FR-14 requires rescued commitment to weigh the full eligible candidate set against the triggering critique; Machine Final content is separated from scores, critiques, rationale, provenance, and source-owned markup; FR-16 protects inline emphasis and verse structure while permitting mapped emphasis movement; and FR-6 explicitly keeps language-specific literary guidance in frozen editorial or method configuration.

Three material ambiguities remain. They do not change the product direction, but a conforming implementation could still violate the source's routing, pass-through, or honesty discipline unless they are resolved.

## Material Gaps

### 1. Ambiguous evaluator subject: the Literal Anchor can still be treated as a routed candidate

**Source idea:** The evaluator judges the Idiomatic Candidate for faithfulness and naturalness while using the Literal Anchor as a mirror that exposes drift. The Literal Anchor is deliberately stiff and is never a selectable final; scoring its naturalness as though it were a competing candidate would collapse the intended distinction and could route every unit to recovery.

**Current representation:** FR-8 gives the two artifacts distinct qualitative purposes and makes the Literal Anchor ineligible for direct commitment. FR-10 nevertheless requires the evaluation workflow to assess “each eligible candidate,” without defining whether the Literal Anchor is eligible or whether it participates in the routing gate. FR-11 then routes based on whether candidates satisfy the frozen gates.

**Gap:** A technically conforming implementation could evaluate the Literal Anchor on the same naturalness scale, treat its expected stiffness as weakness, and route recovery for the wrong reason. The update fixes the artifact definitions but not the evaluator binding between them.

**Recommended reconciliation:** State that routing and commitment gates apply to commitment-eligible Idiomatic and Recovery Candidates. The Literal Anchor is evaluation context and a faithfulness reference, not a naturalness-scored or routable candidate. Its own malformed or missing state may fail proposal generation, but its deliberate literalness must not trigger recovery.

### 2. Pass-through is protected from regeneration but not bound verbatim to the Machine Final

**Source idea:** When the Idiomatic Candidate clears the gate, it passes through unchanged. The commitment stage must not silently rewrite it for taste. If an outright error or obvious calque is discovered later, corrected text becomes newly composed text and must re-enter evaluation with attributable history.

**Current representation:** FR-11 says gate-satisfying candidates pass through unchanged and are not regenerated for stylistic preference. FR-13 requires newly generated, corrected, or composed text to pass evaluation. FR-14 generically requires commitment to “select one evaluated target-language value” and retain a rationale.

**Gap:** FR-14 does not explicitly bind a passing unit's Machine Final to the exact gated Idiomatic Candidate. A commitment implementation could add another evaluated alternative or choose a different evaluated value without calling that regeneration, weakening the source's central “leave good text alone” discipline while still satisfying the current words.

**Recommended reconciliation:** Require a non-recovered unit's Machine Final text and Inline Binding Map to equal the gated Idiomatic Candidate verbatim, with a pass-through rationale. Any proposed correction or alternative after the pass decision must change the unit's route, be attributable, and satisfy FR-13 before commitment.

### 3. Residual findings are reported, but a compliance-clean terminal claim is not explicitly forbidden

**Source idea:** The honesty contract forbids an invented success or compliance-clean claim when evidence is missing or residual findings remain. Processing completion, operational success, and compliance are different facts.

**Current representation:** The Run Status Vector separates processing, completeness, deterministic validation, human review, and publication readiness. FR-15 preserves Failed Units; FR-20 requires diagnostic artifacts and forbids treating successful execution as quality approval; NFR-4 makes provenance loss a run-level compliance failure. The readiness matrix blocks release certification only on unresolved **critical** compliance findings.

**Gap:** No requirement defines whether a deterministic-validation or compliance component may be labeled `passed`, `clean`, or equivalent while unresolved non-critical findings remain. Release certification may reasonably tolerate explicitly accepted lower-severity findings, but the source requires that such a result not be described as evidence-free or finding-free compliance.

**Recommended reconciliation:** Define terminal-state semantics: `clean/passed` requires complete required evidence and zero unresolved findings in the asserted scope; accepted or waived findings require a distinct qualified state that retains their severity, disposition, owner, and rationale. Keep release policy free to accept that qualified state if desired, but never collapse it into compliance-clean.

## Readiness-Gate Fidelity

- **Pilot Profile gate:** Faithful. It freezes the concrete language pair, corpus, content dispositions, residual-language tolerances, provider constraints, and budgets needed to make tests meaningful without hard-coding them into the portable method.
- **Provider Policy gate:** Faithful extension. The source does not prescribe provider governance, but freezing authorization and transfer bounds protects the principle that a run answers a fixed, attributable question.
- **Translation Method and Context Policy gates:** Faithful. Exact scales, thresholds, recovery ceilings, and context behavior remain project choices, yet must be versioned before routing or generation can be interpreted.
- **Prepare Package and confirmation gate:** Faithful. The operator confirms the frozen question once; the run then completes without intermediate human approval gates.
- **Baseline Method and Editor Evaluation Protocol gates:** Faithful. They operationalize the source's claim that qualified-human editing burden and residual severity—not model self-scores—are the honest usefulness evidence.
- **Development-readiness split:** Directionally faithful. It prevents live generation from starting before the question is frozen. Architecture should read “deterministic foundation” as contract and fixture work only where FR-26 still blocks detector implementation or content-class acceptance; the Pilot Profile remains authoritative for those activities.

## Skill-Contract and Method-Boundary Fidelity

- The five invocable Skill Workflows expose stable purposes, artifacts, preconditions, terminal states, version acceptance, retry safety, and actionable failure information.
- Artifact composition prevents consumers from depending on private prompts or provider mechanics and therefore preserves the source's claim that the method may evolve while the honesty envelope stays stable.
- The Orchestration Skill Workflow invokes the automatic trajectory after one authorized confirmation and does not add per-unit human gates.
- The Translation Method owns stage, scoring, routing, recovery, retry, ceiling, and terminal-state choices; the product contract owns immutability, attribution, structural integrity, explicit failure, and independent validation.
- The addendum appropriately delegates schemas, storage, adapters, prompts, threshold values, placeholder serialization, atomic writes, and resumption mechanisms to architecture.

## Machine Final, Human Evidence, and Failure Fidelity

- Machine Finals are immutable target-language values with Inline Binding Maps; source-owned markup, scores, critiques, rationale, and provenance remain separate metadata.
- Every committed value requires a recorded evaluation path, and composition cannot evade evaluation.
- Rescued commitment now considers the full eligible candidate set against the triggering critique and records why the selection resolves it.
- Literal Anchors cannot become Machine Finals; exhausted recovery yields a Failed Unit, not a fluent fallback.
- Required Failed Units block Translation Draft eligibility, literary review, and reviewed export while leaving diagnostic and provenance artifacts available.
- Human Edits remain separate from Machine Finals, and the Review Package captures edit time, edit magnitude, issue severity, and book-level findings.
- SM-3 makes the editing-burden claim falsifiable against a frozen baseline and prohibits improvement claims that increase critical residual errors; SM-C1 through SM-C3 prevent pass-through, model score, or completion-rate optimization from replacing human evidence.

## Source Ideas Adequately Preserved

- Translation is staged judgment rather than a single opaque answer.
- Literal and idiomatic renderings hold meaning and naturalness in productive tension.
- Scores route effort and do not certify literature or publication readiness.
- Recovery is conditional, local, critique-directed, bounded, and never a second full-book translation.
- Passing units are protected from stylistic regeneration; contested units earn deliberation over their attributed candidate history.
- Provenance is part of the translation and remains inspectable by stable Source Unit identity.
- Visible language is generated while deterministic workflows own source structure, placement, projection, and validation.
- Inline emphasis may move as a translation decision without losing or inventing its structural identity; verse, anchors, footnotes, and placeholders remain protected.
- Locked terminology is a binary independently validated rule, distinct from scored judgment; preferred and advisory guidance remain editorially distinguishable.
- Canonical source, terminology/style inputs, method, provider policy, context behavior, and pilot parameters are frozen and attributable for a run.
- Human judgment begins after the automatic run, and Machine Finals remain immutable under later editing.
- Processing, translation completeness, deterministic validation, human review, and publication readiness remain separate states.
- The surrounding product depends on the honesty envelope rather than the internal stage names or implementation mechanisms of today's method.

## Suggested Priority

1. Bind pass-through Machine Finals verbatim to their gated Idiomatic Candidates (Gap 2), because silent commitment-stage rewriting most directly violates the source's literary discipline.
2. Define the Literal Anchor as evaluator context rather than a routed candidate (Gap 1), because otherwise the expected stiffness of the anchor can corrupt routing behavior.
3. Define compliance terminal-state semantics for residual or waived findings (Gap 3), because explicit findings must never coexist with an unqualified clean claim.
