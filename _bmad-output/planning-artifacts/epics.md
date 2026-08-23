---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-LibrarianLM-2026-08-23/prd.md
  - _bmad-output/planning-artifacts/prds/prd-LibrarianLM-2026-08-23/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-LibrarianLM-2026-08-23/ARCHITECTURE-SPINE.md
  - _bmad-output/specs/spec-LibrarianLM/SPEC.md
  - _bmad-output/specs/spec-LibrarianLM/stories.yaml
scope: epics-1-through-3
---

# LibrarianLM - Epic Breakdown

## Overview

This document provides the implementation-ready epic and story breakdown for LibrarianLM through deterministic translation, live translation, and artifact-first editorial review. Epic 1's six stories remain the currently scheduled implementation sequence from `stories.yaml`; Epics 2 and 3 are fully planned but unscheduled. Comparison and pilot-evidence work remains preserved in a separate deferred register under Epic 4.

## Requirements Inventory

### Functional Requirements

FR1: Each Skill Workflow must declare its purpose, required inputs, produced artifacts, preconditions, terminal states, failure behavior, accepted artifact versions, confirmation needs, and retry safety.

FR2: The Orchestration Skill Workflow must compose workflows through versioned artifacts without depending on private prompt, provider, or storage details, and must reject missing, stale, or incompatible inputs with actionable errors.

FR3: After an authorized operator confirms a valid Prepare Package, orchestration must execute automatically to an explicit terminal state without per-unit approval and without changing the frozen Run Snapshot during restart or retry.

FR4: Prepare Translation must identify translatable book-owned content while excluding reader chrome, controls, CSS, JavaScript, generated statistics, and duplicate projections; ambiguous or unsupported content must produce explicit findings.

FR5: Prepare Translation must create ordered Source Units with durable identity, deterministic placement, structural metadata, and source-language content that reproduce for identical inputs.

FR6: Prepare Translation must propose terminology candidates and let the operator confirm scoped Terminology and Literary Style Sheets before a live run.

FR7: Orchestration must freeze every material input into an immutable Run Snapshot and produce a signed `ready-for-confirmation` Prepare Package or a typed blocked result.

FR8: For every required Source Unit, generation must produce a Literal Anchor and at least one Idiomatic Candidate keyed to that unit; Literal Anchors are evaluator references only.

FR9: Every generation and evaluation request must receive declared, bounded, provenance-recorded context derived deterministically from the Run Snapshot and Unit Manifest.

FR10: Evaluation must assess eligible candidates for faithfulness, naturalness, applicable terminology, and Hard Rules while retaining attributable critiques and treating model scores only as routing telemetry.

FR11: Routing must pass gate-satisfying candidates unchanged and send only weak or Hard-Rule-violating units to recovery under versioned rules.

FR12: Recovery must generate bounded local candidates targeted at recorded weaknesses without re-running a full-book translation or modifying other units.

FR13: Any newly generated, corrected, or composed target text must pass the required evaluation path before commitment.

FR14: Commitment must select one evaluated target value per successful Source Unit, preserve its rationale and complete lineage, and make the Machine Final immutable.

FR15: When no candidate satisfies the Translation Method, the run must retain an explicit Failed Unit rather than promote a Literal Anchor or failing candidate.

FR16: Assembly must clone Canonical Source HTML, replace only mapped book-owned values, and deterministically rebind source-owned inline nodes without model-generated structure.

FR17: Every supported Canonical Source HTML class must pass a deterministic dummy round trip proving stable identity, complete selection, exact placement, split-block reassembly, projections, and structural preservation before live use.

FR18: Validation must deterministically check unit coverage, placement, structure, anchors, footnotes, and protected inline bindings; every blocking finding prevents draft eligibility.

FR19: Validation must check locked terminology, residual source-language evidence and declared tolerances, canonical Target Locale metadata, passage language, and directionality.

FR20: Orchestration must emit the Unit Manifest, eligible Translation Draft when complete, Assembly Report, Validation Report, and Translation Run summary with orthogonal status dimensions.

FR21: After a complete Translation Draft exists, an editor must be able to inspect each Source Unit with its Machine Final, proposals, evaluations, recovery history, and rationale.

FR22: An editor must be able to record Human Edits, review state, severity, timing, and export selection without overwriting Machine Finals.

FR23: Review must support book-level findings for voice, character consistency, recurring imagery, and continuity without representing them as unit scores.

FR29: Before Run Translation, the Translation Method must freeze evaluator scales, routing and commitment gates, Hard Rules, recovery strategy, ceilings, and terminal-state rules.

FR30: Before live generation, the Context Policy must freeze source and target neighbor rules, window bounds, batching, concurrency, truncation, and failed-predecessor behavior so scheduling cannot change context.

FR31: Prepare and Validate must classify every selected location as Required, Excluded, or Unsupported; unresolved Unsupported content or an empty included set blocks confirmation, while excluded book-owned content round-trips unchanged.

### NonFunctional Requirements

NFR1: Canonical Source HTML and committed Machine Finals are immutable within a Translation Run.

NFR2: Lifecycle updates and artifact writes must recover after interruption without representing partial state as complete.

NFR3: Identical frozen inputs and component versions must yield byte-equivalent deterministic artifacts under canonical serialization or report the nondeterminism source; live model outputs are excluded unless replay is guaranteed.

