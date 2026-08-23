---
title: Literary Translation Skill Workflow Suite
status: draft
development_readiness: gated
created: 2026-08-23
updated: 2026-08-23
---

# PRD: Literary Translation Skill Workflow Suite

## 0. Document Purpose

This PRD defines LibrarianLM's internal, composable Skill Workflows for producing and reviewing attributed literary-translation drafts. The MVP is artifact-first, preserves explicit failure, and cannot be release-certified until its Pilot Profile and Baseline Method are frozen. Technical mechanisms and standards notes live in `addendum.md`.

### 0.1 Development Readiness

`status` records the lifecycle of this document; `development_readiness` records what may be built safely. The current gate is **gated**.

| Workstream | Readiness | Entry gate |
| --- | --- | --- |
| Deterministic foundation | Ready | Contract scaffolding from FR-1 through FR-7 and the FR-16 through FR-20 dummy assembly/validation loop using synthetic fixtures |
| Live model generation and evaluation | Blocked | Approved Preparation Policy, Translation Method, Context Policy, and Prepare Package |
| Human review | Blocked | Complete Translation Draft and Review Package contract |
| Comparative and usefulness evaluation | Blocked | Completed comparable runs, Editor Evaluation Protocol, frozen Baseline Method, and Pilot Profile |
| MVP release certification | Blocked | All prior gates plus evidence for SM-1 through SM-6 and no unresolved critical compliance finding |

`[NOTE FOR PM: Approving this PRD authorizes deterministic-foundation work only. It does not authorize transfer of source content to a model provider or implementation of live generation.]`

## 1. Vision

LibrarianLM should translate books through skill-based workflows whose judgments remain visible. Instead of asking one model call to draft, judge, repair, and silently declare success, the Workflow Suite separates preparation, candidate generation, evaluation, recovery, assembly, validation, review, and comparison into composable Skill Workflows with declared inputs, outputs, and terminal states.

The product's core bet is that literary machine translation becomes more useful when additional generation is concentrated on weak units, document structure is preserved independently from generated language, and every committed result can be traced back to its source and evaluation history. The output is a complete attributed Translation Draft when all required units succeed, or an honestly incomplete Translation Run when they do not. Neither fluent output nor model confidence is represented as publication readiness.

The surrounding product depends on these guarantees, not on today's prompts, providers, thresholds, stage names, or schemas. Implementations may evolve experimentally while retaining immutability, traceability, deterministic placement, reproducibility, explicit failure, and independent validation.

### 1.1 Proposed Workflow Shape

The product contract permits different packaging, but the initial design should expose five clear workflow outcomes:

1. **Prepare Translation** — select source content, segment stable Source Units, create the Unit Manifest, prepare terminology and style guidance, and freeze the Run Snapshot.
2. **Run Translation** — generate contrasting proposals, evaluate and route them, recover weak units locally, and commit attributed Machine Finals.
3. **Assemble and Validate Translation** — place values deterministically, assemble the Translation Draft, validate its integrity, and emit reports.
4. **Review Translation** — inspect provenance, record Human Edits and book-level findings, and export reviewed content.
5. **Compare Translation Runs** — check compatibility and compare configuration, recovery, compliance, and editing burden.

These may be separate Skill Workflows or explicit subworkflows when a standalone boundary would add no independent value. In either case, every boundary obeys FR-1 through FR-3.

## 2. Target Users

### 2.1 Jobs To Be Done

- As a Translation Operator, I can configure and start a reproducible Translation Run without manually supervising each generation step.
- As a Literary Editor, I can inspect every Machine Final alongside its Source Unit, proposals, evaluation, recovery history, and rationale, then record my Human Edit without destroying provenance.
- As a Method Maintainer, I can change a Translation Method and compare runs without losing the exact configuration or mistaking incompatible runs for equivalent experiments.
- As a Product or Quality Reviewer, I can distinguish processing completion, deterministic compliance, human review, and publication readiness.
- As a Skill Maintainer, I can evolve one Skill Workflow without requiring every consumer to adopt its internal prompts, provider, or storage mechanics.

### 2.2 Non-Users in MVP

- Readers seeking an on-demand translation interface inside the Reader Artifact.
- Publishers seeking an autonomous publication-ready translation.
- Teams seeking a general-purpose localization management system for application chrome.
- Operators seeking to translate works that have not been confirmed as public domain.

### 2.3 Key User Journeys

- **UJ-1. Nora runs an attributed book translation.** Nora, a Translation Operator, supplies Canonical Source HTML, a Target Locale, a Terminology Sheet, and a Literary Style Sheet. She invokes the Orchestration Skill Workflow, reviews the frozen Run Snapshot, and starts the run. The suite prepares stable Source Units, proposes and evaluates candidates, routes only weak units to recovery, assembles successful Machine Finals, and validates the result. Nora receives a Translation Run with explicit status, reports, and either a complete Translation Draft or identified Failed Units; no fallback is promoted to hide incompleteness.
- **UJ-2. Elias edits without losing the machine record.** Elias, a qualified Literary Editor, opens a completed Translation Draft. For each Source Unit he can inspect the Machine Final and its provenance, record a Human Edit and an issue severity, and mark review state. He exports the edited rendition while the original Machine Final remains immutable for later analysis.
- **UJ-3. Mina compares method changes honestly.** Mina, a Method Maintainer, changes a Translation Method and starts a new Translation Run against the same Canonical Source HTML. The suite freezes the new Run Snapshot and reports configuration differences, Recovery yield, deterministic findings, and human edit burden so Mina can learn whether the change helped without conflating incompatible inputs.

