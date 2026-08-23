# Project brief — epub → single-page HTML reader

## 1. Goal

A skill that triggers when someone uploads an `.epub` in chat and returns one `.html` file containing the entire book: all chapters concatenated into a single scrollable document, with a persistent table of contents in a left sidebar.

Conversion is done by a deterministic Python script — same epub in, byte-identical HTML out. Claude's role is to run the script, report what it found, and handle failures. Claude never rewrites, summarises, or re-types book content.

Every book produced by this skill uses the same design system, so a shelf of converted books looks like a set rather than a pile.

## 2. Pipeline

```
upload.epub
   ↓  parse container.xml → .opf  (spine order, metadata)
   ↓  parse nav.xhtml or toc.ncx  (TOC tree, up to 2 levels)
   ↓  extract + clean each spine document's <body> for offline output
   ↓  render into the HTML template (inline CSS + inline JS)
   ↓  /mnt/user-data/outputs/<slug>.html
```

**Parsing strategy:** try `ebooklib` + `beautifulsoup4` first; if pip is unavailable, fall back to `zipfile` + `xml.etree` + `html.parser` from the standard library. Both paths must produce the same output for a well-formed epub — the fallback is a reliability net, not a lesser mode.

**Offline cleanup:** preserve body elements, text, and non-resource attributes by default, including classes, IDs, language/direction, ARIA, `epub:type`, headings, paragraphs, blockquotes, lists, tables, emphasis, footnotes, and page-break semantics. Remove images and multimedia, embedded browsing/resources, source scripts and styles, `style` and event-handler attributes, external stylesheets, resource attributes, and live remote URLs. Rewrite intra-book anchors (`chapter3.xhtml#note7`) to deterministic in-page anchors so footnotes and cross-references still work.

**Input trust:** epub sources are known and trusted. Adversarial archive/XML hardening, a security sandbox, CSP, and hostile-input test fixtures are outside scope. Structural validation exists only to support reliable conversion and useful failure messages.

## 3. Design direction

The subject is a book that has been taken apart and re-assembled as one continuous surface. The design should make that legible: you are not flipping pages, you are looking at the whole thing at once and choosing where to stand in it.

Deliberately avoiding the default reading-app look (cream page, big serif display, terracotta accent). The palette is cool and slightly green — closer to laid paper under daylight than to parchment.

### Tokens

**Colour — light**
| Token | Value | Use |
|---|---|---|
| `--paper` | `#ECEEEA` | page background |
| `--ink` | `#1B1F1D` | body text |
| `--ink-soft` | `#5C645F` | captions, TOC inactive, metadata |
| `--rule` | `#C9CEC6` | hairlines, spine track |
| `--accent` | `#46407F` | position marker, current chapter, links |

**Colour — dark**
| Token | Value |
|---|---|
| `--paper` | `#15181A` |
| `--ink` | `#DEE2DC` |
| `--ink-soft` | `#8B948E` |
| `--rule` | `#2C3235` |
| `--accent` | `#9C93E8` |

Dark mode is a class on `<html>`, defaults to `prefers-color-scheme`, and is overridable by a toggle in the sidebar footer. The choice persists in `localStorage`.

**Type** — three roles, all from system stacks so the file renders identically offline with no font payload:

- Body: `Charter, "Bitstream Charter", "Iowan Old Style", "Source Serif 4", Georgia, serif` — 1.125rem / 1.65 line height, measure capped at 68ch.
- Interface: `ui-sans-serif, "Inter", system-ui, sans-serif` — sidebar, toggle, small caps-ish treatment via 0.06em tracking at 0.8125rem.
- Utility: `ui-monospace, "SF Mono", "JetBrains Mono", monospace` — chapter numbers and word counts only.

Chapter titles set in the body serif at 1.75rem, weight 600, with the chapter number set above in mono at 0.75rem. No display face — in a reading environment the book's own text is the display element.

### Layout

```
┌──────────────┬────────────────────────────────────┐
│ TITLE        │                                    │
│ author       │        ┌──────────────────┐        │
│ ──────────── │        │  01              │        │
│ ▍ 01 Chapter │        │  Chapter title   │        │
│ ▍ 02 Chapter │        │                  │        │
│ █ 03 Chapter │        │  Body text set   │        │
│ ▍   3.1 Sub  │        │  at 68ch, one    │        │
│ ▍ 04 Chapter │        │  continuous      │        │
│ ▍ 05 Chapter │        │  scroll for the  │        │
│              │        │  whole book…     │        │
│ ──────────── │        └──────────────────┘        │
│ ☾ Dark       │                                    │
└──────────────┴────────────────────────────────────┘
   280px fixed              content column
```

- Sidebar: the canonical template's framework-free modal left sheet, hidden by default at every viewport size. It overlays the full-width reading region when opened and has its own scroll, book title and author at top, dark toggle at the bottom, persistent Contents trigger, close control, scrim, focus trap/restoration, inert background, and scroll lock.
- Content: single `<main>`, one `<section id="ch-NN">` per spine document, centred in the remaining space.
- Under 900px: the sheet width is capped to leave a small viewport edge visible; content uses 1rem gutters. At every width, Escape or `c` closes it, `c` also opens it, `aria-expanded` stays accurate, and reduced-motion preferences apply.

