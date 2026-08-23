# Updated Input Reconciliation: `i18n-implementation-spec-units.md`

## Scope

- **Input:** `docs/brief-i18n/i18n-implementation-spec-units.md`
- **Compared with:** the updated `prd.md` and `addendum.md` in this workspace
- **Purpose:** Recheck the source roadmap after the PRD update, with particular attention to development-readiness gates, Skill Workflow and artifact contracts, Source Unit eligibility, Context/Translation Method/Provider policies, the Inline Binding Map, retry and failure behavior, review interchange, and deterministic guarantees.

## Verdict

The update preserves nearly all of the source's product intent and closes the prior reconciliation findings. The PRD now makes terminology candidate generation explicit, limits formal literary review to complete drafts, requires a deterministic dummy round trip, specifies split-block reconstruction and inline-emphasis behavior, and covers single-source metadata projection. It also strengthens the source with versioned Skill Workflow contracts, explicit readiness gates, Required/Excluded/Unsupported eligibility states, frozen Provider/Translation Method/Context policies, bounded recovery, and a multi-axis Run Status Vector.

Four residual issues remain. All four are product-contract ambiguities rather than requests to choose schemas or algorithms. The source's other detailed choices—JSON/schema shape, locator and segmentation algorithms, retry mechanics, atomic-write technique, and Review Package serialization—are correctly delegated to architecture in the addendum.

## Material Gaps and Ambiguities

### 1. The deterministic round-trip is required for acceptance, but not clearly an entry gate before model-stage implementation

**Source requirement:** The first implementation proof must select content, extract stable units, create the manifest, reassemble source-identical dummy finals, and validate preservation. The source explicitly says model-driven stages should not begin until this loop passes.

**Updated representation:** FR-17 requires the proof before model-backed generation is "accepted for" a Canonical Source HTML class. The readiness matrix marks deterministic-foundation work ready and live generation blocked on the Pilot Profile, Provider Policy, Translation Method, Context Policy, and Prepare Package, but it does not name a successful FR-17 round trip as a live-generation entry gate.

**Assessment:** **Product/delivery gate remains weaker than the source.** "Accepted for" can be read as a later test or release condition, allowing model-stage implementation to begin before the preservation loop passes.

**Recommended disposition:** In the PRD readiness matrix or FR-17, state whether passing the applicable deterministic round-trip fixture suite is required before model-backed stages may be implemented, enabled, or merely accepted. To preserve the source exactly, make it an entry gate before model-driven implementation for that content class.

### 2. `Excluded Source Unit` permits omission while deterministic assembly says non-translatable content is preserved

**Source requirement:** Translation selects book-owned language while preserving document structure and non-translatable content. Reader chrome and duplicated projections are excluded from translation, but deterministic reassembly operates on a cloned source document rather than silently deleting excluded source material.

**Updated representation:** FR-16 says non-translatable content remains preserved. The glossary defines an Excluded Source Unit as content "retained or omitted according to the Pilot Profile," and FR-31 requires eligibility reasons but does not define which disposition is allowed for each excluded content class.

**Assessment:** **Internal product-contract ambiguity.** A Pilot Profile could authorize omission of book-owned excluded content in tension with FR-16 and the source preservation contract. Architecture cannot safely choose between retention and deletion.

**Recommended disposition:** Define exclusion disposition at product level: reader chrome is outside translation selection but remains governed by the Reader Artifact contract; excluded book-owned content is preserved unchanged unless an explicitly named product policy permits omission and declares the structural consequence. Keep DOM mechanics in architecture.

### 3. Inline Binding Map validation does not explicitly require one-to-one, exactly-once rebinding

**Source requirement:** Protected inline structure must survive independently of generated language, with restored translated emphasis placement and deterministic validation of structural tokens/placeholders.

**Updated representation:** The glossary defines the Inline Binding Map; FR-16 requires deterministic rebinding and preserves inline identity/order while permitting natural movement of emphasized words; FR-18 checks protected inline placeholders. The addendum says the PRD fixes "exactly-once deterministic rebinding," but the PRD never explicitly states that every expected binding must resolve exactly once and that missing, duplicated, or foreign bindings fail validation.

