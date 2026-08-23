# Input Reconciliation: `i18n-implementation-spec-units.md`

## Scope

- **Input:** `docs/brief-i18n/i18n-implementation-spec-units.md`
- **Compared with:** `prd.md` and `addendum.md` in this workspace
- **Purpose:** Determine whether the input's product intent is represented in the PRD and whether implementation-specific depth has been preserved appropriately in the addendum rather than promoted into product requirements.

## Verdict

The draft preserves the source's central product contract very well: immutable canonical HTML, stable and ordered translation units, a durable manifest, frozen terminology/style/method inputs, bounded attributed model work, evaluation-gated recovery, explicit failure, deterministic reassembly and validation, non-destructive human review, and honest separation of completion from compliance and publication readiness. It also correctly elevates the user's clarification that the deliverable is a suite of composable Skill Workflows.

There are four material reconciliation findings. Two are product-level gaps or conflicts: source-derived terminology candidate generation is absent, and the PRD reopens whether incomplete runs may enter human review even though the source explicitly places post-run editorial work after a complete attributable draft. Two belong downstream and should be preserved in the addendum/architecture: the deterministic dummy round-trip as the required first implementation proof, and a more explicit preservation contract for split-block reassembly and inline emphasis placement. A smaller metadata-boundary detail is also underrepresented.

## Material Gaps and Distortions

### 1. Terminology candidate extraction is omitted from the product requirements

**Source idea:** Unit 4 says the workflow should create and maintain book-wide terminology, including “terminology candidates extracted from the source,” then confirm source/target forms and map applicable entries to unit IDs.

**Current representation:** PRD FR-6 lets the Translation Operator provide and confirm a Terminology Sheet and requires rule-to-unit association. It does not require the suite to extract or propose terminology candidates from the source. The addendum discusses terminology mapping and glossary versioning but does not restore candidate extraction as a capability.

**Assessment:** **Omitted product requirement.** The source describes a user-visible preparation capability, not merely a choice of algorithm. The PRD currently changes the workflow from “create candidates, then confirm” to “operator provides and confirms.”

**Recommended destination:** PRD, under FR-6 or a neighboring requirement. Architecture should own extraction technique, ranking, and data representation.

### 2. Human review entry criteria conflict with the source's phase boundary

**Source idea:** Unit 12 begins only after a complete, attributable draft exists. Units 6–11 form the automatic trajectory, and unresolved failures make the run incomplete.

**Current representation:** The journey and FRs generally align: UJ-2 begins with a completed Translation Draft, FR-15 forbids incomplete runs from claiming a complete draft, and FR-19 distinguishes states. However, Open Question 3 asks whether a processing-complete but translation-incomplete run may enter Human Review.

**Assessment:** **Distorted/undecided product requirement.** The open question weakens a categorical source boundary. Diagnostic inspection of Failed Units could be supported without calling that state post-run Human Review or allowing reviewed export.

**Recommended destination:** Resolve in the PRD. Preserve the source rule for formal editorial review unless the user explicitly overrides it; architecture may separately expose failure diagnostics.

### 3. The required deterministic dummy round-trip is missing

**Source idea:** Before model-driven stages, build and pass a deterministic identity round-trip over real reader HTML: select content, extract and identify units, build a manifest, supply source-identical dummy finals, reassemble a clone, and validate completeness, locator resolution, structure, order, anchors, footnotes, projections, and repeat-output determinism. Model stages should not begin until this preservation loop passes.

**Current representation:** The PRD captures the underlying preservation requirements in FR-4, FR-5, FR-16, FR-17, SM-1, and SM-4. Neither the PRD nor addendum preserves the explicit implementation gate or recommended sequencing.

**Assessment:** **Omitted implementation strategy, appropriately excluded from product FRs but not preserved downstream.** This is a high-value delivery constraint because fluent generated text can mask extraction and placement defects.

