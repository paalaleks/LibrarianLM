---
title: 'EPUB to Single-Page HTML Reader'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 1
baseline_commit: 'NO_VCS'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/brief/html-epub-skill-brief.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** LibrarianLM has a complete reader template but no skill, converter, or evaluations that turn a known-source EPUB into one deterministic, self-contained HTML reader. The result must preserve the EPUB's semantic body markup and navigation while applying the shared reader design.

**Approach:** Preserve the canonical template's existing modal left sheet, add its data-driven Book Rail and converter slot contract, then implement one normalized conversion pipeline that produces identical bytes through optional-dependency and standard-library paths and is invoked by a narrowly scoped chat skill.

## Boundaries & Constraints

**Always:**

1. Keep every product file under `src/epub-html/`; `scripts/template.html` remains directly openable and authoritative.
2. Preserve body elements, text, and non-resource attributes by default, including headings, paragraphs, lists, tables, blockquotes, classes, IDs, `lang`, `xml:lang`, `dir`, ARIA, `epub:type`, and footnote/page-break semantics.
3. Remove images and multimedia (`img`, `picture`, `source`, `svg`, `audio`, `video`, `canvas`), embedded browsing/resources (`iframe`, `object`, `embed`), source `script`/`style`/stylesheet links, `style` and `on*` attributes, `src`/`srcset`/`poster`/`data`/`background`, and remote `href` values. Preserve meaningful surrounding text and links without empty wrappers.
4. Rewrite identifiers and local links deterministically; preserve every linear spine occurrence and include non-linear spine items only through transitive links from included content.
5. Produce one UTF-8/LF offline HTML artifact with inline reader CSS/JS, stable shared accent, zero live external requests, and no manifest.
6. Preserve the template's framework-free modal left sheet at every width. It is hidden by default and overlays the full-width reading region when opened; preserve its persistent Contents toggle, close control, `c`/Escape keys, scrim, scroll lock, focus trap/restoration, inert background, `aria-expanded`, and reduced-motion behavior.
7. Recover malformed body markup only when both available parser paths yield equal normalized IR. Fail without a partial artifact on unreadable package/spine data or IR disagreement.

**Ask First:** Retaining any removed resource/style, unlinked non-linear content, remote URL, per-book design override, second output, or relaxation of parser parity.

**Never:** Rewrite, summarize, translate, or invent book prose; normalize source heading levels for template styling; add a framework, build step, runtime network dependency, security shell, adversarial-input hardening, or DRM bypass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Standard | EPUB 2/3 with metadata, spine, and nav/NCX | One slug-named HTML in occurrence order; preserved markup; facts; two-level TOC; Book Rail; collapsible sheet | Summary reports detected facts |
| Metadata gaps | Missing title and/or creator | Title `Untitled`; author omitted/null; slug `untitled`; section labels `Section NN` when headings are absent | Empty/all-non-linear spine fails with no artifact |
| Navigation | Both nav and NCX, neither, or depth >2 | Precedence nav → NCX → first `h1`/`h2` → `Section NN`; flatten display to two levels while retaining deeper anchors without rail markers | Report fallback source |
| Inclusion closure | Multi-hop/cyclic links to `linear="no"`; duplicate spine hrefs | Visited-set closure; include referenced non-linear items once in spine order; omit unlinked items; all linear occurrences remain | Ambiguous href targets first included occurrence and warns |
| Omitted resources | Images/media/styles/scripts/remote references | Remove per policy; retain meaningful text; output contains no live remote URL | Summary reports counts by category |
| Protection/layout | `encryption.xml`, font obfuscation, or fixed layout | Fail only when content documents are encrypted; ignore standard-obfuscated fonts; fixed layout converts extractable text and warns poor fit | No readable text fails; no layout fidelity claimed |
| Size/malformed | Preserved text >5,000,000 UTF-8 bytes or recoverable body markup | Still one artifact; large-text warning; recover only from equal normalized IR | Unreadable structure/disagreement fails atomically |

## External Contract