NFR4: Loss of required provenance is a run-level compliance failure.

NFR5: Translation Draft HTML must preserve heading hierarchy, landmarks, navigation semantics, reading order, anchors, footnotes, keyboard-focus order, and programmatic language information; any loss is blocking.

NFR6: Document and passage language must be programmatically determinable, with correct directionality for supported RTL locales.

NFR7: Every external model transfer must be attributable to a Translation Run and limited to declared content and context bounds.

NFR8: Secrets must never appear in Run Snapshots, reports, logs, or exported Translation Drafts.

NFR10: Workflow and unit state must be observable by stable identity, stage, attempt, terminal state, and actionable error.

NFR11: Every workflow invocation must record times, input/output digests, attempt/retry counts, applicable ceilings, terminal state, and finding count.

NFR12: MVP execution is batch-oriented and prioritizes integrity and resumability over interactive latency; numeric live budgets are frozen before live integration.

### Additional Requirements

AR1: Use artifact-centric pipes-and-filters: filters consume immutable versioned artifacts and emit new artifacts; orchestration sequences filters but owns no domain truth (`AD-1`).

AR2: A shared kernel exclusively owns cross-workflow schemas, stable identities, lifecycle legality, canonical serialization, and compatibility (`AD-2`).

AR3: The filesystem artifact ledger is append-only and digest-addressed; manifest publication requires predecessor-digest compare-and-swap, deterministic rebase of disjoint changes, linked completion receipts, and verified-chain resume (`AD-3`).

AR4: Source Unit IDs derive from source digest, typed DOM locator, segmentation-profile version, and segment ordinal; source-text digest is separate and any mismatch is terminal (`AD-4`).

AR5: Live context uses deterministic per-unit ContextBundle objects and earlier-wave target artifacts only; bundles record canonical order, rendered bytes, policy, truncation, and absence (`AD-5`).

AR6: Deterministic content objects exclude operational time/attempt/path data; linked invocation receipts carry execution metadata, terminal outcome, findings, and produced digests (`AD-6`).

AR7: **Mandatory starter for the first implementation story:** create `src/i18n-pipeline/pyproject.toml`, lock Python 3.14.4, Pydantic 2.13.4, lxml 6.1.2 under uv 0.11.19, commit `uv.lock`, configure Pydantic as strict/frozen/extra-forbid, and prove unknown/coercible inputs fail before feature code (`AD-7`).

AR8: Protected inline bindings use exact ASCII tokens and a separate Inline Binding Map; binding loss, duplication, invention, crossing, or cross-unit relocation is blocking (`AD-8`).

AR9: Prepare, Run, Assemble-and-Validate, Review, Compare, and Orchestrate are independently invocable thin entrypoints around one package; no daemon, queue, service, or database exists in MVP (`AD-9`).

AR10: The kernel enforces monotonic workflow transitions and independent processing, completeness, compliance, review, and publication states; retries append rather than rewrite (`AD-10`).

AR11: All live calls cross a canonical Model Gateway with bounded preflight, immutable model revision, exact request/response/usage digests, and no workflow-level provider SDK imports (`AD-11`).

AR12: Prepare alone owns content classification, segmentation, Source Unit ordering, locators, and projection groups; downstream stages never resegment (`AD-12`).

AR13: All post-conversion i18n HTML parsing and serialization uses the lxml adapter with network and external entities disabled, typed locators, structural fingerprints, and component identity (`AD-13`).

AR14: Assembly and validation are separate deterministic filters; validation is read-only and solely determines draft eligibility (`AD-14`).

AR15: Human review is an append-only overlay keyed by Source Unit/run and never mutates Machine Finals or manifest history (`AD-15`).

AR16: Fixture and live modes share contracts, but fixture mode cannot resolve a live Model Gateway; Epic 1 uses fixture mode and Epic 2 adds explicitly gated live mode (`AD-16`).

AR17: Prepare accepts a Canonical Source Package binding HTML, converter summary, converter identity, and ownership/projection profile; upstream book-owned omissions block preparation (`AD-17`).

AR18: Prepare Package signing uses HMAC-SHA-256 with a trusted runtime key ring and a separate operator confirmation receipt; verification fails closed (`AD-18`).

AR19: Validation composes structural, terminology, residual-language, locale/directionality, and accessibility controls; Assembly, Validation, and Run Summary reports are canonical machine-truth objects (`AD-19`).

AR20: Pilot evidence uses frozen Baseline Method and Editor Evaluation Protocol objects and a comparison-generated Usefulness Evaluation Report (`AD-20`, deferred from the current phase).

AR21: Confirmed terminology/style rules resolve to explicit Source Unit sets; Literal Anchors are never eligible for commitment; Machine Finals require eligible evaluated candidates, evaluation digest, and rationale (`AD-21`).

AR22: MVP live mode is single-host Windows x86-64 on operator-owned local NTFS with startup environment/locking/flush/dependency/serialization checks, operator-only ACLs, no automatic artifact pruning, and verified backup/restore (`AD-22`).

AR23: Live invocation uses linked `reserved → dispatched → provider-acknowledged → terminal` receipts, stable idempotency identity, ceiling accounting, and blocked reconciliation for unknown non-idempotent crash states (`AD-23`).

