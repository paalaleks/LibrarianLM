---
title: EPUB to Single-Page HTML Reader — PRD Addendum
status: draft
created: 2026-08-22
updated: 2026-08-22
---

# PRD Addendum: EPUB to Single-Page HTML Reader

This addendum preserves implementation constraints, design tokens, source details, and research notes that inform downstream architecture and UX work but do not belong in the capability-focused PRD.

## A. Canonical Product Tree

All EPUB-to-HTML product files belong under the repository’s existing canonical subtree:

```text
src/epub-html/
├── SKILL.md
├── scripts/
│   ├── convert.py
│   └── template.html
└── evals/
    └── evals.json
```

`src/epub-html/scripts/template.html` already exists and is the authoritative source artifact for reader UI. It must be preserved and evolved rather than duplicated or regenerated elsewhere.

## B. Proposed Deterministic Pipeline

```text
upload.epub
   ↓ locate package document through META-INF/container.xml
   ↓ read metadata, manifest, and spine order from package document
   ↓ read nav.xhtml or toc.ncx; fall back to deterministic headings
   ↓ validate expected structure and classify protection/layout/resources
   ↓ extract and clean included Spine Document bodies
   ↓ rewrite identifiers, fragments, and supported local resources
   ↓ fill named Reader Template slots
   ↓ emit /mnt/user-data/outputs/<slugified-title>.html
```

The intended CLI contract from the brief is:

```text
convert.py book.epub --out out.html
```

The preferred parsing path uses `ebooklib` and `beautifulsoup4`. When those dependencies are not already importable, the standard-library path uses `zipfile`, `xml.etree`, and `html.parser`; the Converter never installs packages. When both paths are available, `auto` compares their normalized intermediate representations before serialization. Any disagreement fails without an output file.

The normalized representation contains ordered metadata, spine occurrences, namespace-aware element/text nodes, ordered navigation nodes, and ordered warnings. Deterministic serialization fixes UTF-8, LF, doctype, escaping, sorted attributes, source text after newline normalization, occurrence-scoped identifiers, and warning order; it excludes pretty-printing, timestamps, random values, host paths, and locale-sensitive formatting.

## C. Reader Template Slots

The Converter fills named content slots and does not synthesize independent reader chrome. At minimum, the template needs stable slots for:

- browser document title;
- visible book title and author instances;
- Title Block facts;
- Navigation Tree entries and Book Rail data;
- chapter sections and their identifiers.

The directly openable placeholder state doubles as the primary visual-review artifact.

## D. Design Tokens and Layout

### Light palette

| Token | Value | Purpose |
|---|---:|---|
| `--paper` | `#ECEEEA` | Background |
| `--ink` | `#1B1F1D` | Body text |
| `--ink-soft` | `#5C645F` | Metadata and inactive navigation |
| `--rule` | `#C9CEC6` | Hairlines and rail track |
| `--accent` | `#46407F` | Active chapter, position, links |

### Dark palette

| Token | Value |
|---|---:|
| `--paper` | `#15181A` |
| `--ink` | `#DEE2DC` |
| `--ink-soft` | `#8B948E` |
| `--rule` | `#2C3235` |
| `--accent` | `#9C93E8` |

### Type roles

- Body: `Charter, "Bitstream Charter", "Iowan Old Style", "Source Serif 4", Georgia, serif`; 1.125 rem, 1.65 line height, 68 ch maximum measure.
- Interface: `ui-sans-serif, "Inter", system-ui, sans-serif`; 0.8125 rem with 0.06 em tracking where appropriate.
- Utility: `ui-monospace, "SF Mono", "JetBrains Mono", monospace`; reserved for chapter numbers and counts.
- Chapter title: body serif, 1.75 rem, weight 600; chapter number above in utility mono at 0.75 rem.
- Title Block title: body serif at 2.5 rem.

### Layout and behavior

- The canonical template already implements a framework-free modal left sheet with independent scroll, title/author at top, and theme control at the footer. It is hidden by default at every width and overlays the full-width reading region when opened.
- Preserve the persistent Contents trigger, close control, `c`/Escape shortcuts, scrim, background inert state, scroll lock, focus trap/restoration, `aria-expanded`, and reduced-motion behavior. Below 900 px, sheet width leaves a small viewport edge visible and content uses 1 rem gutters.
- One `<main>` containing a Title Block followed by one identified `<section>` per included Spine Document.
- Theme state is represented by a class on `<html>`, initially follows `prefers-color-scheme`, and is overridable with a persisted local choice.
- Scroll position is observed with `IntersectionObserver`; reduced-motion mode disables smooth scrolling and position animation.
- Print styling hides sidebar and begins chapters on new pages.

## E. Source Cleanup Notes

EPUB Inputs come from a known, trusted source; hostile-input defense is outside scope. Cleanup exists to make output deterministic, portable, and offline. Preserve body markup and non-resource attributes by default. Remove images/multimedia, embedded resource elements, source scripts/styles, style/event/resource attributes, and live remote URLs; report omission counts. External resources are never fetched.

`META-INF/encryption.xml` still requires inspection rather than a blanket “DRM” classification because EPUB font obfuscation is also represented there.

## F. Evaluation Corpus

The brief requires three real EPUBs:

1. a clean Project Gutenberg classic with a deep Navigation Tree;
2. a book rich in footnotes, blockquotes, and tables;
3. a book without `nav.xhtml`, exercising fallback Navigation Tree generation.

Additional synthetic or purpose-built fixtures should cover EPUB 2 and 3, nested paths, duplicate spine occurrences, multi-hop/cyclic non-linear inclusion, missing metadata/spine, missing or broken navigation, fixed layout, remote URLs, omitted resources, encryption versus standard font obfuscation, malformed body recovery, parser disagreement, atomic failure, and repeat-conversion hashes.

## G. Standards and Research Notes

- [EPUB 3.3](https://www.w3.org/TR/epub-33/) defines the OCF container, package document, spine, resources, navigation, encryption metadata, and fixed-layout properties.
- [EPUB Reading Systems 3.3](https://www.w3.org/TR/epub-rs-33/) defines reading-order behavior, navigation processing, and resource handling.
- [EPUB Accessibility 1.1](https://www.w3.org/TR/epub-a11y-11/) layers EPUB-specific accessibility requirements on general web accessibility.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) informs the Reader Template’s keyboard, focus, contrast, resize, and reflow acceptance criteria.
- [Reproducible Builds](https://reproducible-builds.org/docs/definition/) provides the bit-for-bit reproducibility framing used for the deterministic output contract.

## H. Confirmed Decisions

- Preserve body markup by default but omit all images, multimedia, source styling, embedded resources, and live remote references; report omissions.
- Include non-linear spine content only through transitive links from included content; resolve cycles with a visited set and ambiguous repeated targets to the first included occurrence with a warning.
- Recover malformed bodies only when normalized parser representations agree; otherwise fail atomically.
- Emit no conversion manifest and use one shared accent.
- Use a collapsible left sheet at every viewport size.