## 3. Glossary

- **Workflow Suite** — The product defined by this PRD: a composable set of Skill Workflows for literary translation, validation, review, and comparison.
- **Reader Artifact** — The upstream self-contained HTML reading document whose book-owned content and structural behavior supply Canonical Source HTML.
- **Skill Workflow** — An independently invocable, versioned workflow with declared inputs, outputs, preconditions, failure behavior, and terminal states. A Skill Workflow may orchestrate deterministic tools and model calls.
- **Prepare Translation Skill** — Invocable Skill Workflow that produces a Prepare Package and is the only entry point that can make a Translation Run ready for confirmation.
- **Run Translation Skill** — Invocable Skill Workflow that generates, evaluates, routes, recovers, and commits unit-level language artifacts under frozen live-operation gates.
- **Assemble and Validate Translation Skill** — Invocable Skill Workflow that performs deterministic rebinding, assembly, and validation without generating document structure.
- **Review Translation Skill** — Invocable Skill Workflow that renders and updates a Review Package and produces reviewed export artifacts.
- **Compare Translation Runs Skill** — Invocable Skill Workflow that checks compatibility and compares run outcomes.
- **Orchestration Skill Workflow** — The Skill Workflow that freezes inputs, invokes the other Skill Workflows in order, and reports overall Translation Run status.
- **Canonical Source HTML** — Immutable EPUB-derived HTML that owns book content and structural identity for a Translation Run.
- **Target Locale** — The requested translation language expressed as a canonical BCP 47 language tag, including script or region when relevant.
- **Source Unit** — A stable, ordered, book-owned segment selected from Canonical Source HTML for translation.
- **Required Source Unit** — A supported Source Unit that must end in one Machine Final for a complete Translation Draft.
- **Excluded Source Unit** — Content intentionally outside translation scope and preserved unchanged without affecting Translation Draft completeness; content that cannot be preserved safely is Unsupported rather than Excluded.
- **Unsupported Source Unit** — Book-owned content that the approved Preparation Policy cannot prepare or reassemble safely; its presence blocks the Prepare Package unless the Preparation Policy explicitly excludes that content class.
- **Content Class** — A source-structure category with an explicit include, exclude, or unsupported disposition in the Preparation Policy.
- **Unit Manifest** — Durable machine truth that records every Source Unit, stable identity, placement, lifecycle state, and attributed decisions.
- **Terminology Sheet** — Frozen editorial guidance containing locked, preferred, or advisory terms and their applicable scope.
- **Literary Style Sheet** — Frozen editorial guidance for voice, register, tense, address, imagery, and related literary concerns.
- **Translation Method** — The versioned configuration of stages, prompts, providers, models, evaluation rules, routing rules, and recovery rules used by a Translation Run.
- **Hard Rule** — A binary Translation Method constraint whose violation cannot be offset by a model score; MVP categories cover source coverage, locked terminology, protected-placeholder integrity, target language or script, artifact validity, and prohibited additions.
- **Context Policy** — Frozen rules for source and target neighbors, window bounds, batching order, concurrency, truncation, and failed-predecessor behavior.
- **Preparation Policy** — Frozen operational rules for supported content classes, eligibility dispositions, and residual-language tolerances used by preparation and validation.
- **Pilot Profile** — A frozen release-qualification artifact defining the pilot language pair, representative public-domain corpus, applicable Preparation Policy, and qualification budgets.
- **Baseline Method** — The frozen single-pass comparison method used to measure whether the Workflow Suite reduces human editing burden.
- **Prepare Package** — Signed, immutable pre-run artifact containing the Run Snapshot, Unit Manifest, confirmed Terminology Sheet, Literary Style Sheet, Preparation Policy identity, Translation Method identity, and Context Policy identity.
- **Review Package** — Artifact-first review surface containing source and machine values, provenance references, editable Human Edit fields, review state, severity data, timing data, book-level findings, and export state.
- **Editor Evaluation Protocol** — Frozen protocol defining reviewer qualifications, severity rubric, edit-magnitude formula, clocks, assignment or blinding, sample design, exclusions, and analysis rules.
- **Inline Binding Map** — Deterministic metadata connecting protected inline placeholders in target text to source-owned inline nodes without allowing model-authored wrapper markup or identifiers.
- **Run Snapshot** — Immutable record of Canonical Source HTML identity, Target Locale, Unit Manifest version, editorial inputs, Translation Method, and relevant configuration.
- **Translation Run** — One automatically executed workflow sequence from a Run Snapshot to explicit terminal processing and quality states.
- **Run Status Vector** — Separate processing, translation-completeness, deterministic-validation, human-review, and publication-readiness states; no component implies another.
- **Literal Anchor** — A faithfulness-oriented reference generated for evaluation; it is never eligible to become a Machine Final directly.
- **Idiomatic Candidate** — A natural target-language proposal generated for a Source Unit.
- **Recovery Candidate** — An additional local proposal generated only after a Source Unit fails an evaluation or Hard Rule.
- **Machine Final** — The immutable target-language text and Inline Binding Map committed for a successful Source Unit after required evaluation; scores, critiques, rationale, provenance, and source-owned markup remain separate metadata.
- **Failed Unit** — A required Source Unit for which the Translation Method cannot commit a compliant Machine Final.
- **Translation Draft** — Reassembled translated reader HTML containing a Machine Final for every required Source Unit and accompanied by provenance and validation reports.
- **Human Edit** — A reviewer-authored value stored separately from its immutable Machine Final.
- **Assembly Report** — Human-readable report of placement, omissions, duplication, failures, and output facts.
- **Validation Report** — Machine-readable results of deterministic completeness, structure, terminology, language, and integrity checks.