AR24: Canonical JSON uses UTF-8/LF, sorted keys, compact separators, integer versions/counts, decimal strings for scores, and explicit receipt timestamps; reject floats, NaN, duplicate/unknown fields, and implicit coercion.

AR25: Errors and findings use stable codes plus workflow, artifact/unit, rule, expected/observed values, retryability, and next action; exceptions never cross entrypoint boundaries.

AR26: The kernel contract seed includes UnitManifest, UnitRecord, lifecycle, InlineBindingMap, ContextBundle, ProjectionMap, ModelRequest/Response, provenance objects, required reports, and Component Identity shapes from the architecture spine.

AR27: The scheduled implementation queue contains exactly the six ordered Epic 1 slices from `stories.yaml`; Story 1 pauses after specification review and after implementation, and Story 5 pauses after implementation. Epic 2 and 3 stories are planned but unscheduled; Epic 4 remains unnumbered and deferred.

### UX Design Requirements

No UX design contract exists for this artifact-first deterministic-foundation phase; no UX-specific implementation requirements were extracted.

### FR Coverage Map

FR1: Epic 1 - Deterministic Translation Foundation
FR2: Epic 1 - Deterministic Translation Foundation
FR3: Epic 1 - Deterministic Translation Foundation
FR4: Epic 1 - Deterministic Translation Foundation
FR5: Epic 1 - Deterministic Translation Foundation
FR6: Epic 1 - Deterministic Translation Foundation
FR7: Epic 1 - Deterministic Translation Foundation
FR8: Epic 2 - Attributed Live Translation
FR9: Epic 2 - Attributed Live Translation
FR10: Epic 2 - Attributed Live Translation
FR11: Epic 2 - Attributed Live Translation
FR12: Epic 2 - Attributed Live Translation
FR13: Epic 2 - Attributed Live Translation
FR14: Epic 2 - Attributed Live Translation
FR15: Epic 2 - Attributed Live Translation
FR16: Epic 1 - Deterministic Translation Foundation
FR17: Epic 1 - Deterministic Translation Foundation
FR18: Epic 1 - Deterministic Translation Foundation
FR19: Epic 1 - Deterministic Translation Foundation
FR20: Epic 1 - Deterministic Translation Foundation
FR21: Epic 3 - Non-destructive Editorial Review
FR22: Epic 3 - Non-destructive Editorial Review
FR23: Epic 3 - Non-destructive Editorial Review
FR29: Epic 2 - Attributed Live Translation
FR30: Epic 2 - Attributed Live Translation
FR31: Epic 1 - Deterministic Translation Foundation

## Epic List

### Epic 1: Deterministic Translation Foundation

Enable a Translation Operator to take a Canonical Source Package through fixture-mode Prepare and Assemble-and-Validate workflows and receive stable Source Units, a deterministic round-trip draft, explicit validation reports, and resumable outcomes without live model calls.

**Phase:** Current. This epic contains the six approved implementation slices from `stories.yaml`.

**FRs covered:** FR1-FR7, FR16-FR20, FR31.

### Epic 2: Attributed Live Translation

Enable a Translation Operator to produce a complete live translation with controlled batching, explicit failure handling, durable provenance, and model attribution.

**Phase:** Planned, not scheduled. This epic has implementation-ready stories but is not part of the six-story Epic 1 execution queue.

**FRs covered:** FR8-FR15, FR29-FR30.

### Epic 3: Non-destructive Editorial Review

Enable an Editor to inspect, revise, and export a completed draft without altering source artifacts or obscuring editorial changes.

**Phase:** Planned, not scheduled. This epic has implementation-ready stories but is not part of the six-story Epic 1 execution queue.

**FRs covered:** FR21-FR23.

### Epic 4: Reproducible Comparison and Evidence

Enable the team to compare translation methods and produce reproducible evidence about translation quality and workflow usefulness.

**Phase:** Deferred. This epic is retained for complete PRD traceability and will not be expanded into current implementation stories or pilot planning.

**FRs covered:** FR24-FR27.

## Epic 1: Deterministic Translation Foundation

Enable a Translation Operator to take a Canonical Source Package through fixture-mode Prepare and Assemble-and-Validate workflows and receive stable Source Units, a deterministic round-trip draft, explicit validation reports, and resumable outcomes without live model calls.

### Story 1.1: Bootstrap the i18n Package and Shared Kernel Contracts

As a Translation Operator,
I want every workflow to use the same strict, versioned domain contracts,
So that invalid or incompatible artifacts fail before processing and deterministic stages behave consistently.

**Requirements:** FR1, FR2.

**Acceptance Criteria:**

**Given** a clean repository checkout
**When** the i18n package is installed from its committed lockfile
**Then** `src/i18n-pipeline/pyproject.toml` and `uv.lock` provide a reproducible environment using Python 3.14.4, Pydantic 2.13.4, lxml 6.1.2, and uv 0.11.19
**And** no i18n pipeline code is placed outside `src/i18n-pipeline`.

**Given** kernel artifact models
**When** input contains unknown fields, implicit coercions, floating-point values, NaN, duplicate fields, or invalid versions
**Then** validation fails with a stable actionable error
**And** accepted models are strict, frozen, and reject extra fields.

**Given** identical valid domain content
**When** it is serialized repeatedly
**Then** canonical JSON is byte-equivalent using UTF-8, LF endings, sorted keys, compact separators, integer versions and counts, and decimal-string scores
**And** operational timestamps, paths, and attempt data remain outside deterministic content objects.

