# Addendum: Literary Translation Skill Workflow Suite

This addendum preserves implementation-oriented depth and external standards context that informs, but does not constrain, the product contract in `prd.md`.

## 1. Implementation Topics Delegated to Architecture

- Stable Source Unit identity and DOM locator scheme, including source hashes and mismatch behavior.
- Unit Manifest schema, versioning, lifecycle enums, and atomic/resumable updates.
- Sentence and block segmentation algorithms for prose, poetry, dialogue, abbreviations, tables, captions, and footnotes.
- Physical serialization of the Inline Binding Map and protected placeholders; the PRD fixes exactly-once deterministic rebinding and prohibits model-authored wrappers or identifiers.
- Batch execution, context-window, deterministic-boundary, retry, and partial-failure mechanisms under the ceilings frozen by the Translation Method and Context Policy; later Pilot Profiles define qualification budgets rather than live-run controls.
- Provider/model adapters, structured request/response schemas, prompts, numerical evaluation thresholds, and Hard Rule values within the categories fixed by the PRD.
- Storage layout for proposals, critiques, scores, Recovery Candidates, Machine Finals, rationale, and Human Edits.
- A future safe-composition design, if pursued after MVP; MVP disables composition unless the committed result is evaluated under an approved Translation Method version.
- Atomic file writes and interruption recovery.
- Residual source-language detection and its false-positive/false-negative reporting.
- Canonical projection mapping for titles and duplicated navigation.

## 2. External Standards and Comparable Practices

- Use canonical BCP 47 / Unicode locale identifiers for Target Locale, retaining script and region where relevant: [Unicode LDML](https://unicode.org/reports/tr35/).
- Make document and passage language programmatically determinable and apply explicit directionality: [WCAG 2.2](https://www.w3.org/TR/wcag/) and [W3C language declarations](https://www.w3.org/International/questions/qa-html-language-declarations.html).
- EPUB package and resource language semantics inform round-trip compatibility even though EPUB export is out of MVP: [EPUB 3.3](https://www.w3.org/TR/epub-33/) and [EPUB Accessibility Techniques](https://www.w3.org/TR/epub-a11y-tech-111/).
- W3C ITS 2.0 and OASIS XLIFF demonstrate interoperable representations for context, terminology, provenance, validation, and quality issues: [ITS 2.0 requirements](https://www.w3.org/TR/its2req/) and [XLIFF 2.1](https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html).
- Glossary resources need immutable source files or explicit versioning; provider-side resources may not supply rollback: [Google Cloud Translation glossary guidance](https://docs.cloud.google.com/translate/docs/advanced/glossary).

## 3. Options and Deferred Rationale

### Dedicated review UI versus artifact-first review

The MVP Review Translation Skill renders and updates a Review Package through structured artifacts and a human-readable view. A graphical review workspace remains valuable downstream; adding it now would force decisions about UX, collaboration, permissions, and history that the briefs do not support into the workflow contract.

### Document finality versus development readiness

PRD lifecycle status and development readiness are separate. A reviewed PRD may be final while live generation remains gated by concrete policies and method artifacts. During an update, the PRD returns to draft; it can be finalized only when the reviewer gate accepts the readiness matrix and every unresolved phase blocker has an owner and enforced entry condition.

### Private workflow versus public localized reader

The MVP treats Translation Drafts as internal/private artifacts. Public localized URLs, language negotiation, and `hreflang` become requirements only if translated documents are published as crawlable web variants. Google recommends distinct locale URLs and reciprocal annotations for that case: [localized versions guidance](https://developers.google.com/search/docs/specialty/international/localized-versions).

### Local recovery versus second full-book generation

Local recovery preserves the economic and analytical value of the staged method: passing Source Units stay unchanged, weak units receive targeted effort, and edit burden remains attributable. A second full-book translation is therefore a product non-goal rather than merely an implementation preference.
