# i18n workflow — implementation spec units

This document divides the EPUB-to-translation workflow into implementation units that can be specified and built separately. It is a roadmap for future specs, not an implementation specification itself.

## Workflow overview

```text
Existing EPUB → HTML conversion
  ↓
PRE-RUN PREPARATION
1. Source document boundary
  ↓
2. Translation-unit extraction
  ↓
3. Translation manifest and ordering
  ↓
4. Terminology sheet and unit mapping
  ↓
5. Style sheet and run snapshot
  ↓
AUTOMATIC TRANSLATION RUN
6. Translation batch and context builder
  ↓
7. Translation proposal
  ↓
8. Evaluation and recovery routing
  ↓
9. Final-unit commitment and provenance
  ↓
10. Translated HTML reassembly
  ↓
11. Structural and terminology validation
  ↓
POST-RUN EDITORIAL WORK
12. Human review and quality measurement
```

These are separate implementation-spec units, not twelve equivalent runtime stages. Units 1–5 prepare and freeze the question the run will answer. Units 6–11 form the automatic trajectory. Unit 12 begins only after a complete, attributable draft exists.

## Existing prerequisite: EPUB → canonical HTML

The existing converter produces the canonical source HTML. Translation must not modify this file in place. It remains frozen for the translation run and provides document structure, chapter order, IDs, links, footnotes, and visible source text.

This component already exists and is not part of the new i18n implementation, except where it may later need to expose additional stable identifiers.

## 1. Source document boundary

Define which parts of the canonical HTML belong to the book and which parts are reader presentation or generated chrome.

The future spec should cover:

- Selecting translatable book content.
- Excluding CSS, JavaScript, controls, reader labels, generated statistics, and duplicated navigation text.
- Distinguishing book-owned text from reader chrome and metadata projections.
- Translating titles, authorship metadata, and navigation labels once, then projecting their committed values into repeated `data-slot` or TOC locations.
- Identifying structural elements that must survive unchanged.
- Detecting unsupported or ambiguous source markup.

**Produces:** a deterministic view of the source DOM that later stages may inspect.

## 2. Translation-unit extraction

Extract visible language into traceable units without losing its structural location.

The future spec should cover:

- Semantic block types: headings, paragraphs, list items, blockquotes, captions, table cells, footnotes, and verse lines.
- Rules for splitting oversized prose blocks at sentence boundaries without treating verse lines as prose sentences.
- Explicit behavior for poetry, dialogue fragments, abbreviations, and other text for which sentence detection is ambiguous.
- Inline markup and protected structural placeholders.
- Context retained for each unit.
- Stable unit-ID generation.

**Produces:** an ordered collection of source translation units.

## 3. Translation manifest and ordering

Define the JSON-based, machine-readable source of truth and durable working state for the translation run.

The future spec should cover:

- Unit identity and parent block identity.
- Chapter, block, and segment ordering.
- Source text and structural metadata.
- A stable placement locator attached to the cloned source DOM rather than reconstructed later from fragile CSS or XPath queries.
- Locator uniqueness, resolvability, and behavior when the source DOM does not match the frozen manifest.
- Source hashes and manifest versioning.
- Representation of pending, translated, reviewed, and failed states.
- Storage for proposals, evaluations, recovery candidates, committed finals, rationale, and later human edits.
- Atomic and resumable manifest updates.

**Produces:** a translation manifest from which order and placement can always be reconstructed.

## 4. Terminology sheet and unit mapping

Create and maintain book-wide terminology, then map relevant entries to individual units. Terminology confirmation is pre-run editorial work, not part of the automatic translation trajectory.

The future spec should cover:

- Terminology candidates extracted from the source.
- Confirmed source and target forms.
- `locked`, `preferred`, and `guidance` rule types.
- Names, inflections, aliases, capitalization, and contextual exceptions.
- Mapping terms to the unit IDs in which they appear.
- Deterministic checks for locked terms.

**Produces:** a global terminology sheet and per-unit terminology references.

## 5. Style sheet and run snapshot

Capture book-wide literary guidance and freeze all inputs needed for a reproducible translation run.

The future spec should cover:

- Narrative tense, register, dialogue conventions, address forms, and punctuation.
- Character voices and recurring imagery.
- Target-language-specific guidance.
- Frozen versions or hashes of source HTML, manifest, terminology, style, method configuration, and prompts.
- Rules for starting a new run when frozen inputs change.

**Produces:** an immutable run snapshot.

## 6. Translation batch and context builder

Construct focused JSON requests for translation stages from the durable manifest. The LLM should receive only the units and context needed for the current operation rather than the entire book manifest.

The future spec should cover:

- Selecting units by status and processing stage.
- Supplying neighboring units, chapter context, and parent-block context.
- Defining whether each stage receives source neighbors, previously committed target neighbors, or both.
- Preventing processing order or concurrency from silently changing the context policy and therefore the translation result.
- Including only applicable terminology and style guidance.
- Token or size limits and deterministic batch boundaries.
- Structured request and response contracts keyed by stable unit ID.
- Validating model responses before applying them to the manifest.
- Retry and partial-failure behavior without losing completed work.

**Produces:** bounded JSON request batches and validated response updates for the manifest.

## 7. Translation proposal

