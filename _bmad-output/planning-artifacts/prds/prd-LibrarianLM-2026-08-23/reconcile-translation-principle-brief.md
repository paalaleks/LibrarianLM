# Input Reconciliation: `translation-principle-brief.md`

## Inputs Compared

- Source: `docs/brief-i18n/translation-principle-brief.md`
- Product requirements: `prd.md`
- Downstream design context: `addendum.md`

## Reconciliation Verdict

The PRD preserves the source's central product stance well: literary translation is an automatic but inspectable sequence of skill-based workflows; literal and idiomatic proposals are separated from evaluation; scores route effort rather than certify quality; recovery is local; structure and provenance are first-class; human editing follows the run; and completion, compliance, review, and publication readiness are distinct. The addendum also correctly keeps current workflow packaging and technical mechanisms revisable.

Five source ideas remain materially underrepresented or ambiguous. None overturns the product direction, but all affect whether a conforming implementation would preserve the source's literary and epistemic intent.

## Material Gaps

### 1. Underrepresented: the two initial renderings lack a sufficiently explicit qualitative contract

**Source idea:** The Literal Anchor is deliberately close to source wording and order, even when stiff. The Idiomatic Candidate must carry the same information, register, and tone in natural target-language prose while refusing calque and translationese. The productive tension between meaning and naturalness is the point of generating both.

**Current representation:** FR-8 requires both outputs and bars the Literal Anchor from direct commitment. FR-10 evaluates faithfulness and naturalness. The glossary describes the Literal Anchor as faithfulness-oriented and the Idiomatic Candidate as natural.

**Gap:** A workflow could technically comply while producing two loosely differentiated paraphrases. Neither the PRD nor addendum requires the Literal Anchor to preserve wording/order as an evaluator's mirror, or the idiomatic proposal to preserve information, register, and tone while actively avoiding calque/translationese. Those are not merely prompt details; they define the distinct jobs of the two artifacts.

**Recommended reconciliation:** Strengthen FR-8's observable consequences or the glossary contracts so the Literal Anchor and Idiomatic Candidate have distinct, testable qualitative purposes. Keep exact prompts and scoring mechanisms in architecture.

### 2. Underrepresented: rescued commitment does not explicitly deliberate over the full candidate set against the triggering critique

**Source idea:** Passing text normally passes through; rescued text earns a different commitment discipline. The assembler weighs the full candidate set against the critique that triggered recovery and may compose a final rather than merely pick one. Any correction is attributable, and taste alone is not grounds to rewrite a passing unit.

**Current representation:** FR-11 protects passing candidates from stylistic regeneration. FR-12 requires recovery to target the recorded weakness. FR-13 requires newly generated, corrected, or composed text to pass evaluation. FR-14 requires an evaluated value and selection rationale.

**Gap:** FR-14 can be satisfied by choosing any evaluated candidate with a generic rationale; it does not require the rescued commitment to consider the original proposals, Recovery Candidates, and triggering critique together. The source's asymmetric discipline—pass through strong units, deliberate over contested ones—is therefore only partly encoded. FR-11's wording also reads as absolute pass-through, while the source permits correction of an outright error or obvious calque, provided this is not taste-driven silent rewriting.

**Recommended reconciliation:** Clarify that rescued commitment evaluates the full attributed candidate set against the triggering critique and records why the committed value resolves it. Clarify the narrow error/calque exception for a previously passing unit and require it to re-enter the evaluation route, preserving FR-13.

### 3. Omitted: rationale and telemetry must remain outside the translated value

**Source idea:** Rationale and telemetry travel beside the text, never inside it. Pipeline labels, score chatter, or untranslated source leakage in a final are method failures even when the prose otherwise reads well.

**Current representation:** FR-14 retains rationale, FR-18 checks residual source-language content within declared limits, and FR-19 emits reports. The Unit Manifest is described as durable machine truth.

**Gap:** No requirement explicitly separates the Machine Final value from provenance, rationale, critiques, or scores. A conforming artifact schema could embed workflow commentary inside the translated text and still appear to satisfy attribution requirements. Residual-language checking covers only one of the named contamination modes and is qualified by declared limits.

**Recommended reconciliation:** Add an explicit Machine Final purity requirement: generated target text is stored separately from provenance/telemetry; pipeline labels, critiques, score commentary, or unauthorized source leakage in a final produce a validation finding or Failed Unit.