**Given** the initial shared-kernel contract set
**When** its public schemas are inspected
**Then** it includes stable identities, compatibility metadata, lifecycle and status models, Unit Manifest and Unit Record, Inline Binding Map, Context Bundle, Projection Map, model request/response and provenance shapes, Component Identity, and required report shapes
**And** workflows cannot define competing versions of these contracts.

**Given** an attempted lifecycle transition
**When** the transition is illegal or would reverse completed state
**Then** the kernel rejects it using a stable error code
**And** processing, completeness, compliance, review, and publication remain independent status dimensions.

**Given** incompatible, stale, malformed, or missing artifact input
**When** a workflow boundary validates it
**Then** processing stops before feature logic runs
**And** the resulting error identifies the workflow, artifact or unit, rule, expected and observed values, retryability, and next action without exposing an uncaught exception.

### Story 1.2: Implement Durable Artifact State and Recovery

As a Translation Operator,
I want workflow artifacts and state transitions to survive interruption safely,
So that I can resume a run without losing provenance or mistaking partial work for completion.

**Requirements:** FR2, FR3.

**Acceptance Criteria:**

**Given** a valid canonical content object
**When** it is published
**Then** it is stored immutably under its SHA-256 digest
**And** reading it verifies that its canonical bytes match that digest.

**Given** a workflow invocation or state transition
**When** its operational result is recorded
**Then** an immutable receipt records its predecessor, times, attempt and retry counts, applicable ceilings, terminal outcome, findings, and produced artifact digests
**And** operational metadata does not alter deterministic content objects.

**Given** a manifest successor with an expected predecessor digest
**When** publication acquires the run lock and the current reference still matches that predecessor
**Then** the manifest reference is atomically replaced
**And** a completion receipt binds the predecessor and successor digests.

**Given** the current manifest changed before publication
**When** the proposed update advances only disjoint Source Units
**Then** the store deterministically rebases those advances in Source Unit order
**And** overlapping changes fail with `manifest-conflict`.

**Given** an interrupted or partially written workflow
**When** recovery begins
**Then** it resumes only from a verified receipt and manifest chain whose referenced objects exist and match their digests
**And** unlinked or incomplete state is never represented as complete.

**Given** concurrent attempts to update the same run
**When** they contend for publication
**Then** an exclusive per-run lock permits one writer at a time
**And** stale-lock reclamation requires local process-liveness verification.

**Given** a retry after a recoverable failure
**When** the same logical operation is attempted again
**Then** history is appended rather than rewritten
**And** stable identity, stage, attempt, terminal state, error code, retryability, and next action remain observable.

### Story 1.3: Prepare Stable Source Units

As a Translation Operator,
I want a Canonical Source Package converted into stable, classified Source Units,
So that every later deterministic stage operates on an approved and reproducible translation scope.

**Requirements:** FR4, FR5, FR6, FR7, FR31.

**Acceptance Criteria:**

**Given** a Canonical Source Package
**When** Prepare validates its HTML, converter summary, converter identity, ownership profile, and projection profile
**Then** all required components and compatible versions are bound to their digests
**And** upstream omissions of book-owned content block preparation with actionable findings.

**Given** Canonical Source HTML containing book content and application-owned material
**When** Prepare parses and classifies it
**Then** the lxml adapter runs with networking and external entities disabled
**And** reader chrome, controls, CSS, JavaScript, generated statistics, and duplicate projections are not selected for translation.

**Given** every selected location
**When** eligibility classification completes
**Then** each location is classified as Required, Excluded, or Unsupported
**And** the frozen Preparation Policy determines the content-class dispositions and residual-language tolerances; unresolved Unsupported content or an empty Required set produces a blocked result while Excluded book-owned content is retained for unchanged round-trip assembly.

**Given** identical package content and segmentation configuration
**When** Prepare is run repeatedly
**Then** it emits byte-equivalent ordered Source Units with typed DOM locators, structural metadata, source text, projection membership, and component identity
**And** each Source Unit ID derives from source digest, typed locator, segmentation-profile version, and segment ordinal.

**Given** a previously identified Source Unit
**When** its locator identity matches but its source-text digest differs
**Then** Prepare reports a terminal identity-integrity failure
**And** no downstream artifact silently reuses that unit identity.

**Given** terminology and literary-style candidates derived from the prepared units
**When** the operator confirms their scopes
**Then** every confirmed rule resolves to an explicit Source Unit set
**And** the confirmed sheets become immutable, versioned inputs to the Prepare Package.

**Given** a valid prepared package in fixture mode
**When** the operator confirms it
**Then** Prepare emits a signed `ready-for-confirmation` package using HMAC-SHA-256 and a separate confirmation receipt
**And** missing, invalid, or untrusted signatures fail closed.

### Story 1.4: Preserve Inline Structure and Assemble Drafts

As a Translation Operator,
I want translated values rebound into a clone of the source HTML without model-generated structure,
So that the resulting draft preserves the publication's exact semantics, placement, and inline markup.

**Requirements:** FR16, FR17.

**Acceptance Criteria:**

**Given** a supported source location containing source-owned inline nodes
**When** it is prepared for fixture translation
**Then** inline bindings are represented by exact ASCII protected tokens and a separate Inline Binding Map
**And** the translatable value contains no model-owned HTML structure.