- CLI: `python convert.py INPUT.epub --out OUTPUT.html [--template TEMPLATE.html] [--parser auto|ebooklib|stdlib]`; template defaults beside `convert.py`; `auto` runs both adapters and compares IR when optional dependencies are importable, otherwise uses stdlib. Explicit `ebooklib` fails with `parser-unavailable` when imports are missing. The converter never installs packages.
- Exit `0`: atomically replace `--out` and write one UTF-8 JSON Conversion Summary to stdout. Exit `1`: expected conversion/unsupported-input failure, no output file, JSON error summary to stdout. Exit `2`: CLI usage error. Unexpected diagnostics go to stderr.
- Success summary fields: `status`, `output`, `slug`, `title`, nullable `author`, `chapters`, `words`, `reading_minutes` (ceiling at 250 WPM), `bytes`, `navigation_source`, `parser`, `warnings`, and `omissions` counts for images, multimedia, embeds, styles, and remote references. Error summary fields: `status`, `code`, `message`, `warnings`.
- Slug: NFKD normalize title, ASCII-fold, lowercase, replace non-alphanumeric runs with `-`, trim, fallback `untitled`. The skill writes `/mnt/user-data/outputs/<slug>.html` and presents exactly that artifact plus the summary.

</frozen-after-approval>

## Code Map

- `src/epub-html/scripts/template.html:7,566-652` — existing `head-title`, repeated `title`/`author`, `facts`, `toc`, and `chapters` slots plus the authoritative modal-sheet markup; add reusable TOC/chapter prototypes without changing visible preview behavior.
- `src/epub-html/scripts/template.html:141-319,742-969` — authoritative sheet/TOC CSS and runtime already handle modal state, focus, inert background, shortcuts, theme, and scroll spy; preserve them while adding Book Rail data behavior and converter-owned facts.
- `src/epub-html/scripts/convert.py` — new CLI, parser adapters, normalized IR, inclusion closure, cleanup, ID/link rewriting, canonical serializer, atomic output, and JSON summaries.
- `src/epub-html/SKILL.md` — new trigger, converter invocation, summary/failure handling, and single-artifact delivery.
- `src/epub-html/evals/evals.json` — new chat-trigger, success, warning, and failure assertions.
- `src/epub-html/tests/` — new unit suite plus synthetic and real-fixture corpus.

## Tasks & Acceptance

**Execution:**

- [x] `src/epub-html/scripts/template.html` — preserve the existing sheet interaction and preview; retain `head-title`, repeated `title`/`author`, `facts`, `toc`, and `chapters`; add `<template>` slots `toc-chapter-template`, `toc-subitem-template`, and `chapter-template`, Book Rail behavior, and preserved-heading styling. Converter may fill/clone those slots and set only `id`, `data-target`, integer `data-words`, `href`, and text/content placeholders. Filled ASCII facts must not be overwritten by the current locale-aware fallback.
- [x] `src/epub-html/scripts/convert.py` — implement the External Contract and one canonical IR: ordered metadata; spine occurrences; namespace-aware element/text nodes; sorted attributes; normalized LF; ordered nav nodes/warnings. Serialize with UTF-8, LF, fixed doctype, no pretty-printing, stable escaping, sorted attributes, occurrence IDs `ch-NNNN[-source-id]`, and deterministic warning order. Compare IR, not parser-native trees.
- [x] `src/epub-html/SKILL.md` — define `.epub` trigger, no prose regeneration, auto-parser invocation, output location, JSON summary rendering, and plain failures.
- [x] `src/epub-html/evals/evals.json` — distinguish skill assertions (trigger, one artifact, summary/warnings, failure wording) from converter assertions.
- [x] `src/epub-html/tests/test_convert.py` and `src/epub-html/tests/fixtures/` — test matrix, slots, hashes, parity, markup retention, anchors, cleanup, atomic failure, and browser-find compatibility on Python 3.12. Include `real/gutenberg-classic.epub`, `real/footnotes-tables.epub`, and `real/no-nav.epub` with provenance in `fixtures/README.md`, plus generated synthetic fixtures.