## 4. Features and Functional Requirements

### 4.1 Skill Contract and Orchestration

**Description:** The Workflow Suite is delivered as composable Skill Workflows rather than one opaque command. Each workflow exposes stable product-level contracts while allowing internal methods to evolve. The Orchestration Skill Workflow realizes UJ-1 and UJ-3.

**MVP invocable inventory:** Prepare Translation Skill, Run Translation Skill, Assemble and Validate Translation Skill, Review Translation Skill, and Compare Translation Runs Skill. Internal stages may be subworkflows, but these five entry points and their artifact handoffs are externally distinguishable.

| Invocable Skill Workflow | Required inputs | Success artifacts | Non-success outcome |
| --- | --- | --- | --- |
| Prepare Translation Skill | Canonical Source HTML, Target Locale, editorial inputs, Preparation Policy, Translation Method, Context Policy | Signed Prepare Package with `ready-for-confirmation` state | `blocked` preparation report with content or contract findings |
| Run Translation Skill | Confirmed Prepare Package | Updated Unit Manifest with attributed proposals, evaluations, Machine Finals or Failed Units, plus Translation Run summary | `processing-failed` or `translation-incomplete` summary with resumable diagnostics |
| Assemble and Validate Translation Skill | Canonical Source HTML and completed Unit Manifest | Translation Draft, Assembly Report, and Validation Report | `assembly-failed` or `validation-failed` reports; no eligible Translation Draft |
| Review Translation Skill | Complete Translation Draft and provenance artifacts | Review Package, Human Edits, book-level findings, reviewed export, and review metrics | `review-blocked` report; Machine Finals remain unchanged |
| Compare Translation Runs Skill | Two or more Translation Runs and their Run Snapshots | Compatibility decision, configuration diff, and comparable outcome metrics | `non-equivalent` report that prevents silent ranking |

#### FR-1: Declare skill contracts

Each Skill Workflow must declare its purpose, required inputs, produced artifacts, preconditions, terminal states, and failure behavior.

**Consequences (testable):**
- A caller can determine whether a workflow can run without reading its implementation.
- A successful result and an incomplete or failed result use distinguishable terminal states.
- Every produced artifact identifies the Skill Workflow and version that produced it.
- Each invocable Skill Workflow declares its accepted artifact versions, confirmation or authorization needs, retry safety, and terminal-state vocabulary.

#### FR-2: Compose workflows through artifacts

The Orchestration Skill Workflow must pass versioned artifacts between Skill Workflows and must not depend on their private prompt or provider details.

**Consequences (testable):**
- Replacing one conforming Skill Workflow does not require changing unrelated workflow contracts.
- Missing, incompatible, or stale input artifacts stop the dependent workflow with an actionable error.
- An actionable error identifies the Skill Workflow, artifact or Source Unit, violated rule, expected and observed state, retryability, and next operator action.
- The minimum information contract is product-stable even when physical schemas or storage change: artifact identity and version, Run Snapshot identity, producer, timestamps, input identities, terminal state, findings, and integrity digest.

#### FR-3: Execute automatically after confirmation

After an authorized Translation Operator confirms a valid Prepare Package, the Orchestration Skill Workflow must execute the configured workflow sequence without interactive approval gates.

**Consequences (testable):**
- The run reaches an explicit terminal processing state without requiring per-unit human input.
- A processing-complete run may still be translation-incomplete or validation-failed.
- Restart and retry behavior never silently changes the frozen Run Snapshot.
- Confirmation is recorded with operator identity, time, and the exact Prepare Package integrity digest.
- Live model stages cannot start when any live-operation entry gate in §0.1 is missing or invalid.

### 4.2 Source Preparation and Frozen Inputs

**Description:** A preparation Skill Workflow identifies book-owned content, preserves structure, and freezes reproducible inputs before generation begins. It realizes the entry path of UJ-1.

#### FR-4: Select book-owned content

The preparation Skill Workflow must identify translatable book-owned content while excluding reader chrome, controls, CSS, JavaScript, generated statistics, and duplicated projections.