**Given** protected tokens returned for a Source Unit
**When** bindings are checked before assembly
**Then** loss, duplication, invention, crossing, or cross-unit relocation creates a blocking finding
**And** malformed bindings are never inserted into the draft.

**Given** committed fixture target values and their Unit Manifest
**When** Assembly runs
**Then** it clones the Canonical Source HTML and replaces only mapped Required values
**And** Excluded book-owned content and all application-owned content remain unchanged.

**Given** split blocks or projected duplicate locations
**When** the canonical Source Unit is assembled
**Then** segments are rejoined in declared order and the selected value is applied to every Projection Map member using its declared transformation rule
**And** the applied value and Projection Map digests are recorded.

**Given** identical source, manifest, bindings, projection maps, and fixture values
**When** Assembly runs repeatedly
**Then** the candidate draft and Assembly Report are byte-equivalent
**And** no timestamp, path, attempt count, or scheduler order changes deterministic output.

**Given** every supported Canonical Source HTML class
**When** the deterministic dummy round-trip fixtures execute
**Then** they prove stable identity, complete selection, exact placement, split-block reassembly, projection behavior, structural preservation, anchors, and footnotes
**And** any regression blocks that content class from live use.

### Story 1.5: Validate Drafts and Emit Machine-Truth Reports

As a Translation Operator,
I want assembled drafts independently validated with canonical reports,
So that only structurally complete and policy-compliant HTML can become an eligible Translation Draft.

**Requirements:** FR18, FR19, FR20.

**Acceptance Criteria:**

**Given** a candidate draft, its source HTML, Unit Manifest, binding maps, and projection maps
**When** Validation runs
**Then** it reads those inputs without modifying them
**And** checks Source Unit coverage, placement, structure, anchors, footnotes, protected bindings, projections, and unchanged Excluded content.

**Given** confirmed terminology and declared language policies
**When** semantic validation runs
**Then** it checks locked terminology, residual source-language evidence and tolerances, canonical Target Locale metadata, passage language, and directionality
**And** every finding uses a stable code with rule, expected and observed values, retryability, and next action.

**Given** an assembled publication
**When** accessibility validation runs
**Then** it verifies heading hierarchy, landmarks, navigation semantics, reading order, keyboard-focus order, anchors, footnotes, and programmatically determinable language
**And** loss of any required property is blocking.

**Given** one or more unresolved blocking findings
**When** draft eligibility is calculated
**Then** no eligible Translation Draft is emitted
**And** processing, completeness, compliance, review, and publication statuses remain independently truthful.

**Given** a complete candidate with no blocking findings
**When** validation finishes
**Then** the draft is marked eligible
**And** canonical Assembly Report, Validation Report, and Translation Run Summary artifacts identify their inputs, components, findings, and status vector.

**Given** identical deterministic validation inputs and component versions
**When** validation is repeated
**Then** reports are byte-equivalent
**And** any nondeterminism is reported explicitly instead of being hidden.

### Story 1.6: Expose Fixture-Mode Workflows and Orchestration

As a Translation Operator,
I want independently invocable workflows and an automatic fixture-mode orchestration path,
So that I can run, resume, and diagnose the deterministic translation foundation through explicit artifact handoffs.

**Requirements:** FR1, FR2, FR3, FR7, FR20.

**Acceptance Criteria:**

**Given** the deterministic package capabilities
**When** workflow entrypoints are inspected
**Then** Prepare and Assemble-and-Validate are independently invocable thin adapters around `src/i18n-pipeline`
**And** each declares its purpose, inputs, outputs, preconditions, accepted versions, confirmation requirements, terminal states, failure behavior, and retry safety.

**Given** missing, stale, incompatible, or invalid workflow input
**When** an entrypoint is invoked
**Then** it rejects the input before processing with an actionable typed result
**And** no exception crosses the entrypoint boundary.

**Given** an operator-confirmed valid Prepare Package
**When** fixture-mode orchestration starts
**Then** it freezes all material inputs into an immutable Run Snapshot and proceeds without per-unit approval to an explicit terminal state
**And** restart or retry never changes the frozen snapshot.

**Given** fixture-mode execution
**When** the orchestration path needs target values
**Then** it uses the same artifact contracts as live mode with deterministic fixture values
**And** fixture mode cannot resolve or call a live Model Gateway.

**Given** interruption at any completed workflow boundary
**When** the same run is resumed
**Then** orchestration verifies its receipt and manifest chain, reuses compatible completed artifacts, and continues safely
**And** records a new attempt without rewriting history.

**Given** a successful fixture-mode run
**When** orchestration reaches its terminal state
**Then** it emits the Unit Manifest, eligible Translation Draft, Assembly Report, Validation Report, and Translation Run Summary
**And** every invocation records input and output digests, timing, attempts, ceilings, terminal state, and finding count.

**Given** a blocked or failed run
**When** orchestration terminates
**Then** its result identifies the failed workflow and artifact or Source Unit, stable error or finding codes, retryability, and next action
**And** partial output is never advertised as a complete or eligible draft.

## Epic 2: Attributed Live Translation

Enable a Translation Operator to produce a complete live translation with controlled batching, explicit failure handling, durable provenance, and model attribution.