### Signature element — the spine

The left rail is not a list of links, it is a scale model of the book. Each TOC entry's marker is a vertical bar whose height is proportional to that chapter's word count, so a 40-page chapter and a two-page interlude are visibly different weights. A filled marker travels down the rail as you scroll, and the current chapter's bar takes `--accent`.

This is the one place the design spends boldness. Everything else — type, spacing, rules — stays quiet. The rail is generated from real data, not decoration: it is why you can tell at a glance that you are a third of the way through a long middle chapter rather than a third of the way through the book.

### Title block

The book opens with a generated title block occupying roughly the first screen: title in the body serif at 2.5rem, author beneath in the interface face, and a single mono line of book facts — chapter count, total word count, estimated reading time at 250wpm. A hairline rule closes it before chapter one begins.

It earns its place by answering the question you ask before committing to a long scroll: how big is this, and how long will it take. The facts come from the parsed book, so the line is real data in the same spirit as the rail. In the sidebar the block gets its own TOC entry at the top, with no rail marker — it is not a chapter.

Scroll-spy runs on `IntersectionObserver`. Under `prefers-reduced-motion` the marker jumps rather than animates, and smooth scrolling is disabled.

## 4. One template as the source of truth

`src/epub-html/scripts/template.html` is the single canonical model of the reader UI. It is a complete, working, hand-authored HTML file — openable in a browser on its own with placeholder chapters — and it holds all markup, all CSS, and all JavaScript for the reading experience. Every converted book is that file with content substituted in.

This means:

- The converter never generates UI markup, CSS, or JS. It fills named slots — book title, author, TOC entries, chapter sections — and nothing else. If a design change is needed, it happens in the template, not in Python string concatenation.
- Design tokens are declared once, as CSS custom properties on `:root` in the template. The values in §3 live there and nowhere else.
- Because the template is directly openable, it doubles as the design review artefact: to judge a change to the reader, open the template rather than converting a book.
- Any book converted with the same template version is visually identical to any other, which is the point — a shelf of converted books should read as one set.

## 5. Output contract

- One file, zero external requests — fully offline once downloaded.
- `<style>` and `<script>` inline; no build step, no CDN, no framework.
- Keyboard: `Tab` reaches every TOC link with a visible focus ring; `d` toggles dark mode.
- Semantic HTML — `<nav>`, `<main>`, `<article>`, real heading levels — so browser reader mode, Ctrl+F, and print all work.
- Print stylesheet: sidebar hidden, chapters break to new pages.
- Filename: `<slugified-title>.html`, presented in chat when done.
- CLI: `convert.py INPUT.epub --out OUTPUT.html [--template TEMPLATE.html] [--parser auto|ebooklib|stdlib]`; success writes the file atomically and emits one JSON Conversion Summary. Expected conversion failure emits an error summary and leaves no partial file.
- The Conversion Summary reports title, optional author, chapter count, word count, reading time at 250wpm, output bytes, navigation source, parser path, warnings, and omission counts.

## 6. Edge cases the script must handle

| Case                         | Behaviour                                                                  |
| ---------------------------- | -------------------------------------------------------------------------- |
| No `nav.xhtml` or `toc.ncx`  | Build TOC from spine order and each document's first `<h1>`/`<h2>`         |
| TOC deeper than 2 levels     | Flatten to 2; deeper entries keep their anchors but not their rail markers |
| DRM-encrypted epub           | Detect `META-INF/encryption.xml`, stop, and say so plainly                 |
| Fixed-layout / comic epub    | Warn that it's a poor fit for a text-only reader, convert anyway           |
| Very large books (>5MB text) | Still one file; note the size in the summary                               |

## 7. Deliverables

```
src/epub-html/
├── SKILL.md              trigger conditions, workflow, failure handling
├── scripts/
│   ├── convert.py        CLI: convert.py book.epub --out out.html
│   └── template.html     the reader shell, CSS and JS inline
└── evals/
    └── evals.json        test prompts + assertions
```

## 8. Test set

Three real epubs, chosen to stress different things: one Project Gutenberg classic (clean, deep TOC), one book with heavy footnotes, blockquotes and tables, one epub with no `nav.xhtml` (fallback TOC generation). Synthetic fixtures cover duplicate spine occurrences, transitive/cyclic links to non-linear content, missing metadata, protection/layout classification, cleanup, parser parity, malformed bodies, and atomic failure. Assertions cover chapter count matching included spine occurrences, every retained link resolving to a real anchor, no live resource paths in the output, repeat hashes, and the file opening with no console errors.

## 9. Confirmed product decisions

- One shared accent and identity across all books; no per-book override.
- Ignore all images and multimedia.
- Include non-linear spine documents only through transitive links from included content; omit unlinked items.
- Omit remote resources and report warnings.
- Recover malformed body markup only when available parser paths produce the same normalized representation; otherwise fail without a partial file.
- Emit no conversion manifest; the Conversion Summary is the only conversion report.
- Use a collapsible left sheet at every viewport size rather than a permanently fixed desktop sidebar.