**Consequences (testable):**
- Headings, prose, lists, quotations, captions, tables, footnotes, and verse are included when supported.
- Excluded content is preserved unchanged and listed by category in the Assembly Report.
- Ambiguous or unsupported markup produces an explicit finding rather than silent omission.

#### FR-5: Build stable Source Units

The preparation Skill Workflow must create ordered Source Units with durable identity, deterministic placement, structural metadata, and source-language content.

**Consequences (testable):**
- Repeating preparation against identical Canonical Source HTML and configuration yields the same Source Unit identities and order.
- Each placement resolves exactly once against the frozen source or the workflow fails.
- Segmentation does not require an LLM to reconstruct document HTML.

#### FR-6: Prepare editorial guidance

The preparation Skill Workflow must propose terminology candidates from Canonical Source HTML, and the Translation Operator must be able to confirm a Terminology Sheet and Literary Style Sheet before a Translation Run starts.

**Consequences (testable):**
- Locked, preferred, and advisory terminology rules remain distinguishable.
- Proposed terminology remains unconfirmed until an editorial decision classifies it as locked, preferred, advisory, or rejected.
- Each applicable rule can be associated with relevant Source Units.
- Missing required editorial inputs stop the run; optional omissions are recorded.
- Language-specific literary guidance is frozen in the Literary Style Sheet or Translation Method rather than hard-coded in orchestration.
- The Terminology Sheet and Literary Style Sheet are required for the pilot, may explicitly contain no entries, and must be editorially confirmed before Prepare Translation succeeds.

#### FR-7: Freeze a Run Snapshot

The Orchestration Skill Workflow must freeze all inputs that can materially affect a Translation Run.

**Consequences (testable):**
- The Run Snapshot identifies the Canonical Source HTML, Target Locale, Unit Manifest, editorial inputs, and Translation Method.
- Mutating an input after confirmation cannot alter an in-progress or historical Translation Run.
- A material input change requires a new Translation Run.
- Prepare Translation succeeds only by emitting a signed Prepare Package with terminal state `ready-for-confirmation`; otherwise it emits `blocked` with machine-readable findings.

### 4.3 Candidate Generation and Evaluation

**Description:** Generation and judgment remain separate attributed steps. Scores route work but never certify literary quality.

#### FR-8: Generate contrasting proposals

For every required Source Unit, the generation Skill Workflow must produce a Literal Anchor and at least one Idiomatic Candidate keyed to that Source Unit.

**Consequences (testable):**
- Outputs cannot reorder or create Source Units.
- The Literal Anchor must expose source order, sense relations, ambiguity, and emphasis closely enough to act as a faithfulness reference without optimizing for fluent prose.
- The Idiomatic Candidate must preserve meaning, emphasis, imagery, and applicable constraints in natural target-language prose without using the Literal Anchor as text to translate.
- The Literal Anchor is ineligible for direct commitment as a Machine Final.
- The Literal Anchor is an evaluator reference only; it is never scored, routed, recovered, or selected as an eligible candidate.
- Missing or malformed proposals place the Source Unit into an explicit non-success state.
- Candidate qualities are hypotheses subject to FR-10 evaluation; producing a fluent candidate is not evidence of literary quality or release readiness.

#### FR-9: Supply bounded deterministic context

Each generation or evaluation request must receive declared, bounded context derived from the Run Snapshot and Unit Manifest.

**Consequences (testable):**
- The provenance record identifies which context was supplied.
- Equivalent runs do not change request context due only to concurrency or processing order.
- Context truncation or omission is reported rather than concealed.
- No live request is built until the Context Policy is frozen and referenced by the Prepare Package.

#### FR-10: Evaluate faithfulness and naturalness

The evaluation Skill Workflow must assess each eligible candidate for source faithfulness and target-language naturalness, and for compliance with applicable terminology and declared Hard Rules, and must retain its critique.

**Consequences (testable):**
- Evaluation results remain attributable to the Source Unit, candidate, evaluator configuration, and Run Snapshot.
- Hard-rule violations remain distinguishable from scored judgments.
- Model scores are labeled routing telemetry, not publication approval.
- The Translation Method defines score scales and gates plus Hard Rule categories for source coverage, locked terminology, protected-placeholder integrity, target language or script, artifact validity, and prohibited additions.

#### FR-11: Route only weak units to recovery

The routing Skill Workflow must pass gate-satisfying candidates through unchanged and route only Source Units with weak candidates or Hard Rule violations to recovery.

**Consequences (testable):**
- A passing candidate is not regenerated merely for stylistic preference.
- A passing Idiomatic Candidate becomes the Machine Final text and Inline Binding Map verbatim; any correction or composition enters FR-13 evaluation as a new candidate.
- Each recovery decision cites the evaluation or Hard Rule that triggered it.
- Routing rules are versioned as part of the Translation Method.
- Passing, weak, recoverable, and failed states are testable only through the frozen Translation Method; absent gates block the Run Translation Skill.

### 4.4 Local Recovery and Final Commitment

**Description:** Recovery spends additional generation on identified weakness while protecting provenance and evaluation integrity.

#### FR-12: Generate local Recovery Candidates

For a routed Source Unit, the recovery Skill Workflow must generate additional candidates targeted at the recorded weakness without initiating a second full-book translation.

