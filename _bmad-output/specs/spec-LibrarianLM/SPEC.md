---
id: SPEC-LibrarianLM
companions:
  - ../../planning-artifacts/prds/prd-LibrarianLM-2026-08-23/prd.md
  - ../../planning-artifacts/prds/prd-LibrarianLM-2026-08-23/addendum.md
  - ../../planning-artifacts/architecture/architecture-LibrarianLM-2026-08-23/ARCHITECTURE-SPINE.md
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# LibrarianLM Literary Translation Workflow Suite

## Why

Literary translation needs more than one opaque model call: operators need reproducible execution, editors need visible provenance, and method maintainers need honest comparisons. LibrarianLM will produce useful attributed drafts through staged preparation, generation, evaluation, local recovery, deterministic assembly, independent validation, and non-destructive human review—without presenting fluency or model confidence as publication readiness.

## Capabilities

- **CAP-1 — Prepare a translation run**
  - **intent:** An operator can classify book-owned content, create stable Source Units, confirm editorial guidance, and freeze a signed Prepare Package.
  - **success:** Identical eligible inputs produce the same `ready-for-confirmation` package, while unresolved unsupported content or invalid gates produce a typed `blocked` report.

- **CAP-2 — Run attributed translation**
  - **intent:** The system can generate contrasting proposals, evaluate them, route only weak units through bounded local recovery, and commit eligible Machine Finals.
  - **success:** Every required Source Unit ends with exactly one fully attributed Machine Final or one explicit Failed Unit; no ineligible or unevaluated value is promoted.

- **CAP-3 — Assemble and validate**
  - **intent:** The system can deterministically rebind committed values into Canonical Source HTML and independently validate the result.
  - **success:** A Translation Draft is eligible only when placement, structure, language, terminology, directionality, accessibility, and completeness pass with no blocking finding.

- **CAP-4 — Review without erasing provenance**
  - **intent:** A literary editor can inspect the complete machine history, record Human Edits and book-level findings, and export reviewed content.
  - **success:** Every selected export value remains linked to its immutable Machine Final, evaluation path, Source Unit, review state, and projection map.

- **CAP-5 — Compare runs and qualify the pilot**
  - **intent:** A method maintainer can reject non-equivalent comparisons and measure recovery, compliance, edit burden, and usefulness under frozen methods and protocols.
  - **success:** Comparison and usefulness reports disclose all material configuration differences, evidence limits, recovery outcomes, and qualified-editor measurements without ranking non-equivalent runs.

- **CAP-6 — Orchestrate composable workflows**
  - **intent:** An operator can confirm one valid package and let independently invocable workflows execute automatically to an explicit terminal state.
  - **success:** Artifact handoffs are resumable and version-compatible; every failure is actionable; orchestration depends on no workflow's private prompts, provider adapter, or storage internals.

## Constraints

- Canonical Source HTML, Machine Finals, artifact history, and adopted architecture `AD` identifiers are immutable within their declared scope; changes create new versioned artifacts.
- Models author target-language values only. Structure, markup, identifiers, order, placement, and projections remain deterministic system-owned data.
- Workflow boundaries use versioned immutable artifacts and explicit terminal outcomes; hidden shared mutable state and silent completeness fallbacks are prohibited.
- Processing completion, translation completeness, deterministic compliance, human review, and publication readiness are orthogonal states.
- The automatic trajectory has no per-unit human approval after package confirmation; literary judgment occurs afterward through CAP-4.
- Deterministic-foundation work may proceed now. Live generation, human usefulness evaluation, and release certification remain blocked by the PRD and architecture entry gates.
- All i18n pipeline code lives under `src/i18n-pipeline` and conforms to every decision in the adopted architecture spine.

## Non-goals

- Autonomous publication readiness or replacement of qualified literary judgment.
- Literal Anchors as Machine Finals, second full-book recovery, or unevaluated composed text.
- Translation of reader chrome or model-authored document structure.
- A general translation-management UI, public multilingual publishing or SEO, EPUB/XLIFF export, or automated book-level literary certification in MVP.

## Success signal

- Every required Source Unit has exactly one valid placement and either one attributed Machine Final or one explicit Failed Unit; complete drafts have 100% provenance and zero blocking deterministic findings.
- Identical frozen inputs and deterministic component versions produce zero unexplained identity, placement, artifact, or validation differences.
- Under the frozen Pilot Profile and evaluation protocol, qualified-editor median review-and-edit time is at least 30% below the single-pass baseline with no increase in critical residual errors; recovery yield and editorial burden are reported without optimizing away honest failure.

## Open Questions

- Which language pair, representative public-domain corpus, and qualification budgets will form the first Pilot Profile?
- Which supported-content dispositions and residual-language tolerances will form the first live Preparation Policy?
- Which providers/models, prompts, evaluator scales, gates, recovery recipe, and retry/token/time/cost ceilings will form the first Translation Method?
- What source/target neighbor windows, wave sizes, truncation rules, and failed-predecessor behavior will the first Context Policy freeze within `AD-5`?
- Which qualified-editor sample, assignment/blinding design, gold subset, severity rubric, timing protocol, and Baseline Method will form the first Editor Evaluation Protocol?