### 4. Distorted or ambiguous: structural preservation does not capture the special treatment of translatable inline emphasis and verse

**Source idea:** Block identity, order, inline emphasis, verse lines, footnotes, and related scaffolding carry meaning. Structural tokens may not vanish or be invented. At the same time, emphasis placement may move when target-language syntax requires it because placement can itself be a translation judgment.

**Current representation:** FR-4 names verse and footnotes when supported; FR-16 preserves order, identifiers, anchors, footnotes, and non-translatable content; FR-17 checks structure and protected inline placeholders. The addendum delegates placeholder representation and segmentation for poetry and inline markup.

**Gap:** The product contract neither explicitly protects verse-line identity and inline emphasis marks nor states that emphasis may be repositioned without being deleted or invented. "Replace only mapped book-owned values" plus placeholder preservation could be interpreted as freezing inline placement, which would distort the source principle; a looser implementation could instead drop or duplicate meaningful inline structure.

**Recommended reconciliation:** Define the invariant at product level: semantic structural tokens and verse-line identities survive one-for-one, while approved translatable inline marks may move within their owning Source Unit when the target language requires it. Leave locator and placeholder mechanics to architecture.

### 5. Underrepresented: language-specific literary knowledge must remain frozen configuration, not orchestration folklore

**Source idea:** Tense, address forms, register, recurring imagery, and other language-specific literary knowledge belong in the frozen terminology/style inputs and method configuration. They must not be hard-coded into orchestration. This is what makes the stance portable across target languages and experiments.

**Current representation:** FR-6 and FR-7 freeze editorial guidance and the Translation Method; the glossary names tense, address, register, and imagery. The general guardrail says the product contract must not fix a provider, prompt, threshold, schema, or storage mechanism.

**Gap:** The portability constraint is inferable but not explicit. Nothing prohibits a Skill Workflow implementation from embedding target-language literary rules in orchestration code, reducing comparability and making the method appear parameterized when it is not.

**Recommended reconciliation:** Add a guardrail or consequence requiring language- and locale-specific literary rules to be attributable frozen inputs or versioned method configuration, rather than undeclared orchestration behavior.

## Source Ideas Adequately Preserved

- The product output is explicitly a suite of composable, versioned Skill Workflows with declared contracts, rather than one opaque command.
- Propose, evaluate/route, recover, and commit remain separate attributed jobs; the workflow trajectory is controlled outside the model.
- Scores are routing telemetry, not evidence of literary quality or publication readiness.
- Recovery is conditional and local; passing units do not receive gratuitous alternatives, and a second full-book recovery translation is a non-goal.
- The Literal Anchor cannot become a Machine Final.
- Newly generated, corrected, or composed text cannot bypass evaluation.
- Per-unit history, rationale, run configuration, and later Human Edits remain attributable; Machine Finals remain immutable.
- Model generation does not reconstruct HTML; deterministic workflows own placement, completeness, and structural validation.
- Locked terminology is independently checkable and remains distinct from scored evaluation, while preferred/advisory classes remain distinguishable.
- Source, terminology/style inputs, and method configuration are frozen for a run; materially changed inputs create a new run.
- The automatic trajectory has no intermediate human approval gates; qualified human review begins after an attributable draft exists.
- Human edit time, magnitude, and issue severity are treated as the meaningful usefulness signal; model scores and completion rate are explicit counter-metrics.
- Honest incomplete and failed states prevent fluent output or successful execution from masquerading as compliance or readiness.
- The surrounding product depends on stable honesty invariants rather than today's stages, providers, prompts, thresholds, schemas, or packaging.

## Suggested Priority

1. Machine Final purity and metadata separation (Gap 3), because contamination can invalidate both the readable draft and provenance contract.
2. Distinct qualitative contracts for Literal Anchors and Idiomatic Candidates (Gap 1), because they are foundational to the evaluation method.
3. Rescued commitment discipline (Gap 2), because it preserves the method's deliberate asymmetry and auditability.
4. Inline emphasis and verse structural semantics (Gap 4), because generic structural preservation is insufficient for literary content.
5. Explicit parameterization of language-specific literary knowledge (Gap 5), because it protects portability and experimental comparability.