**Consequences (testable):**
- Recovery artifacts retain their triggering critique and generation lineage.
- Unrouted Source Units receive no Recovery Candidates.
- Recovery cannot modify the Canonical Source HTML or another Source Unit.
- Candidate count, retry count, token, elapsed-time, and cost ceilings come from the frozen Translation Method; exhausting any ceiling yields a Failed Unit.

#### FR-13: Evaluate newly composed text

Any newly generated, corrected, or composed target-language text must pass the required evaluation route before it can become a Machine Final.

**Consequences (testable):**
- No Machine Final exists without a recorded evaluation path.
- Combining evaluated fragments cannot bypass evaluation of the committed result. Safe composition is disabled in MVP unless a later Translation Method version defines an evaluated-span recipe and validates the composed output before commitment.

#### FR-14: Commit an attributed Machine Final

The commitment Skill Workflow must select one evaluated target-language value for each successful Source Unit and retain the selection rationale.

**Consequences (testable):**
- A Machine Final identifies its originating candidate and evaluation history.
- After recovery, the commitment Skill Workflow weighs every eligible surviving candidate against the triggering critique and records why the selected value resolves it.
- Machine Final content contains only committed target-language text plus its Inline Binding Map; scores, critiques, rationale, provenance, and source-owned markup remain separate metadata.
- The Machine Final becomes immutable after commitment.
- Later Human Edits do not overwrite the Machine Final.
- Commitment cannot rewrite or normalize candidate language; deterministic serialization may normalize only artifact encoding outside the committed text and Inline Binding Map.

#### FR-15: Preserve honest failure

When no candidate satisfies the Translation Method, the workflow must retain a Failed Unit rather than promoting the Literal Anchor or another failing candidate.

**Consequences (testable):**
- A Translation Run with any unresolved required Failed Unit cannot claim a complete Translation Draft.
- The Failed Unit records attempted stages and actionable failure information.
- Automatic retries are bounded by the Translation Method. After exhaustion, resolution requires either a new Translation Run with a new Run Snapshot or operator diagnosis and retry under the identical snapshot; a Human Edit may salvage editorial work but cannot mint or replace a Machine Final.

### 4.5 Deterministic Assembly and Validation

**Description:** Language generation supplies values; deterministic workflows own document structure, placement, and compliance. This feature completes UJ-1.

#### FR-16: Reassemble without structural regeneration

The assembly Skill Workflow must clone Canonical Source HTML and replace only mapped book-owned values with Machine Final text, deterministically rebinding source-owned inline nodes through the Inline Binding Map.

**Consequences (testable):**
- The workflow does not ask an LLM to emit or reconstruct the document HTML.
- Model output cannot author HTML wrappers, source identifiers, DOM locators, or executable markup.
- Document order, identifiers, anchors, footnotes, and non-translatable content remain preserved.
- Split Source Units rejoin their owning structural block in deterministic order without duplicating wrapper markup.
- The workflow preserves the source identity and order of inline emphasis and verse structure. When a natural translation moves emphasized words, the mapped inline placement may move, but the owning structural relationship must not.
- Translated title and other book-owned metadata project to every reader location from one Machine Final.
- Duplicate reader projections originate from one translated value rather than separate translations.

#### FR-17: Prove deterministic round-trip integrity

Before model-backed generation is accepted for a Canonical Source HTML class, the assembly and validation workflows must pass a deterministic dummy round trip that substitutes known test values through the Unit Manifest.

**Consequences (testable):**
- The proof demonstrates complete selection, stable identity, exactly-once placement, split-block reassembly, projection mapping, and structural preservation.
- Test-only dummy values are labeled structural fixtures and cannot be represented as Machine Finals or Literal Anchors.
- A failing content class is unsupported until the round-trip defect is resolved or the Preparation Policy excludes it explicitly.
- No model-stage implementation begins for a Content Class until that class passes the deterministic round-trip proof.

#### FR-18: Validate completeness and structural integrity

The validation Skill Workflow must deterministically check unit coverage, placement, structure, anchors, footnotes, and protected inline placeholders.

**Consequences (testable):**
- Missing, duplicated, unexpected, or unresolved required Source Units fail validation.
- Each locator resolves exactly once.
- Findings identify the affected Source Unit or structural location.
- A Required Source Unit without exactly one Machine Final blocks Translation Draft eligibility; Excluded Source Units do not; Unsupported Source Units block preparation unless explicitly excluded by the Preparation Policy.
- Every protected placeholder and Inline Binding Map entry binds exactly once to one source-owned inline node; missing, duplicate, unexpected, or cross-unit bindings are blocking errors.
- Validation findings use stable `blocking-error` and `warning` severities. Any unresolved blocking error prevents a compliance-clean status and Translation Draft eligibility.

#### FR-19: Validate language and terminology constraints

The validation Skill Workflow must check locked terms, unresolved source-language residue within declared limits, Target Locale metadata, and directionality requirements.