**Recommended destination:** Addendum and later architecture/implementation plan. Record it as the first implementation proof and a gate before enabling model-driven stages. The source's recommended specification order may accompany it as non-binding sequencing guidance.

### 4. Split-block and inline-emphasis reassembly are underrepresented

**Source idea:** Unit 10 explicitly requires reconstruction of blocks split into multiple segments and restoration of inline structure and translated emphasis placement.

**Current representation:** FR-16 requires replacing only mapped book-owned values while preserving document structure. FR-17 validates protected inline placeholders. The addendum delegates segmentation and protected-placeholder representation, but neither artifact explicitly states how split segments are rejoined or that translated emphasis placement must be restored correctly.

**Assessment:** **Underrepresented preservation behavior.** The product-level outcome is mostly implied, but this is an important acceptance edge for literary HTML. The specific reconstruction mechanism is architectural.

**Recommended destination:** Keep the PRD outcome-oriented (structure and inline semantics survive reassembly), and add the reconstruction/placement mechanics to the addendum or architecture.

### 5. Title, authorship metadata, and navigation projection are only partially represented

**Source idea:** Unit 1 calls for titles, authorship metadata, and navigation labels to be translated once and projected into repeated `data-slot` or TOC locations, while distinguishing book-owned metadata projections from reader chrome.

**Current representation:** FR-4 covers book-owned versus chrome selection and duplicated projections; FR-16 requires duplicate reader projections to originate from one translated value. The addendum mentions canonical projection mapping for titles and duplicated navigation. Authorship metadata is not named, and the distinction between translated book-owned navigation labels and excluded generated reader labels remains implicit.

**Assessment:** **Minor underrepresentation with potential boundary ambiguity.** The core single-source projection invariant is present, but the concrete metadata classes from the source could be lost during downstream interpretation.

**Recommended destination:** Addendum/architecture for projection mappings; PRD only if these metadata classes are required acceptance examples for MVP.

## Coverage by Source Unit

| Source unit | Coverage | Where represented | Notes |
|---|---|---|---|
| Existing prerequisite: canonical HTML | Strong | Vision; glossary; FR-4, FR-5, FR-7, FR-16; NFR-1; dependencies | Immutability and upstream boundary are explicit. Possible need for upstream stable-ID exposure is properly left to architecture/integration planning. |
| 1. Source document boundary | Strong with minor gap | FR-4; FR-16; Non-Goals; addendum §2 | Chrome exclusion, ambiguity findings, and single-value projection are present. Authorship metadata and navigation boundary examples are not fully preserved. |
| 2. Translation-unit extraction | Strong | FR-4, FR-5, FR-17; Open Question 6; addendum §2 | Semantic block support and stable identity are product requirements; detailed segmentation behavior is correctly delegated. Poetry/dialogue ambiguity remains an explicit open planning question. |
| 3. Manifest and ordering | Strong | Glossary; FR-2, FR-5, FR-7, FR-9, FR-19; NFR-2; addendum §2 | Durable truth, ordering, placement, versioning, provenance storage, and resumability are covered at the right levels. Exact schema and lifecycle enum are correctly architectural. |
| 4. Terminology and unit mapping | Partial | FR-6, FR-10, FR-18; addendum §§2–3 | Rule classes, applicability, freezing, and deterministic checks are present. Candidate extraction from source is missing. |
| 5. Style and run snapshot | Strong | FR-6, FR-7, FR-23; glossary; addendum §2 | Editorial concerns and material input freezing are clear. Hash/schema details are correctly downstream. |
| 6. Batch and context builder | Strong | FR-9; FR-2; NFR-2, NFR-7, NFR-10; Open Question 4; addendum §2 | Bounded manifest-derived context, concurrency invariance, attribution, validation, retry, and partial failure are adequately split between PRD and architecture. |
| 7. Translation proposal | Strong | FR-8; FR-9 | Literal and idiomatic outputs, stable identity, malformed-response failure, context, and guidance are represented. |
| 8. Evaluation and recovery routing | Strong | FR-10, FR-11; glossary; success/counter-metrics | Faithfulness, naturalness, hard-rule routing, critique, and the telemetry-versus-approval distinction are explicit. |
| 9. Commitment and provenance | Strong | FR-13–FR-15; FR-20–FR-21; NFR-1, NFR-4 | Passing text is protected, composed/corrected text cannot bypass evaluation, Machine Finals are immutable, and failures remain honest. |
| 10. HTML reassembly | Strong with edge gap | FR-16; FR-17; addendum §2 | Deterministic cloning and structural preservation are strong. Split-block reconstruction and translated emphasis placement need more explicit downstream preservation. |
| 11. Structural and terminology validation | Strong | FR-17–FR-19; SM-1, SM-4; addendum §2 | Coverage, locator uniqueness, anchors, footnotes, placeholders, locked terms, source residue, and distinct completion/compliance states are all present. Atomic-output mechanics are correctly delegated. |
| 12. Human review and quality | Strong except phase conflict | UJ-2; FR-20–FR-22; FR-24; SM-3, SM-5, SM-6 | Non-destructive edits, timing/magnitude/severity, provenance, comparison, and book-level review are covered. Open Question 3 conflicts with the source's complete-draft prerequisite. |
| Recommended specification order | Missing downstream | None | Not a product requirement; preserve as addendum/architecture sequencing guidance if still desired. |
| First implementation proof | Missing downstream | Requirements imply its checks, but no gate exists | Material implementation omission; should be explicitly retained before model work. |
| Cross-cutting invariants | Strong | Vision; FR-2, FR-5, FR-7, FR-9, FR-11, FR-13–FR-19; NFRs; guardrails | Nearly all invariants are stated directly and testably. |