### Story 2.1: Freeze Live Translation Controls and Context

As a Translation Operator,
I want live-run methods and context behavior frozen before dispatch,
So that evaluation decisions and request context cannot drift during a translation run.

**Requirements:** FR29, FR30.

**Acceptance Criteria:**

**Given** a proposed Translation Method
**When** it is validated for a live run
**Then** it declares evaluator scales, routing and commitment gates, Hard Rule categories, recovery strategy, candidate and retry limits, token/time/cost ceilings, and terminal-state rules
**And** missing, contradictory, or unbounded controls prevent confirmation of the Prepare Package.

**Given** a proposed Context Policy
**When** it is validated
**Then** it declares source and committed-target neighbor rules, window bounds, batching and wave order, concurrency, truncation, and failed-predecessor behavior
**And** no setting can be supplied implicitly by runtime scheduling or provider defaults.

**Given** identical Run Snapshot, Unit Manifest, and policy versions
**When** Context Bundles are generated under different worker schedules
**Then** each Source Unit receives byte-equivalent role-tagged context in canonical source order
**And** peers never consume one another while target context comes only from declared earlier-wave artifacts.

**Given** context that exceeds a frozen bound or cannot satisfy a declared dependency
**When** the bundle is built
**Then** truncation, omission, or absence is recorded explicitly with rendered bytes and digests
**And** a required unavailable dependency yields a typed blocked result rather than an implicit fallback.

**Given** a confirmed Prepare Package
**When** any Preparation Policy, Translation Method, or Context Policy content changes
**Then** its digest changes and the prior confirmation cannot authorize the altered run
**And** all downstream decisions cite the exact applicable policy or method version.

### Story 2.2: Dispatch Attributed and Recoverable Model Calls

As a Translation Operator,
I want every live model call bounded, attributable, and safely resumable,
So that provider behavior cannot bypass run controls or create ambiguous translation state.

**Requirements:** FR9, FR29, FR30.

**Acceptance Criteria:**

**Given** any live generation or evaluation request
**When** it is dispatched
**Then** it crosses the single Model Gateway as a canonical Model Request containing exact rendered-input and Context Bundle digests, prompt and method digests, immutable provider/model revision, all parameters, logical invocation identity, and idempotency key
**And** workflow and kernel modules do not import provider SDKs.

**Given** a provider model alias
**When** gateway preflight runs
**Then** the alias resolves to a captured immutable revision before dispatch
**And** unresolved revisions, incompatible artifacts, exceeded ceilings, or settings outside the frozen controls are rejected before transfer.

**Given** a live invocation
**When** it advances through execution
**Then** immutable linked receipts record `reserved`, `dispatched`, `provider-acknowledged`, and `terminal` states
**And** only a terminal receipt may link a normalized response and usage digest into a manifest successor.

**Given** a crash after dispatch
**When** recovery determines that provider status is unknown and the operation is not provably idempotent
**Then** the invocation becomes `reconciliation-required`
**And** orchestration does not automatically repeat the request or disregard its ceiling consumption.

**Given** provider credentials and returned metadata
**When** the call is recorded
**Then** secrets remain outside snapshots, artifacts, reports, logs, and drafts while the secret reference version and provider request identity remain attributable
**And** exact request, response, and usage digests bind the call to its Translation Run.

### Story 2.3: Generate Literal Anchors and Idiomatic Candidates

As a Translation Operator,
I want every Required Source Unit to receive attributable faithfulness and idiomatic proposals,
So that evaluation can compare natural translation candidates against a source-grounded reference.

**Requirements:** FR8, FR9.

**Acceptance Criteria:**

**Given** an eligible Required Source Unit and its Context Bundle
**When** generation completes successfully
**Then** it produces one Literal Anchor and at least one Idiomatic Candidate keyed to the stable Source Unit identity
**And** every proposal references its request, response, context, Translation Method, and Run Snapshot digests.

**Given** a Literal Anchor
**When** it is inspected
**Then** it exposes source order, sense relations, ambiguity, and emphasis as a faithfulness reference
**And** it is ineligible for scoring, routing, recovery, or commitment as a Machine Final.

**Given** an Idiomatic Candidate
**When** it is inspected
**Then** it preserves meaning, emphasis, imagery, applicable terminology, and protected bindings in natural target-language prose
**And** it is treated as an unevaluated hypothesis rather than evidence of literary quality.

**Given** proposal generation for multiple units
**When** results arrive out of order
**Then** proposals remain keyed to their original Source Units and cannot create, delete, or reorder units
**And** runtime completion order does not alter any unit's Context Bundle.

**Given** a missing or malformed required proposal
**When** generation is finalized
**Then** the Source Unit enters an explicit non-success state with actionable provenance
**And** no placeholder proposal or Literal Anchor is silently promoted.

### Story 2.4: Evaluate Candidates and Route Weak Units

As a Translation Operator,
I want candidate quality evaluated under frozen rules and only weak units routed to recovery,
So that passing translations remain unchanged while identifiable problems receive focused attention.

**Requirements:** FR10, FR11.

**Acceptance Criteria:**

**Given** an eligible Idiomatic Candidate
**When** evaluation runs
**Then** it assesses source faithfulness, target-language naturalness, applicable terminology, and declared Hard Rules
**And** retains an attributable critique linked to the Source Unit, candidate, evaluator configuration, Context Bundle, Translation Method, and Run Snapshot.