**Consequences (testable):**
- Locked-term violations are reported independently from model evaluation scores.
- The translated document declares the Target Locale using a canonical BCP 47 tag.
- RTL output declares correct document direction; nested language changes remain identifiable.
- Residual-language detection limitations are recorded with the Validation Report.
- The Preparation Policy declares permitted code-switching, quotations, names, and other residual-language exemptions; the detector reports evidence and applies failure only where the policy defines a prohibited condition.

#### FR-20: Produce explicit run outputs

The Orchestration Skill Workflow must emit the Unit Manifest, Translation Draft when complete, Assembly Report, Validation Report, and Translation Run summary.

**Consequences (testable):**
- The summary distinguishes processing, translation completeness, deterministic compliance, human review, and publication readiness.
- An incomplete run still emits available diagnostic and provenance artifacts.
- No report represents successful execution alone as quality approval.

### 4.6 Human Review and Export

**Description:** Human judgment follows the automatic run and remains measurable without erasing machine provenance. This feature realizes UJ-2.

#### FR-21: Inspect unit provenance

A Literary Editor must be able to inspect a Source Unit, Machine Final, proposals, evaluations, recovery history, and rationale together after the Translation Run has produced a complete Translation Draft.

**Consequences (testable):**
- Provenance can be retrieved by Source Unit identity.
- Missing provenance is a compliance finding and blocks a claim of complete attribution.
- Processing-complete but translation-incomplete runs remain available for operator diagnosis and retry, but cannot enter literary review or reviewed export.
- The Review Translation Skill must render these fields from a Review Package without requiring a dedicated graphical application.

#### FR-22: Record non-destructive Human Edits

A Literary Editor must be able to store a Human Edit and review state without overwriting its Machine Final.

**Consequences (testable):**
- Machine Final and Human Edit remain separately retrievable.
- Edit time, edit magnitude, and issue severity can be recorded at Source Unit level.
- Export identifies whether each value is machine-final or human-edited.
- The Review Package supports inspect, record edit, set review state, assign severity, record timing, add book-level finding, validate, and export operations through the Skill Workflow and machine-readable artifacts.

#### FR-23: Capture book-level review

The review Skill Workflow must support book-level findings for voice, character consistency, recurring imagery, and continuity that unit evaluation cannot certify.

**Consequences (testable):**
- Book-level findings are not misrepresented as unit scores.
- Human-review status remains separate from deterministic validation status.

### 4.7 Reproducibility and Method Comparison

**Description:** Method Maintainers can compare compatible runs and understand exactly what changed. This feature realizes UJ-3.

#### FR-24: Reproduce a Translation Run

The Workflow Suite must preserve sufficient frozen identity and configuration to rerun a Translation Method against the same inputs.

**Consequences (testable):**
- A rerun can identify any unavailable provider or model dependency that prevents exact reproduction.
- Deterministic preparation, placement, and validation outputs repeat for identical inputs and versions.

#### FR-25: Compare compatible runs

The comparison Skill Workflow must compare Translation Runs and disclose material input or method differences.

**Consequences (testable):**
- The comparison reports Recovery yield, validation findings, edit time, edit magnitude, and issue severity when available.
- Runs with different Canonical Source HTML, Target Locale, terminology, or style inputs are flagged as non-equivalent rather than silently ranked.

### 4.8 Pilot Qualification

**Description:** The generic Workflow Suite remains language- and provider-configurable, while a concrete Pilot Profile makes MVP release acceptance decidable.

#### FR-26: Freeze a Pilot Profile

Before the product makes pilot or release-qualification claims, the Product Owner must approve a Pilot Profile defining the source/target language pair, representative public-domain corpus, applicable Preparation Policy, and measurable throughput, latency, cost, and editorial-evaluation budgets.

**Consequences (testable):**
- Every pilot book and content class maps through the referenced Preparation Policy to an explicit included, excluded, or unsupported category.
- Numeric qualification budgets are versioned and testable.
- Changing the Pilot Profile invalidates prior release-certification results but does not change the generic Skill Workflow contracts.

#### FR-27: Run a reproducible usefulness evaluation

The Product Owner must freeze a Baseline Method and evaluation protocol before claiming improvement in human editing burden.

**Consequences (testable):**
- Workflow Suite and Baseline Method outputs use the same Pilot Profile and source corpus.
- Qualified editors receive an equivalent review task and severity rubric, while timing and edit magnitude are captured consistently.
- The evaluation reports editor count, assignment method, exclusions, uncertainty, and critical residual errors alongside median review-and-edit time.
- The Editor Evaluation Protocol defines qualified-editor criteria, the review clock, edit-magnitude formula, severity rubric, assignment or blinding, a human-rated gold subset, sample-size rationale, and analysis plan; a dry run must demonstrate that these measurements can be reproduced.

#### FR-29: Freeze a Translation Method

Before Run Translation starts, the Translation Method must freeze evaluator scales, routing and commitment gates, Hard Rule categories, recovery strategy, retry and candidate ceilings, token/time/cost ceilings, and terminal-state rules.

**Consequences (testable):**
- Missing or internally inconsistent gates make the Prepare Package invalid.
- Every evaluation, routing, recovery, commitment, and failure decision cites the Translation Method version and applicable rule.
- Threshold values remain replaceable configuration and are not hard-coded into the generic Skill Workflow contract.

