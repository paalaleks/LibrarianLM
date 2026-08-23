# Validation Report — EPUB to Single-Page HTML Reader

- **PRD:** `_bmad-output/planning-artifacts/prds/prd-LibrarianLM-2026-08-22/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-08-23T08:45:00+02:00
- **Grade:** Fair

## Overall verdict

This is a decision-ready internal-tool PRD: the thesis (faithful, offline, byte-identical one-file readers; converter-not-editor; one canonical template) actually governs features, non-goals, and metrics, including honest counter-metrics. What holds up is trade-off honesty and operational success criteria. What is at risk for architecture and story work is done-ness at the edges—especially the unsupported-element allowlist, leftover image/accessibility language after the omit-images decision, and confirmed failure/recovery behavior that lives in §11/addendum rather than as FRs.

A completeness/feasibility pass materially shifts the gate: §11/§12 close the document while CLI vs skill I/O, Conversion Summary shape (JSON vs prose), dual-parser identity, and several FR contradictions remain unspecified. Treat those as **blocking before development**, even though the rubric grade is Fair rather than Poor (no broken dimensions).

## Dimension verdicts
- Decision-readiness — strong
- Substance over theater — strong
- Strategic coherence — strong
- Done-ness clarity — adequate
- Scope honesty — strong
- Downstream usability — adequate
- Shape fit — strong

## Findings by severity

### Critical (4)
**Completeness** — False closure of open questions (§11, §12)
The PRD states no phase-blocking questions or unresolved assumptions remain, yet CLI flags, atomic write, JSON summary fields, slug, parser `auto`, and SKILL.md host are not FRs; memlog still lists superseded assumptions.
Fix: Reopen §11/§12 with an explicit decision list, or promote those contracts into numbered FRs; reconcile stale memlog assumptions.

**Completeness** — CLI vs skill vs Conversion Summary contract (FR-2, FR-3, brief §5, addendum B)
Glossary calls the Conversion Summary human-readable; the brief requires JSON, `--out`, `--parser`, and atomic write; FR-2 only names a host output location.
Fix: Split Converter CLI (argv, exits, JSON schema, atomic `--out`) from skill presentation (file location, chat rendering).

**Completeness** — Dual-parser byte identity underspecified (FR-17, FR-18, addendum B)
`auto` IR comparison and fail-on-disagreement are addendum-only; “well-formed Supported EPUB” is undefined vs parser HTML differences.
Fix: Make IR comparison, `--parser` values, and fail-on-disagreement FRs; name which fixtures must match vs parser-disagreement.

**Completeness** — Image omission vs preserved image alt (FR-11, FR-16)
FR-11 removes image elements; FR-16 still requires preserving image alternative text.
Fix: One rule (drop alt with the element vs promote alt to text) and rewrite FR-16.

### High (8)
**Done-ness** — No supported-markup allowlist (§4.3 FR-8)
“Preserved where valid and supported” has no element/attribute inventory.
Fix: Preserve / strip / fail table; report stripped categories in the Conversion Summary.

**Done-ness** — Failure/recovery contract is not an FR (§11; addendum H)
Parser-agree recovery and atomic fail are decided but not testable FRs.
Fix: Use the empty FR-7 slot for agree-and-recover vs disagree-and-emit-no-file.

**Completeness** — Missing FRs for confirmed pipeline behavior (§11, addendum H)
Transitive non-linear inclusion, cycle/visited-set, first-occurrence warning, no conversion manifest are not FRs.
Fix: Assign FRs (stable IDs) for inclusion-closure, malformed recovery, and atomic failure.

**Completeness** — “Usable” navigation is undefined (FR-5)
Empty nav, broken hrefs, landmarks-only, and NCX with zero navPoints are unspecified.
Fix: Define usable (e.g. at least one resolvable content target) and the precedence test.

**Completeness / Decision-readiness** — Fixed-layout “best-effort” is not a conversion rule (FR-6)
No bound for extractable text vs bitmap-only vs SM-1 hash on those fixtures.
Fix: Replace “best-effort” with observable rules (same text/spine omit-images policy; fail if no text; never claim layout fidelity).

**Completeness** — Slug, missing title, filename collisions unspecified (FR-2)
No Unicode/empty-title/overwrite policy.
Fix: Specify slug algorithm, untitled fallback, and overwrite vs fail.

**Completeness** — Word count, chapter count, reading-time formatting unspecified (FR-3, FR-14, FR-17)
Tokenizer, locale-stable facts string, and chapter vs spine vs TOC counts can diverge.
Fix: One word-count function, chapter count = included spine occurrences, locale-stable display.

**Completeness** — Chat upload vs trusted-source; SKILL.md host missing (UJ-1, NFR-2, FR-1)
Chat is an untrusted-upload surface; no skill trigger/host/invocation FR.
Fix: Name host and operator; add skill FR for SKILL.md, `convert.py` invocation, and “valid” EPUB.

### Medium (n)
**Done-ness / Completeness** — Source styling / class preservation (FR-10, FR-11 vs brief)
“Source styling” can be read as stripping `class` while the brief keeps classes/IDs/ARIA/`epub:type`.
Fix: FR-level attribute allowlist/denylist.

**Scope** — Glossary still implies embeddable resources (§3 vs FR-11)
Fix: Redefine Source Content as text/semantics/identifiers/links only for MVP.

**Downstream** — FR ID gap (§4)
FRs skip FR-7.
Fix: Reuse FR-7 for parser-agreement/atomic-failure.

**Downstream** — Circular Supported EPUB (§3; SM-1–SM-3)
Fix: Point metrics at addendum F classes plus exclusion of protected / parser-disagreeing / unreadable packages.

**Completeness** — Encryption vs font obfuscation incomplete (FR-6)
Fix: Fail only when content documents required for reading are encrypted; fonts-only encryption.xml is not DRM.

**Completeness** — Identifier scheme and nav depth (FR-9, FR-14)
Fix: Occurrence-scoped IDs; parse-full / flatten-display.

**Completeness** — SVG, MathML, embedded browsing resources (FR-11, §9.2)
Fix: Named omitted-element list.

**Completeness** — Unnamed corpus / “interactively usable” (NFR-5, SM-4)
Fix: Point at SM-4 checks and addendum F fixture classes; name engine for console-error checks.

**Completeness** — Template vs unfinished Book Rail (FR-12, FR-14)
Fix: State remaining template slot/rail work as in-scope.

**Completeness** — Wrong brief path (§0)
Actual path is `docs/brief-epub-html/html-epub-skill-brief.md`.

**Completeness** — Remote href vs zero-network (FR-9, FR-11, NFR-1)
Fix: Allowed URL schemes (`#` only vs keep http(s) without prefetch).

### Low (n)
Slug/rail mapping (partially covered under High) · Dual output-path wording (label `/mnt/user-data/outputs/` as host example) · Memlog vs §12 drift · FR-1 “filenames resemble book titles” · Print CSS vs continuous-surface vision · Brief ASCII sidebar vs modal sheet.

## Mechanical notes
- FR-7 missing; remaining FR and SM IDs unique; SM citations resolve.
- Glossary drift: “chapter count” vs “Spine Document count”; “language direction” vs “text direction”; “supported embedded resources” vs omit-images.
- No inline `[ASSUMPTION]` tags; §12 empty matches the PRD body, not the memlog.
- Memlog still lists image embedding, hostile-input limits, and non-linear inclusion as unconfirmed after later overrides.
- §0 brief path does not match the repo (`docs/brief-epub-html/html-epub-skill-brief.md`).

## Reviewer files
- `review-rubric.md`
- `review-completeness-feasibility.md`