**Given** evaluation output
**When** its results are stored
**Then** scored judgments remain distinct from binary Hard Rule violations
**And** model scores are labeled routing telemetry rather than publication or literary-quality approval.

**Given** a candidate satisfying every applicable gate and Hard Rule
**When** routing runs
**Then** the candidate passes through unchanged and remains eligible for commitment
**And** it is not regenerated merely for stylistic preference.

**Given** a weak candidate or Hard Rule violation
**When** routing runs
**Then** only its Source Unit is routed to recovery with the triggering critique or rule
**And** unaffected Source Units and their candidates remain unchanged.

**Given** absent or internally inconsistent evaluation gates
**When** Run Translation attempts routing
**Then** the workflow blocks with an actionable method-validation error
**And** no candidate is guessed into passing, weak, recoverable, or failed state.

### Story 2.5: Recover Locally and Re-evaluate New Text

As a Translation Operator,
I want failed candidate weaknesses recovered locally under bounded rules,
So that the system can improve individual units without rerunning or disturbing the rest of the book.

**Requirements:** FR12, FR13.

**Acceptance Criteria:**

**Given** a Source Unit routed to recovery
**When** recovery generates a candidate
**Then** the request targets the recorded critique or Hard Rule failure and retains complete triggering and generation lineage
**And** it cannot modify Canonical Source HTML, another Source Unit, or an unrouted candidate.

**Given** a Source Unit that was not routed
**When** recovery executes for the wave
**Then** no Recovery Candidate or model request is created for that unit
**And** its previously passing candidate remains byte-identical.

**Given** a Recovery Candidate or any corrected or composed target text
**When** it is considered for commitment
**Then** the exact resulting value passes the full required evaluation and Hard Rule path
**And** evaluated fragments cannot be combined to bypass evaluation of the composed result.

**Given** recovery attempts
**When** candidate, retry, token, elapsed-time, or cost ceilings are reached
**Then** no further model call is dispatched for that logical operation
**And** the Source Unit receives an explicit exhausted outcome with the applicable ceiling and next action.

**Given** an interrupted recoverable invocation
**When** execution resumes
**Then** it follows the durable invocation receipts and idempotency rules from Story 2.2
**And** it neither duplicates a potentially completed provider call nor loses dispatched-attempt accounting.

### Story 2.6: Commit Machine Finals and Preserve Honest Failure

As a Translation Operator,
I want each successful unit committed with full lineage and each unsuccessful unit retained honestly,
So that a run never hides failure or mistakes unevaluated text for a finished translation.

**Requirements:** FR14, FR15.

**Acceptance Criteria:**

**Given** one or more eligible evaluated candidates for a Source Unit
**When** commitment runs
**Then** it selects exactly one target value under the frozen commitment gates and records the selection rationale
**And** after recovery the rationale explains how the selected candidate addresses the triggering weakness.

**Given** a selected candidate
**When** its Machine Final is created
**Then** the committed text and Inline Binding Map are copied verbatim and become immutable
**And** scores, critiques, rationale, provenance, and source-owned markup remain separate referenced artifacts.

**Given** a Literal Anchor, an unevaluated value, or a candidate violating a required gate
**When** commitment evaluates eligibility
**Then** it rejects that value
**And** deterministic serialization cannot rewrite or normalize candidate language to make it eligible.

**Given** no candidate satisfies the Translation Method after bounded recovery
**When** the unit reaches terminal state
**Then** it becomes an explicit Failed Unit recording attempted stages, findings, ceilings, and actionable next steps
**And** no failing candidate or Literal Anchor is promoted.

**Given** any unresolved Required Failed Unit
**When** run completeness is calculated
**Then** the run remains translation-incomplete and cannot claim an eligible complete Translation Draft
**And** later Human Edits may support editorial salvage but cannot mint or replace a Machine Final.

### Story 2.7: Orchestrate a Complete Live Translation Run

As a Translation Operator,
I want the live stages executed automatically through explicit terminal outcomes,
So that a confirmed source becomes an attributed complete draft or an honestly incomplete diagnosable run.

**Requirements:** FR3, FR8-FR15, FR20, FR29, FR30.

**Acceptance Criteria:**

**Given** a confirmed Prepare Package with compatible Preparation Policy, Translation Method, and Context Policy digests
**When** the Run Translation entrypoint starts in live mode
**Then** it validates the frozen Run Snapshot and automatically sequences context, generation, evaluation, routing, recovery, and commitment without per-unit approval
**And** no runtime credential or scheduler setting changes frozen run truth.

**Given** multiple Source Units
**When** the run schedules work
**Then** it executes the frozen wave and concurrency plan while preserving canonical Source Unit order in artifacts
**And** provider latency cannot change Context Bundles, routing rules, or commitment eligibility.

**Given** an interruption at any live stage
**When** the run resumes
**Then** it verifies the manifest and receipt chain, reuses compatible completed artifacts, and reconciles live invocations according to their durable receipt state
**And** it appends attempts rather than rewriting history or repeating ambiguous calls.

**Given** every Required Source Unit reaches one Machine Final
**When** live orchestration finishes
**Then** translation completeness becomes complete and Assemble-and-Validate can consume the resulting Unit Manifest
**And** the final Translation Run Summary preserves independent processing, completeness, compliance, review, and publication states.