Generate the initial renderings for each unit under the frozen run context.

The future spec should cover:

- Literal anchor and idiomatic candidate outputs.
- Context windows supplied with a unit.
- Applicable terminology and style guidance.
- Structured response validation.
- Retry and failure behavior without losing unit identity.

**Produces:** attributable initial candidates for every eligible unit.

## 8. Evaluation and recovery routing

Evaluate the idiomatic candidate and decide whether the unit passes through or needs additional work.

The future spec should cover:

- Faithfulness and naturalness evaluation.
- Critique representation.
- Routing thresholds and hard terminology violations.
- Conditional generation of recovery candidates.
- The distinction between routing telemetry and literary approval.

**Produces:** a routing decision and, where needed, additional candidates.

## 9. Final-unit commitment and provenance

Commit a final translation for each successful unit while retaining the complete decision trail and representing unsuccessful units explicitly.

The future spec should cover:

- Pass-through behavior for successful units.
- Preventing taste-based rewriting of gate-passing units; a changed pass-through final must follow an explicit correction route and be evaluated again.
- Deliberate selection or composition for rescued units.
- Re-evaluating any newly composed rescue final that did not itself pass evaluation, or limiting composition to evaluated spans joined through a recorded recipe.
- Final rationale.
- Candidate, score, critique, route, and final attribution.
- Separation of machine output from later human edits.
- Representing failed units without a committed final; the literal anchor must never be silently promoted as a fallback.

**Produces:** one committed final per successful unit, explicit failure states for unsuccessful units, and provenance for every attempted unit. A run with unresolved failures is incomplete.

## 10. Translated HTML reassembly

Apply committed finals to a copy of the canonical document without asking an LLM to regenerate the book HTML.

The future spec should cover:

- Locating every source unit in the cloned DOM.
- Reconstructing blocks split into multiple segments.
- Restoring inline structure and translated emphasis placement.
- Preserving IDs, anchors, footnotes, order, and non-translatable content.
- Writing a new translated reader HTML file atomically.

**Produces:** a translated HTML reader and an assembly report.

## 11. Structural and terminology validation

Check deterministically that the translated document is complete and structurally sound.

The future spec should cover:

- Every required unit has exactly one committed final before the run may be considered complete.
- No missing, duplicated, or unexpected units.
- Explicit failure when any required unit has no committed final.
- Anchor and footnote integrity.
- Structural-token and inline-placeholder balance.
- Locked-terminology compliance.
- Residual source-language detection and explicit limitations.
- Clear separation of run completion from compliance success.

**Produces:** a machine-readable validation report with blocking errors and warnings.

## 12. Human review and quality measurement

Provide the complete attributed draft for human editing and measure the pipeline by the burden of that edit.

The future spec should cover:

- Unit-level editing without losing the machine final.
- Recording edit time and edit magnitude.
- Severity classification for remaining translation errors.
- Review status and export behavior.
- Comparison of runs using rescue rate, compliance findings, and human editing burden.
- Book-level review of voice, character consistency, and recurring imagery that unit-level scores cannot certify.
- Whether a later optional continuity audit should flag book-level drift or whether this residue remains solely a human-edit quality signal.

**Produces:** a reviewed translation, an audit trail, and honest quality signals.

## Recommended specification order

The units should not all be specified at once. A practical order is:

1. Source document boundary.
2. Translation-unit extraction.
3. Translation manifest and ordering.
4. Translated HTML reassembly.
5. Structural validation.
6. Terminology sheet and mapping.
7. Style sheet and run snapshot.
8. Translation batch and context builder.
9. Proposal, evaluation, recovery, and commitment.
10. Human review and quality measurement.

Specifying extraction, identity, reassembly, and validation first establishes the preservation contract before model behavior is introduced.

## First implementation proof

Before implementing model-driven stages, build a deterministic dummy round-trip over the real reader HTML:

1. Select book-owned source content.
2. Extract units and assign stable IDs and locators.
3. Create a manifest.
4. Supply dummy finals, initially identical to the source text.
5. Reassemble a cloned document.
6. Verify unit completeness, locator resolution, structure, order, anchors, footnotes, chrome projections, and repeat-output determinism.

This proves units 1–3 and 10–11 as one preservation loop. Model stages should not begin until that loop passes, because fluent generated text can conceal extraction or reassembly defects.

## Cross-cutting invariants

Every later implementation spec should respect these invariants:

- The canonical source HTML is immutable during a run.
- Every translation unit has a stable identity and deterministic position.
- Every locator resolves exactly once against the frozen source DOM or fails explicitly.
- Structure is preserved independently of generated language.
- The JSON manifest is the durable working state and machine source of truth.
- LLM requests are bounded views derived from the manifest, never an independent document state.
- LLM outputs are keyed by unit ID and never trusted to reorder the document.
- Repeated reader chrome is projected from one translated value rather than translated as duplicate units.
- Terminology and style inputs are frozen for a run.
- Every committed final retains its decision history.
- Newly composed or corrected text cannot bypass evaluation.
- Failed units remain failed; no candidate is silently promoted to make a run appear complete.
- Reassembly and hard-rule checks are deterministic.
- A completed run is not automatically a compliant or publication-ready translation.
- Unit-level evaluation does not certify book-level voice or continuity.
