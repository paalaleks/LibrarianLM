---
name: epub-to-single-page-html-reader
description: Convert a supplied EPUB into one offline, single-page HTML reader without changing its prose.
---

# EPUB to single-page HTML reader

Trigger when the user supplies an `.epub` and asks to read, convert, or export it as HTML. Do not trigger for a request to summarize, rewrite, or otherwise transform the book's prose.

Run the bundled converter with the uploaded EPUB and its default `auto` parser:

```bash
python src/epub-html/scripts/convert.py INPUT.epub --out /mnt/user-data/outputs/SLUG.html --parser auto
```

Read the one JSON object printed to stdout. On success, present exactly the generated `/mnt/user-data/outputs/<slug>.html` artifact and render the title, optional author, chapter count, word count, reading minutes, navigation source, warnings, and omission counts from that summary. Do not generate or repeat book prose.

On failure, plainly relay the JSON error `message` and `code`; do not create a substitute artifact, retry with package installation, or promise partial content. The converter itself never installs optional parsers.
