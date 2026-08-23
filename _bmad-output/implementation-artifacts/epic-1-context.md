# Epic 1 Context: Deterministic Translation Foundation

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Deliver the fixture-mode, deterministic foundation that lets a Translation Operator prepare a Canonical Source Package, produce stable Source Units, assemble a structurally faithful draft, validate it independently, and resume safely after interruption. This establishes machine-truth artifacts and explicit outcomes before any live model calls, so later translation work cannot weaken document integrity, provenance, or reproducibility.

## Stories

- Story 1.1: Bootstrap the i18n Package and Shared Kernel Contracts
- Story 1.2: Implement Durable Artifact State and Recovery
- Story 1.3: Prepare Stable Source Units
- Story 1.4: Preserve Inline Structure and Assemble Drafts
- Story 1.5: Validate Drafts and Emit Machine-Truth Reports
- Story 1.6: Expose Fixture-Mode Workflows and Orchestration

## Requirements & Constraints

- Workflows must publish declared, versioned artifact contracts with inputs, outputs, preconditions, accepted versions, confirmation needs, retry safety, terminal states, and failure behavior. Invalid, stale, missing, or incompatible artifacts must stop processing before feature logic and return typed, actionable errors.
- The foundation runs in explicit fixture mode only. It uses deterministic structural fixture values through the same artifact contracts intended for live mode, and must never resolve or call a live Model Gateway.
- Preparation accepts an immutable Canonical Source Package that binds source HTML, converter identity and summary, and ownership/projection profiles. Converter omissions affecting book-owned content block preparation.
- Prepare alone classifies locations as Required, Excluded, or Unsupported; it owns segmentation, ordering, typed locators, and projection groups. Unsupported unresolved content or an empty Required set blocks confirmation; Excluded book-owned content must round-trip unchanged.
- Source Unit identity must be stable and derived from source digest, typed DOM locator, segmentation-profile version, and segment ordinal. A source-text-digest mismatch is terminal; downstream stages must not resegment or silently reuse identities.
- Confirmed terminology and literary-style rules must resolve to explicit Source Unit sets and become immutable inputs. A signed Prepare Package and separate operator confirmation are required before orchestration advances.
- Assembly must clone source HTML and replace only mapped Required values. It must preserve structure, order, anchors, footnotes, non-translatable content, and declared duplicate projections; model output may not author HTML or DOM structure.
- Validation is read-only and is the sole authority for Translation Draft eligibility. It must block on unresolved structural, binding, terminology, residual-language, locale/directionality, or accessibility failures, and preserve separate processing, completeness, compliance, review, and publication states.
- Deterministic stages must emit byte-equivalent canonical artifacts for identical frozen inputs and component versions, or explicitly report nondeterminism. Partial or unverified work must never appear complete.

## Technical Decisions

- Implement exclusively under `src/i18n-pipeline` as one Python package: Python 3.14.4, Pydantic 2.13.4, lxml 6.1.2, and uv 0.11.19 with a committed lockfile. Boundary models are strict, frozen, and forbid unknown fields; no application or web framework is introduced.
- Use artifact-centric pipes and filters. The shared `kernel` exclusively owns schemas, compatibility, stable identities, lifecycle legality, and canonical serialization; workflows own only their own stage behavior and exchange immutable versioned artifacts by digest.
- Canonical JSON uses UTF-8/LF, sorted keys, compact separators, integer versions/counts, and decimal strings for non-integral scores. Reject floats, NaN, duplicate or unknown fields, and implicit coercion. Keep timestamps, paths, attempts, and execution metadata in linked immutable receipts, not content objects.
- Persist immutable SHA-256-addressed objects. Publish manifest successors with predecessor-digest compare-and-swap under an exclusive run lock; deterministically rebase disjoint unit advances in Source Unit order and reject overlaps. Resume only from verified receipt and manifest chains; retries append history.
- Use the lxml HTML adapter with networking and external entities disabled. Emit typed locators and structural fingerprints, clone before mutation, and limit mutation to mapped text/tail slots and declared metadata projections.
- Represent source-owned inline structure with exact protected ASCII tokens and a separate Inline Binding Map. Loss, duplication, invention, crossing, illegal relocation, or malformed bindings are blocking; assembly rebinds each valid token exactly once.
- Keep assembly and validation as separate deterministic filters. Emit canonical Unit Manifest, Assembly Report, Validation Report, and Translation Run Summary; human-readable files are projections rather than independent state.
- Entrypoints are thin, independently invocable adapters around the package. MVP uses no daemon, queue, service, or database; state and errors remain observable through stable identities, status vectors, receipts, and findings.

## Cross-Story Dependencies

- Story 1.1 establishes the reproducible package, kernel contracts, canonical serialization, identities, and lifecycle rules used by every later story.
- Story 1.2 supplies the artifact ledger, atomic manifest publication, receipts, locking, and recovery required by preparation, assembly, validation, and orchestration.
- Story 1.3 creates the frozen manifest, eligibility decisions, locators, projection maps, binding maps, and confirmed preparation inputs consumed by Stories 1.4–1.6.
- Story 1.4 produces the candidate draft and Assembly Report that Story 1.5 validates. Story 1.6 composes the completed Prepare and Assemble-and-Validate workflows, reusing their artifact handoffs and recovery guarantees.