#### FR-30: Freeze deterministic context behavior

Before live generation, the Context Policy must define source neighbors, committed target neighbors, window bounds, batching order, concurrency behavior, truncation, and failed-predecessor behavior.

**Consequences (testable):**
- Identical Run Snapshots and policy versions produce identical request context independent of runtime scheduling.
- A context dependency that cannot be satisfied yields a declared blocked or failed state rather than an implicit fallback.

#### FR-31: Enforce Source Unit eligibility states

The preparation and validation workflows must classify every selected content location as Required, Excluded, or Unsupported under the Preparation Policy.

**Consequences (testable):**
- No content location can enter generation without one eligibility state and one stable identity.
- An empty included set or any unresolved Unsupported Source Unit prevents a `ready-for-confirmation` Prepare Package.
- Eligibility counts and reasons appear in the Assembly Report and Validation Report.
- Excluded book-owned content must round-trip unchanged; omission is permitted only for non-book-owned chrome or generated projections explicitly outside Canonical Source HTML ownership.

## 5. Cross-Cutting Non-Functional Requirements

### 5.1 Integrity and Reliability

- **NFR-1:** Canonical Source HTML and committed Machine Finals are immutable within a Translation Run.
- **NFR-2:** Lifecycle updates and artifact writes must be recoverable after interruption without representing partial state as complete.
- **NFR-3:** For identical frozen inputs and component versions, deterministic workflow stages must produce byte-equivalent machine artifacts under a versioned canonical serialization or report the source of nondeterminism. This claim excludes live model outputs unless the provider guarantees deterministic replay.
- **NFR-4:** Required provenance loss is a run-level compliance failure.

### 5.2 Accessibility and Language Correctness

- **NFR-5:** Translation Draft HTML must preserve heading hierarchy, landmarks and navigation semantics, reading order, anchor and footnote behavior, keyboard-focus order, and programmatic language information from Canonical Source HTML; any changed or missing behavior is a blocking validation error.
- **NFR-6:** Document and passage languages must be programmatically determinable; directionality must be correct for supported RTL Target Locales.

### 5.3 Security and Data Governance

- **NFR-7:** Every external model transfer must be attributable to a Translation Run and limited to the declared content and context bounds.
- **NFR-8:** Secrets must never be embedded in Run Snapshots, reports, or exported Translation Drafts.

### 5.4 Operability

- **NFR-10:** Workflow and unit state must be observable by stable identity, stage, attempt, terminal state, and actionable error.
- **NFR-11:** Every Skill Workflow invocation records start and finish time, input and output artifact digests, attempt and retry counts, applicable operation ceilings, terminal state, and findings count.
- **NFR-12:** MVP is batch-oriented and prioritizes integrity and resumability over interactive latency; the Translation Method supplies live token, candidate, retry, elapsed-time, and cost ceilings, while later Pilot Profiles supply qualification budgets.

## 6. Constraints and Guardrails

- Structure is preserved independently from generated language.
- The Unit Manifest is durable machine truth; model requests and responses are bounded attributed views.
- Model outputs are keyed by Source Unit identity and cannot reorder the document.
- Newly composed or corrected text cannot bypass required evaluation.
- Failed Units remain failed until a conforming workflow resolves them.
- Processing completion, translation completeness, deterministic compliance, human review, and publication readiness are separate states.
- Unit-level evaluation cannot certify book-level literary coherence.
- The product contract must not fix a particular model provider, prompt, threshold, schema, or storage mechanism.

## 7. Non-Goals

- Replacing qualified literary judgment or claiming autonomous publication readiness.
- Interactive human approval during the automatic Translation Run.
- Using the Literal Anchor as a Machine Final.
- Regenerating all passing Source Units for stylistic taste.
- Running a second full-book translation as recovery.
- Translating reader chrome, controls, generated statistics, CSS, or JavaScript as book content.
- Modifying Canonical Source HTML in place or regenerating document HTML with an LLM.
- Building a general translation management UI, public marketplace, or reader-facing on-demand translation product in MVP.
- Public multilingual SEO, `hreflang`, or locale-specific public URLs in MVP.
- Exporting a publication-ready EPUB or XLIFF package in MVP.

## 8. MVP Scope

### 8.1 In Scope

- Versioned Skill Workflow contracts and orchestration.
- Canonical Source HTML selection, Source Unit preparation, and Unit Manifest creation.
- Terminology Sheet, Literary Style Sheet, Translation Method, and Run Snapshot freezing.
- Literal Anchor and Idiomatic Candidate generation, evaluation, routing, local recovery, and Machine Final commitment.
- Deterministic HTML assembly and validation.
- Explicit incomplete and failed states with diagnostic artifacts.
- Unit-level provenance inspection, non-destructive Human Edits, and review measurements.
- Compatible-run comparison.
- A frozen Pilot Profile, Translation Method, Context Policy, Editor Evaluation Protocol, and Baseline Method for gated implementation and release qualification.
- Configurable Target Locale represented by canonical BCP 47 tags; the Pilot Profile selects the first concrete language pair without hard-coding product-wide coverage.

### 8.2 Out of Scope for MVP