**Assessment:** **Under-specified product integrity rule.** Placeholder balance alone can pass while bindings are duplicated, swapped, or left unresolved. Physical placeholder and map serialization are architecture details, but the one-to-one outcome is a product acceptance rule.

**Recommended disposition:** Add a testable FR-18 consequence requiring every expected Inline Binding Map entry to resolve exactly once to its source-owned inline node, with missing, duplicated, unexpected, or unresolved bindings treated as blocking findings.

### 4. Validation findings lack the source's explicit blocking-error versus warning contract

**Source requirement:** Structural and terminology validation produces a machine-readable report with blocking errors and warnings, while keeping run completion separate from compliance success.

**Updated representation:** The Validation Report is machine-readable, multiple FRs define failures, limitations, and evidence, and FR-20 separates status dimensions. However, neither the glossary nor FR-18/FR-19 defines a severity/disposition vocabulary that distinguishes blocking findings from warnings or states how each affects deterministic-validation status and Translation Draft eligibility.

**Assessment:** **Omitted product-level report semantics.** The exact enum and serialization are architectural, but callers need a stable distinction between a blocker and a warning to interpret terminal states consistently.

**Recommended disposition:** Require every validation finding to carry at least a blocking/non-blocking disposition (or equivalent stable semantics), and define that only blocking findings prevent deterministic compliance or Translation Draft eligibility. Delegate field names and schema to architecture.

## Focus-Area Coverage

| Focus area | Coverage | Reconciliation note |
| --- | --- | --- |
| Development readiness | Strong with one sequencing gap | The matrix correctly blocks live transfer and model operation on frozen policy artifacts. It does not clearly make successful FR-17 proof an entry gate before model-stage implementation. |
| Skill Workflow contracts | Strong | Five invocable workflows have required inputs, success artifacts, non-success outcomes, versioning, preconditions, terminal states, retry safety, and actionable errors. This appropriately realizes the user's skill-based-workflow requirement. |
| Artifact contracts | Strong | The Prepare Package, Unit Manifest, Translation Draft, reports, Review Package, and comparison artifacts have stable product-level meanings. Physical schemas and storage remain correctly architectural. |
| Eligibility states | Strong with one disposition ambiguity | Required/Excluded/Unsupported states make preparation and completion decidable. The only gap is whether excluded book-owned material may be omitted despite the preservation rule. |
| Context Policy | Strong | Source/target neighbors, batching order, bounds, concurrency, truncation, and failed-predecessor behavior are frozen; unsatisfied dependencies block or fail rather than silently falling back. |
| Translation Method | Strong | Evaluation scales, gates, Hard Rules, recovery, retries, candidates, budgets, and terminal states are frozen and attributable. Numerical choices remain configuration, as they should. |
| Provider Policy | Strong extension | Authorization, rights, provider/model eligibility, training, retention, residency, transfer bounds/logging, and deletion are explicit gates before transfer. These add governance without distorting the source workflow. |
| Inline Binding Map | Strong concept, incomplete validation invariant | Deterministic source-owned markup rebinding and translated emphasis movement are captured, but exact one-to-one binding integrity is not stated testably in the PRD. |
| Retry and failure | Strong | Retries and resource ceilings are frozen, completed work is recoverable, Failed Units remain explicit, and no Literal Anchor or failing candidate is promoted. Mechanisms are correctly delegated. |
| Human review and interchange | Strong | Review begins only after a complete attributed draft; machine values remain immutable; edits, state, severity, timing, book-level findings, validation, and export are exposed through artifacts. The physical Review Package format is correctly an architecture/UX decision, not a missing product requirement. |
| Deterministic rules | Strong with two explicitness gaps | Stable identity/order, exactly-once unit placement, clone-based assembly, split-block order, projections, structural preservation, byte-equivalent deterministic artifacts, and source-of-nondeterminism reporting are covered. Inline exactly-once binding and validation severity semantics need tightening. |

## Source-Unit Coverage