**Acceptance Criteria:**

- Given identical input, template, and configuration, when conversion runs three times and through each available adapter, then normalized IR and output SHA-256 match.
- Given retained source markup, when converted, then permitted elements/attributes survive, IDs are unique, and every retained local link resolves exactly once.
- Given omitted content, when converted, then no removed element, style behavior, image, or live remote URL remains and summary counts match.
- Given a generated reader, when opened offline, then the existing modal sheet behavior, TOC, Book Rail, browser Find, theme, focus/ARIA, reduced motion, and print work without console or network errors; there is no custom search UI.
- Given every matrix failure/warning condition, when converted, then the specified classification occurs without silent included-chapter loss or a partial artifact.

## Design Notes

EbookLib defaults `ignore_ncx` to true, so its adapter must retain NCX explicitly. Optional libraries help parse source data but never serialize output. Repeated spine occurrences prefix all source IDs; links to repeated hrefs target the first included occurrence and warn. Unlinked non-linear items are intentionally omitted and do not count as silent chapter loss.

## Verification

**Commands:**

- `uv run --python 3.12 --no-project python -m unittest discover -s src/epub-html/tests -v` — stdlib, structural, fixture, and repeat-hash suite passes.
- `uv run --python 3.12 --with EbookLib --with beautifulsoup4 python -m unittest discover -s src/epub-html/tests -v` — optional adapter and IR/output parity pass.
- `python -m json.tool src/epub-html/evals/evals.json` — eval JSON is valid.

**Manual checks:**

- Open the standalone template and a generated fixture at desktop/mobile widths; verify the sheet remains hidden by default and preserves toggle/close/shortcut/scrim/focus/inert/scroll-lock behavior, plus Book Rail weight/position, dark mode, reduced motion, browser Find, print preview, and zero console/network errors.

### Review Findings

- [x] [Review][Patch] Build a two-level heading-fallback TOC with subsequent `h2` entries as chapter subitems [src/epub-html/scripts/convert.py:579]
- [x] [Review][Patch] Reject missing manifest references and missing archive files in the linear spine [src/epub-html/scripts/convert.py:270]
- [x] [Review][Patch] Avoid parsing malformed unlinked non-linear documents before inclusion is resolved [src/epub-html/scripts/convert.py:505]
- [x] [Review][Patch] Let malformed navigation documents warn and fall back instead of aborting content parsing [src/epub-html/scripts/convert.py:505]
- [x] [Review][Patch] Include linked non-linear spine documents only once [src/epub-html/scripts/convert.py:317]
- [x] [Review][Patch] Canonicalize encoded/query-bearing local URLs and remove retained links that cannot resolve in-page [src/epub-html/scripts/convert.py:91]
- [x] [Review][Patch] Preserve meaningful fallback text when removing resource containers [src/epub-html/scripts/convert.py:320]
- [x] [Review][Patch] Remove empty wrappers left behind by resource cleanup [src/epub-html/scripts/convert.py:320]
- [x] [Review][Patch] Strip whitespace-obscured and non-`href` URL attributes that can make live requests [src/epub-html/scripts/convert.py:95]
- [x] [Review][Patch] Prevent explicit EbookLib mode from recovering malformed markup without parser parity [src/epub-html/scripts/convert.py:193]
- [x] [Review][Patch] Include ordered navigation and warning state in parser-parity IR [src/epub-html/scripts/convert.py:524]
- [x] [Review][Patch] Preserve converter-owned chapter word counts at runtime [src/epub-html/scripts/template.html:875]
- [x] [Review][Patch] Exercise all checked-in real EPUB fixtures in the normal test suite [src/epub-html/tests/test_convert.py:70]
- [x] [Review][Patch] Add executable coverage for modal sheet interactions and accessibility state [src/epub-html/tests/test_convert.py:92]
- [x] [Review][Patch] Add executable coverage for the documented custom-template CLI option [src/epub-html/tests/test_convert.py:71]