**Given** one or more Failed Units or blocked operations
**When** live orchestration reaches terminal state
**Then** it emits all available manifests, provenance, receipts, and actionable diagnostics while remaining incomplete or blocked
**And** successful execution of other units is never represented as complete-draft or quality approval.

## Epic 3: Non-destructive Editorial Review

Enable an Editor to inspect, revise, and export a completed draft without altering source artifacts or obscuring editorial changes.

### Story 3.1: Inspect an Artifact-first Review Package

As a Literary Editor,
I want each translated unit displayed with its complete machine provenance,
So that I can understand the source, proposed alternatives, evaluation history, and final decision before editing.

**Requirements:** FR21.

**Acceptance Criteria:**

**Given** a complete eligible Translation Draft and its provenance artifacts
**When** Review Translation creates a Review Package
**Then** every Source Unit can be retrieved by stable identity with its source value, Machine Final, proposals, evaluations, recovery history, and selection rationale
**And** the package binds the exact draft, manifest, Run Snapshot, and projection-map digests.

**Given** missing required provenance for any Machine Final
**When** the Review Package is validated
**Then** it emits a compliance finding and blocks a claim of complete attribution
**And** it does not fabricate or infer the missing history.

**Given** a processing-complete but translation-incomplete run
**When** Review Translation is invoked
**Then** it returns a typed `review-blocked` result suitable for operator diagnosis
**And** it does not open literary review or reviewed export.

**Given** a valid Review Package
**When** an editor inspects it
**Then** the Skill Workflow renders an artifact-first human-readable view from canonical machine data
**And** no dedicated graphical application or independent mutable view state is required.

### Story 3.2: Record Non-destructive Edits and Literary Findings

As a Literary Editor,
I want to record unit edits, review decisions, and book-level literary findings separately from machine output,
So that editorial judgment is measurable without erasing the translation system's provenance.

**Requirements:** FR22, FR23.

**Acceptance Criteria:**

**Given** a Source Unit in a valid Review Package
**When** an editor records a Human Edit
**Then** the edit is stored as a new immutable overlay keyed to Source Unit and run identity
**And** the Machine Final and historical manifest remain byte-identical and separately retrievable.

**Given** an editor reviews a unit
**When** review metadata is recorded
**Then** review state, issue severity, timing, edit magnitude, and export selection are stored in versioned machine-readable artifacts
**And** retries append new history rather than overwriting prior editorial records.

**Given** concerns about voice, character consistency, recurring imagery, or continuity
**When** the editor records a book-level finding
**Then** it is keyed to the Translation Run with its evidence and disposition
**And** it is never represented as a unit score or deterministic-validation result.

**Given** deterministic validation and human review statuses
**When** either changes
**Then** the two status dimensions remain independent
**And** a compliance-clean draft cannot imply human approval, while an editorial edit cannot erase a blocking deterministic finding.

### Story 3.3: Validate and Export Reviewed Values

As a Literary Editor,
I want reviewed selections validated and exported with their origins disclosed,
So that the resulting publication draft applies my edits consistently without obscuring machine-authored text.

**Requirements:** FR22, FR23.

**Acceptance Criteria:**

**Given** a reviewed Source Unit
**When** an export value is selected
**Then** the selection explicitly references either the immutable Machine Final or a Human Edit digest
**And** the Review Package identifies the origin of every exported value.

**Given** a canonical unit with multiple Projection Map members
**When** reviewed export runs
**Then** it applies the selected value to every member under the declared transformation rule
**And** records both the selected-value and Projection Map digests.

**Given** incomplete selections, invalid overlays, unresolved review blockers, or a mismatched draft or manifest
**When** export validation runs
**Then** it returns a typed `review-blocked` result with actionable findings
**And** it emits no reviewed export that claims completion.

**Given** a valid completed review
**When** export finishes
**Then** it emits the reviewed HTML projection and canonical review/export artifacts with per-unit origin, review state, severity, timing, and book-level findings
**And** Machine Finals, Human Edits, and prior manifests remain unchanged.

## Epic 4: Reproducible Comparison and Evidence

Enable the team to compare translation methods and produce reproducible evidence about translation quality and workflow usefulness.

This epic is intentionally deferred. In accordance with the approved phase boundary, comparison and pilot-evidence stories remain unnumbered and are not implementation-ready in this artifact.

## Deferred Requirements Register

The following PRD requirements are preserved for traceability but are outside the Epic 1–3 implementation-ready scope validated by this artifact. They remain unnumbered and must pass a future epic-and-story workflow before implementation.

### Epic 4 Candidate Requirements: Reproducible Comparison and Evidence

FR24: The suite must preserve sufficient frozen identity and configuration to reproduce deterministic stages and identify unavailable provider/model dependencies.

FR25: Compare Translation Runs must disclose material configuration differences, reject non-equivalent ranking, and report compatible recovery, validation, and editorial metrics.

FR26: Before making pilot or release-qualification claims, an approved Pilot Profile must define the language pair, representative public-domain corpus, applicable Preparation Policy, and measurable qualification budgets.

FR27: Before claiming reduced editing burden, the Product Owner must freeze a Baseline Method and reproducible Editor Evaluation Protocol covering reviewer qualifications, clocks, severity, assignment, sample design, exclusions, and analysis.