- Dedicated graphical review workspace; the Review Translation Skill and Review Package provide the MVP review surface.
- Selection-only translation and live original/translated reader toggles.
- Automated book-level continuity certification.
- Concurrent multi-editor collaboration, permissions, and approval routing.
- RTL rollout beyond metadata/directionality correctness unless the pilot language requires it.
- Public publishing, SEO localization, EPUB reconstruction, and XLIFF interchange.

## 9. Success Metrics

### Primary

- **SM-1: Structural completeness** — 100% of required Source Units have exactly one valid placement and either one Machine Final or one explicit Failed Unit; no missing, duplicated, or unexpected unit is accepted. Validates FR-5, FR-15, FR-17, FR-18.
- **SM-2: Provenance completeness** — 100% of Machine Finals retain their Source Unit, originating candidate, evaluation path, Translation Method, and Run Snapshot attribution. Validates FR-10, FR-13, FR-14, FR-21.
- **SM-3: Human usefulness hypothesis** — under the frozen Pilot Profile, Baseline Method, and Editor Evaluation Protocol, median qualified-editor review-and-edit time is at least 30% lower for Workflow Suite output, with no increase in critical residual errors. This is a falsifiable release hypothesis, not an implementation acceptance claim. Validates FR-8 through FR-15, FR-22, FR-26, FR-27, FR-29, and FR-30.

### Secondary

- **SM-4: Deterministic integrity** — identical frozen inputs and versions yield zero differences in Source Unit identity/order, placement, and Validation Report results. Validates FR-5, FR-7, FR-16 through FR-18, FR-24.
- **SM-5: Recovery yield** — report the proportion of routed Source Units that become compliant Machine Finals after local recovery, segmented by failure reason; no target is set until a baseline exists. Validates FR-11 through FR-15.
- **SM-6: Editorial burden profile** — report edit time, edit magnitude, and issue severity by stage outcome and Source Unit type. Validates FR-22, FR-23, FR-25, FR-27.

### Counter-Metrics

- **SM-C1: Pass-through rate** — do not optimize for a higher pass rate if residual critical errors or edit burden worsen; high pass-through can conceal weak evaluation. Counterbalances SM-3 and SM-5.
- **SM-C2: Model score** — do not treat evaluator confidence or average scores as literary quality or publication readiness. Counterbalances SM-3.
- **SM-C3: Completion rate** — do not promote failing content or suppress validation findings merely to increase completed Translation Runs. Counterbalances SM-1.

## 10. Risks and Mitigations

- **Fluent but materially unfaithful output:** contrast faithfulness and idiomatic proposals, retain critique, and measure the severity of residual errors found by human reviewers.
- **Structural corruption hidden by readable prose:** keep HTML assembly deterministic and validate placement, anchors, footnotes, and placeholders.
- **Terminology or voice drift:** freeze editorial inputs, retain unit-level applicability, and require book-level human review.
- **Concurrency-dependent context:** require declared deterministic context independent of processing order.
- **Recovery bypasses evaluation:** prohibit commitment of newly composed text without the required evaluation route.
- **Incomplete runs appear successful:** separate processing, translation, compliance, review, and publication states.
- **Configuration changes invalidate comparisons:** disclose Run Snapshot and Translation Method differences before comparison.

## 11. Dependencies and Integration Boundaries

- Canonical EPUB-derived HTML and its structural contract are upstream dependencies.
- Skill execution, model access, artifact storage, and secrets management are provided by LibrarianLM's runtime.
- The Workflow Suite consumes book content but does not own the Reader Artifact's presentation design.
- Downstream architecture must define versioned artifact schemas, resumption mechanics, and provider adapters without weakening this PRD's invariants.
- Downstream UX may later define a dedicated reviewer surface; MVP requirements remain artifact- and capability-based.

## 12. Open Questions and Deferred Decisions

1. What exact Context Policy should govern committed target-language neighbors under parallel execution? Owner: Architecture; phase blocker for live generation and explicitly enforced by FR-30.
2. Which concrete language pair, public-domain corpus, and qualification budgets form the first Pilot Profile? Owner: Product, Editorial, and Architecture; phase blocker for comparative evaluation and release qualification under FR-26.
3. What numeric evaluation scales, gates, and recovery ceilings form the first Translation Method? Owner: Product, Editorial, and Evaluation; phase blocker for Run Translation under FR-29.
4. Which artifact serialization and rendering format implements the Review Package contract? Owner: Architecture and UX; phase blocker for Review Translation implementation, but not for deterministic translation foundations.
5. What qualified-editor sample and dry-run design populate the first Editor Evaluation Protocol and Baseline Method? Owner: Product and Evaluation; phase blocker for usefulness evidence, not deterministic foundations.
6. Should XLIFF or EPUB export follow the initial HTML workflow, and what provenance must survive that handoff? Owner: Product; revisit after the HTML pilot meets SM-1 through SM-4.
7. Should a later workflow add an automated continuity audit, or should book-level continuity remain exclusively human-assessed? Owner: Product and Editorial; revisit after pilot error analysis.

## 13. Assumptions Index

No unowned assumptions remain. All unresolved choices are explicit gates or deferred decisions in §12.