| Source unit | Coverage | Updated disposition |
| --- | --- | --- |
| Canonical HTML prerequisite | Strong | Immutable upstream Reader Artifact boundary is explicit. |
| 1. Source document boundary | Strong with exclusion ambiguity | Book/chrome selection, unsupported findings, and title/metadata/navigation projection are covered; omission of excluded book-owned content needs clarification. |
| 2. Translation-unit extraction | Strong | Stable identity, deterministic placement, supported content classes, inline bindings, and structural fixtures are product requirements; segmentation algorithms remain architecture. |
| 3. Manifest and ordering | Strong | Durable machine truth, lifecycle state, placement, versioned artifact composition, atomic recovery outcome, and provenance are covered. JSON shape and enum design are architecture details. |
| 4. Terminology and mapping | Strong | Source-derived candidates, editorial confirmation, rule types, unit applicability, freezing, and deterministic locked-term validation are explicit. Inflection/alias data design is downstream detail. |
| 5. Style and Run Snapshot | Strong | Voice/register/tense/address/imagery, target-locale identity, methods, prompts through Translation Method, and material-change rerun behavior are represented. |
| 6. Batch and context builder | Strong | Bounded manifest-derived views, deterministic context policy, structured artifact boundaries, validation/failure, retries, and partial recovery are covered at the right levels. JSON request shape and batching algorithms are downstream. |
| 7. Translation proposal | Strong | Literal and idiomatic outputs, stable unit attribution, applicable constraints, malformed-output states, and Literal Anchor ineligibility are explicit. |
| 8. Evaluation and recovery routing | Strong | Faithfulness/naturalness, retained critique, hard-rule separation, frozen routing gates, and telemetry-versus-approval distinctions are explicit. |
| 9. Commitment and provenance | Strong | Passing candidates remain unchanged, corrected/composed text cannot bypass evaluation, rescue rationale is retained, finals are immutable, and failures remain honest. |
| 10. HTML reassembly | Strong with inline invariant gap | Clone-based deterministic assembly, split-block rejoin, projection mapping, anchors/footnotes/order, and translated emphasis movement are explicit. Exactly-once inline binding needs a testable rule. |
| 11. Structural and terminology validation | Strong with report-severity gap | Completeness, unit placement, locators, anchors, footnotes, placeholders, terminology, language residue, locale, and directionality are covered. Blocking-versus-warning semantics are not. |
| 12. Human review and quality | Strong | Complete-draft entry, provenance inspection, non-destructive edits, timing/magnitude/severity, book-level review, comparison, and honest quality metrics are covered. |
| Recommended specification order | Appropriately downstream | The PRD's readiness model and addendum delegate sequencing, though the model-stage entry gate should be tightened as finding 1. |
| First implementation proof | Present but weaker as a gate | FR-17 captures the proof contents; readiness wording does not fully preserve the source's "before model-driven stages begin" rule. |
| Cross-cutting invariants | Strong | All central invariants are preserved; the residual issues concern exclusion disposition, inline binding cardinality, and validation finding semantics. |

## Architecture Details Correctly Kept Out of the PRD

The following source material is implementation detail rather than a product gap, and the addendum preserves it adequately:

- JSON and other physical serialization choices for the Unit Manifest, requests/responses, Inline Binding Map, reports, and Review Package.
- DOM locator encoding, source hashing, source-mismatch detection, and canonical projection-map representation.
- Sentence/block segmentation algorithms and special handling for poetry, dialogue, abbreviations, tables, captions, and footnotes.
- Batch construction, token packing, context-window implementation, concurrency scheduling, retry mechanics, and partial-update mechanics under frozen product policies.
- Provider/model adapters, prompt bodies, numerical evaluation thresholds, and storage layout.
- Atomic file-write technique and interruption-recovery implementation.
- Residual-language detector implementation and false-positive/false-negative analysis.
- Review Package rendering technology and future graphical reviewer UX.

## Reconciliation Disposition

No edits were made to `prd.md` or `addendum.md`. The update faithfully incorporates the prior source-reconciliation fixes. Before finalization, the parent workflow should resolve the four remaining product-contract ambiguities above; architecture can proceed with the already-delegated schema, algorithm, storage, and transport choices once the applicable readiness gates are satisfied.
