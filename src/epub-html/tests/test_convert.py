from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "src/epub-html/scripts/convert.py"
TEMPLATE = ROOT / "src/epub-html/scripts/template.html"
sys.path.insert(0, str(SCRIPT.parent))
import convert as converter


def fixture(path: Path, *, malformed: bool = False, encrypted: bool = False, font_encrypted: bool = False, no_metadata: bool = False, nav: bool = True, fixed: bool = False, all_non_linear: bool = False) -> None:
    nav_item = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>' if nav else ""
    layout = '<meta property="rendition:layout">pre-paginated</meta>' if fixed else ""
    font_item = '<item id="font" href="font.otf" media-type="application/vnd.ms-opentype"/>' if font_encrypted else ""
    linear = ' linear="no"' if all_non_linear else ""
    opf = '''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">%s%s</metadata><manifest><item id="c1" href="one.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="two.xhtml" media-type="application/xhtml+xml"/><item id="extra" href="notes.xhtml" media-type="application/xhtml+xml" properties=""/>%s%s</manifest><spine><itemref idref="c1"%s/><itemref idref="c2"%s/><itemref idref="extra" linear="no"/></spine></package>''' % ("" if no_metadata else "<dc:title>Résumé &amp; Tables</dc:title><dc:creator>Ada</dc:creator>", layout, nav_item, font_item, linear, linear)
    one = '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1 id="start">Start</h1><p class="chapter keep" lang="en" epub:type="z3998:fiction" xmlns:epub="http://www.idpf.org/2007/ops">Hello <a href="two.xhtml#end">next</a> <a href="notes.xhtml#note">note</a><img src="cover.jpg"/></p></body></html>'
    if malformed: one = '<html><body><h1 id="start">Start</h1><p>broken <em>but readable</body></html>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr("book.opf", opf)
        archive.writestr("one.xhtml", one)
        archive.writestr("two.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><h2 id="end">End</h2><p style="color:red" onclick="x()"><a href="https://example.com">outside</a>Fin.</p></body></html>')
        archive.writestr("notes.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><aside id="note">Useful note.</aside></body></html>')
        if nav: archive.writestr("nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops"><ol><li><a href="one.xhtml">One</a></li></ol></nav></body></html>')
        if font_encrypted: archive.writestr("font.otf", b"not-a-real-font")
        if encrypted or font_encrypted:
            uri = "one.xhtml" if encrypted else "font.otf"
            archive.writestr("META-INF/encryption.xml", f'<encryption><EncryptedData><CipherData><CipherReference URI="{uri}"/></CipherData></EncryptedData></encryption>')


def closure_fixture(path: Path, *, with_navigation: bool = False, large: bool = False) -> None:
    metadata = '<dc:title>Closure Book</dc:title><dc:creator>Tester</dc:creator>'
    manifest = '<item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/><item id="deep" href="deep.xhtml" media-type="application/xhtml+xml"/>'
    spine = '<itemref idref="one"/><itemref idref="one"/><itemref idref="notes" linear="no"/><itemref idref="deep" linear="no"/>'
    nav_item = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>' if with_navigation else ""
    opf = f'<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{metadata}</metadata><manifest>{manifest}{nav_item}</manifest><spine>{spine}</spine></package>'
    payload = ("word " * 1_100_000) if large else "Body"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr("book.opf", opf)
        archive.writestr("one.xhtml", f'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1 id="first">First</h1><p>{payload} <a href="notes.xhtml#note">notes</a></p><h2 id="sub">Sub heading</h2><h3 id="deep-anchor">Deep heading</h3></body></html>')
        archive.writestr("notes.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><aside id="note">Note <a href="deep.xhtml#deep">deep</a></aside></body></html>')
        archive.writestr("deep.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><p id="deep">Deep <a href="one.xhtml#first">back</a></p></body></html>')
        if with_navigation:
            archive.writestr("nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops"><ol><li><a href="one.xhtml#first">NAV Wins</a><ol><li><a href="one.xhtml#sub">Sub nav</a><ol><li><a href="one.xhtml#deep-anchor">Deep nav</a></li></ol></li></ol></li></ol></nav></body></html>')
            archive.writestr("toc.ncx", '<ncx><navMap><navPoint><navLabel><text>NCX Must Lose</text></navLabel><content src="one.xhtml#first"/></navPoint></navMap></ncx>')


def unreadable_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr("book.opf", '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Pictures</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>')
        archive.writestr("one.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><img src="only-image.jpg"/></body></html>')


def custom_fixture(path: Path, opf: str, documents: dict[str, str | bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr("book.opf", opf)
        for name, content in documents.items():
            archive.writestr(name, content)


def find_headless_browser() -> str | None:
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        if executable := shutil.which(name):
            return executable
    roots = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]
    candidates = (
        ("Microsoft", "Edge", "Application", "msedge.exe"),
        ("Google", "Chrome", "Application", "chrome.exe"),
    )
    for root in filter(None, roots):
        for parts in candidates:
            candidate = Path(root, *parts)
            if candidate.is_file():
                return str(candidate)
    return None


class ConvertTests(unittest.TestCase):
    def run_converter(self, epub: Path, out: Path, *extra: str):
        run = subprocess.run([sys.executable, str(SCRIPT), str(epub), "--out", str(out), *extra], text=True, capture_output=True, check=False)
        return run, json.loads(run.stdout)

    def test_repeat_hash_cleanup_links_and_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; fixture(epub)
            a, b = root / "a.html", root / "b.html"
            first, summary = self.run_converter(epub, a, "--parser", "stdlib")
            second, _ = self.run_converter(epub, b, "--parser", "stdlib")
            self.assertEqual(0, first.returncode); self.assertEqual(0, second.returncode)
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
            result = a.read_text(encoding="utf-8")
            self.assertIn('class="chapter keep"', result); self.assertIn('epub:type=', result)
            self.assertNotIn("cover.jpg", result); self.assertNotIn("https://example.com", result)
            self.assertIn('href="#ch-0002-end"', result); self.assertIn('href="#ch-0003-note"', result)
            self.assertEqual(3, summary["chapters"]); self.assertGreater(summary["omissions"]["images"], 0)
            self.assertEqual(summary["chapters"], len(re.findall(r'<section class="reader-chapter" id="ch-\d{4}"', result)))
            self.assertIn('id="toc-chapter-template"', result); self.assertIn('data-converter-owned="true"', result)
            self.assertNotIn("The Binding Copy", result)

    def test_template_preview_has_active_book_rail_data(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        preview = template.split('<template id="toc-chapter-template">', 1)[0]
        self.assertEqual(5, preview.count('class="book-rail"'))
        self.assertEqual(5, len(re.findall(r'<li class="toc-ch"[^>]*data-words="\d+"', preview)))
        self.assertEqual(5, len(re.findall(r'<section class="reader-chapter" id="ch-\d+" data-words="\d+">', template)))

    def test_missing_metadata_and_atomic_encryption_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; fixture(epub, no_metadata=True)
            out = root / "untitled.html"; run, summary = self.run_converter(epub, out)
            self.assertEqual(0, run.returncode); self.assertEqual("Untitled", summary["title"]); self.assertIsNone(summary["author"])
            fixture(epub, encrypted=True); failed, error = self.run_converter(epub, out)
            self.assertEqual(1, failed.returncode); self.assertEqual("encrypted-content", error["code"])
            self.assertTrue(out.exists(), "pre-existing output must not be removed on failed conversion")

    def test_obfuscated_font_is_ignored_and_all_non_linear_spine_fails_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; out = root / "out.html"
            fixture(epub, font_encrypted=True)
            run, summary = self.run_converter(epub, out)
            self.assertEqual(0, run.returncode); self.assertEqual("success", summary["status"])
            out.write_text("keep", encoding="utf-8")
            fixture(epub, all_non_linear=True)
            run, error = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(1, run.returncode); self.assertEqual("unreadable-spine", error["code"])
            self.assertEqual("keep", out.read_text(encoding="utf-8"))

    def test_no_readable_text_fails_without_replacing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "empty.epub"; out = root / "out.html"; unreadable_fixture(epub); out.write_text("keep", encoding="utf-8")
            run, error = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(1, run.returncode); self.assertEqual("unreadable-content", error["code"])
            self.assertEqual("keep", out.read_text(encoding="utf-8"))

    def test_explicit_optional_parser_is_classified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; fixture(epub); out = root / "out.html"
            run, summary = self.run_converter(epub, out, "--parser", "ebooklib")
            if run.returncode:
                self.assertEqual("parser-unavailable", summary["code"])
            else:
                self.assertEqual("ebooklib", summary["parser"])

    def test_navigation_fallback_fixed_layout_and_malformed_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; out = root / "out.html"
            fixture(epub, nav=False, fixed=True)
            run, summary = self.run_converter(epub, out)
            self.assertEqual(0, run.returncode, summary); self.assertEqual("headings", summary["navigation_source"])
            self.assertIn("fixed-layout-poor-fit", summary["warnings"])
            fixture(epub, malformed=True)
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(1, run.returncode); self.assertEqual("malformed-content", summary["code"])
            run, summary = self.run_converter(epub, out)
            if importlib.util.find_spec("ebooklib") and importlib.util.find_spec("bs4"):
                self.assertEqual(1, run.returncode); self.assertEqual("parser-disagreement", summary["code"])
            else:
                self.assertEqual(1, run.returncode); self.assertEqual("malformed-content", summary["code"])

    def test_adapter_output_parity_when_optional_dependencies_exist(self):
        if not (importlib.util.find_spec("ebooklib") and importlib.util.find_spec("bs4")):
            self.skipTest("optional parser unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; fixture(epub)
            outputs = []
            for parser in ("stdlib", "ebooklib", "auto"):
                out = root / (parser + ".html"); run, _ = self.run_converter(epub, out, "--parser", parser)
                self.assertEqual(0, run.returncode); outputs.append(hashlib.sha256(out.read_bytes()).digest())
            self.assertEqual([outputs[0]] * 3, outputs)

    def test_transitive_cyclic_non_linear_closure_and_duplicate_spine_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "closure.epub"; out = root / "closure.html"; closure_fixture(epub)
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertEqual(4, summary["chapters"])
            self.assertIn("ambiguous-href-target:one.xhtml", summary["warnings"])
            result = out.read_text(encoding="utf-8")
            self.assertIn('id="ch-0003-note"', result); self.assertIn('id="ch-0004-deep"', result)
            self.assertIn('href="#ch-0001-first">back</a>', result)
            self.assertIn('id="ch-0002-first"', result)

    def test_large_text_warns_and_still_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "large.epub"; out = root / "large.html"; closure_fixture(epub, large=True)
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertTrue(out.exists())
            self.assertIn("large-text-over-5000000-bytes", summary["warnings"])

    def test_nav_precedes_ncx_and_flattens_deeper_items_without_rail_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "nav.epub"; out = root / "nav.html"; closure_fixture(epub, with_navigation=True)
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertEqual("nav", summary["navigation_source"])
            result = out.read_text(encoding="utf-8")
            self.assertIn("NAV Wins", result); self.assertNotIn("NCX Must Lose", result)
            self.assertIn('href="#ch-0001-sub">Sub nav</a>', result)
            self.assertIn('href="#ch-0001-deep-anchor">Deep nav</a>', result)
            self.assertIn('<ol class="toc-sub"><li><a href="#ch-0001-sub">Sub nav</a></li><li><a href="#ch-0001-deep-anchor">Deep nav</a></li></ol>', result)

    def test_auto_fails_atomically_when_adapters_disagree(self):
        if not (importlib.util.find_spec("ebooklib") and importlib.util.find_spec("bs4")):
            self.skipTest("optional parser unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; out = root / "out.html"; fixture(epub); out.write_text("existing", encoding="utf-8")
            stdout = io.StringIO()
            with patch.object(converter, "parse_body_ebooklib", return_value=([converter.Node("p", text="different")], False)), redirect_stdout(stdout):
                status = converter.main([str(epub), "--out", str(out), "--parser", "auto"])
            self.assertEqual(1, status); self.assertEqual("existing", out.read_text(encoding="utf-8"))
            self.assertEqual("parser-disagreement", json.loads(stdout.getvalue())["code"])

    def test_invalid_or_missing_linear_spine_content_fails(self):
        metadata = '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Broken</dc:title></metadata>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = {
                "missing-manifest": (f'<package xmlns="http://www.idpf.org/2007/opf">{metadata}<manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="ghost"/></spine></package>', {"one.xhtml": '<html><body><p>Readable.</p></body></html>'}),
                "missing-file": (f'<package xmlns="http://www.idpf.org/2007/opf">{metadata}<manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>', {}),
            }
            for name, (opf, documents) in cases.items():
                with self.subTest(name=name):
                    epub = root / f"{name}.epub"; out = root / f"{name}.html"
                    custom_fixture(epub, opf, documents)
                    run, error = self.run_converter(epub, out, "--parser", "stdlib")
                    self.assertEqual(1, run.returncode); self.assertEqual("unreadable-spine", error["code"])
                    self.assertFalse(out.exists())

    def test_unlinked_malformed_non_linear_content_is_omitted(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Selective</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="bad" href="bad.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="bad" linear="no"/></spine></package>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "selective.epub"; out = root / "selective.html"
            custom_fixture(epub, opf, {"one.xhtml": '<html><body><h1>Good</h1><p>Readable.</p></body></html>', "bad.xhtml": '<html><body><p>broken</body>'})
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertEqual(1, summary["chapters"])
            self.assertNotIn("broken", out.read_text(encoding="utf-8"))

    def test_malformed_nav_warns_and_falls_back_to_heading_navigation(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fallback</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="one"/></spine></package>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "fallback.epub"; out = root / "fallback.html"
            custom_fixture(epub, opf, {"one.xhtml": '<html><body><h1>Chapter</h1><p>Readable.</p></body></html>', "nav.xhtml": '<html><body><nav><ol><li>broken</nav>'})
            run, summary = self.run_converter(epub, out)
            self.assertEqual(0, run.returncode, summary); self.assertEqual("headings", summary["navigation_source"])
            self.assertIn("nav-unreadable", summary["warnings"])

    def test_linked_non_linear_duplicate_is_included_once(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Duplicates</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="note" href="note.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="note" linear="no"/><itemref idref="note" linear="no"/></spine></package>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "duplicates.epub"; out = root / "duplicates.html"
            custom_fixture(epub, opf, {"one.xhtml": '<html><body><p>Main <a href="note.xhtml#n">note</a>.</p></body></html>', "note.xhtml": '<html><body><aside id="n">Only once.</aside></body></html>'})
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertEqual(2, summary["chapters"])
            self.assertEqual(1, out.read_text(encoding="utf-8").count("Only once."))

    def test_local_url_canonicalization_and_unresolved_link_removal(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Links</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="two" linear="no"/></spine></package>'
        one = '<html><body><p><a href="two.xhtml?edition=1#end%20note">query</a><a href="%74wo.xhtml#end%20note">encoded</a><a href="missing.xhtml#x">missing</a></p></body></html>'
        two = '<html><body><p id="end note">Target.</p></body></html>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "links.epub"; out = root / "links.html"
            custom_fixture(epub, opf, {"one.xhtml": one, "two.xhtml": two})
            run, _ = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode)
            result = out.read_text(encoding="utf-8")
            self.assertEqual(2, result.count('href="#ch-0002-end-note"'))
            self.assertNotRegex(result, r'<a[^>]+href="[^"]+"[^>]*>missing</a>')

    def test_resource_fallback_text_empty_wrappers_and_live_url_cleanup(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Cleanup</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>'
        body = '<html><body><object data="x">Object fallback</object><picture><img src="x" alt="Cover description"/></picture><figure><img src="x"/></figure><form action="https://example.com/post"><button formaction=" https://example.com/button">Go</button></form><a href=" https://example.com" ping="https://tracker.example">Remote</a></body></html>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "cleanup.epub"; out = root / "cleanup.html"
            custom_fixture(epub, opf, {"one.xhtml": body})
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode)
            result = out.read_text(encoding="utf-8")
            self.assertIn("Object fallback", result); self.assertIn("Cover description", result)
            self.assertNotIn("<figure>", result); self.assertNotIn("example.com", result); self.assertNotIn(" ping=", result)
            self.assertGreaterEqual(summary["omissions"]["remote_references"], 4)

    def test_explicit_ebooklib_rejects_malformed_markup_without_parity(self):
        if not (importlib.util.find_spec("ebooklib") and importlib.util.find_spec("bs4")):
            self.skipTest("optional parser unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "malformed.epub"; out = root / "malformed.html"; fixture(epub, malformed=True)
            run, error = self.run_converter(epub, out, "--parser", "ebooklib")
            self.assertEqual(1, run.returncode); self.assertEqual("malformed-content", error["code"])

    def test_normalized_ir_includes_navigation_and_warning_state(self):
        book = converter.Book("Title", None, {}, [], "book.opf", None, None, False)
        parsed = {"one.xhtml": [converter.Node("p", text="Text")]}
        baseline = converter.normalized_ir(book, parsed, "headings", [], [])
        self.assertNotEqual(baseline, converter.normalized_ir(book, parsed, "nav", [], []))
        self.assertNotEqual(baseline, converter.normalized_ir(book, parsed, "headings", [("one.xhtml", "", "One", 1)], []))
        self.assertNotEqual(baseline, converter.normalized_ir(book, parsed, "headings", [], ["warning"]))

    def test_heading_fallback_builds_two_level_toc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "headings.epub"; out = root / "headings.html"; closure_fixture(epub)
            run, summary = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode); self.assertEqual("headings", summary["navigation_source"])
            result = out.read_text(encoding="utf-8")
            self.assertIn('<ol class="toc-sub"><li><a href="#ch-0001-sub">Sub heading</a></li></ol>', result)
            self.assertIn('<ol class="toc-sub"><li><a href="#ch-0002-sub">Sub heading</a></li></ol>', result)

    def test_converter_owned_word_counts_are_not_overwritten(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('if (!ch.dataset.words) ch.dataset.words = String(n);', template)
        self.assertIn('var declared = Number(ch.dataset.words);', template)

    def test_custom_template_option_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; out = root / "book.html"; custom = root / "custom.html"; fixture(epub)
            custom.write_text(TEMPLATE.read_text(encoding="utf-8").replace("</head>", "<!-- custom-template-marker --></head>"), encoding="utf-8")
            run, _ = self.run_converter(epub, out, "--parser", "stdlib", "--template", str(custom))
            self.assertEqual(0, run.returncode); self.assertIn("custom-template-marker", out.read_text(encoding="utf-8"))

    def test_checked_in_real_epub_corpus(self):
        real = ROOT / "src/epub-html/tests/fixtures/real"
        expected_navigation = {"gutenberg-classic.epub": None, "footnotes-tables.epub": None, "no-nav.epub": "ncx"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, navigation in expected_navigation.items():
                with self.subTest(name=name):
                    out = root / f"{name}.html"
                    run, summary = self.run_converter(real / name, out, "--parser", "stdlib")
                    self.assertEqual(0, run.returncode, run.stdout + run.stderr)
                    self.assertGreater(summary["chapters"], 0); self.assertGreater(summary["words"], 0)
                    if navigation: self.assertEqual(navigation, summary["navigation_source"])
                    self.assertTrue(out.read_text(encoding="utf-8").lower().startswith("<!doctype html>"))

    def test_modal_sheet_interactions_in_headless_browser(self):
        browser = find_headless_browser()
        if browser is None:
            self.skipTest("Chrome/Edge/Chromium unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); epub = root / "book.epub"; out = root / "book.html"; fixture(epub)
            run, _ = self.run_converter(epub, out, "--parser", "stdlib")
            self.assertEqual(0, run.returncode)
            probe = '''<script>(function(){var menu=document.querySelector("[data-menu]");var side=document.getElementById("sidebar");var scrim=document.querySelector("[data-scrim]");var page=document.querySelector(".page");menu.click();var opened=side.classList.contains("is-open")&&menu.getAttribute("aria-expanded")==="true"&&!side.hasAttribute("inert")&&page.hasAttribute("inert")&&!scrim.hidden;document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));var closed=!side.classList.contains("is-open")&&menu.getAttribute("aria-expanded")==="false"&&side.hasAttribute("inert")&&!page.hasAttribute("inert")&&scrim.hidden;document.body.setAttribute("data-modal-probe",opened&&closed?"pass":"fail");})();</script>'''
            out.write_text(out.read_text(encoding="utf-8").replace("</body>", probe + "</body>"), encoding="utf-8")
            profile = root / "browser-profile"
            browser_run = subprocess.run([browser, "--headless", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", "--dump-dom", out.as_uri()], text=True, capture_output=True, check=False, timeout=45)
            self.assertEqual(0, browser_run.returncode, browser_run.stderr)
            self.assertIn('data-modal-probe="pass"', browser_run.stdout)


if __name__ == "__main__":
    unittest.main()