## Ideas Correctly Delegated to the Addendum or Architecture

The following source detail does not need promotion into the PRD because the product outcome is already covered:

- DOM locator encoding, source hashes, manifest schema/versioning, lifecycle enum names, and source-mismatch algorithms.
- Sentence-boundary algorithms and special-case parsing for prose, poetry, dialogue, abbreviations, tables, captions, and footnotes.
- Inline-placeholder representation and deterministic verification mechanism.
- Batch sizing, context window construction, deterministic batch boundaries, structured response schemas, retry policy, and partial-failure mechanics.
- Provider/model adapters, prompts, numerical thresholds, evaluation configuration, and storage layout.
- Exact safe-composition recipe and whether a composed result is reevaluated wholesale.
- Atomic file-write mechanics and interruption recovery implementation.
- Residual-language detection technique and its false-positive/false-negative characterization.

The addendum already captures these topics adequately except for the dummy round-trip gate, specification/build order, and explicit split-block/emphasis restoration behavior identified above.

## Source Ideas Preserved Particularly Well

- The output is explicitly a **suite of composable Skill Workflows**, not merely a monolithic translation pipeline.
- The source HTML is immutable, while deterministic code—not an LLM—owns structure and placement.
- The Unit Manifest remains the durable machine truth, and model requests are bounded attributed views rather than competing document state.
- Passing units are not taste-rewritten; recovery is local and triggered by recorded weakness.
- Newly generated or composed text cannot bypass evaluation.
- Failed Units remain failed, and the Literal Anchor cannot be silently promoted.
- Processing completion, translation completeness, deterministic compliance, human review, and publication readiness remain separate states.
- Human Edits remain distinct from immutable Machine Finals, enabling honest edit-burden measurement.
- Unit-level scores do not claim book-level voice or continuity certification.

## Reconciliation Disposition

No edits were made to `prd.md` or `addendum.md`. Before finalization, the parent workflow should surface the two product-level items (terminology candidate extraction and human-review entry criteria) for resolution. The deterministic dummy round-trip and remaining preservation details should be retained as addendum/architecture guidance rather than expanding the PRD with implementation mechanics.
