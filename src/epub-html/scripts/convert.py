#!/usr/bin/env python3
"""Deterministically turn a trusted EPUB into the standalone reader template."""
from __future__ import annotations

import argparse
import copy
import html
import json
import math
import os
import posixpath
import re
import sys
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

EPUB_NS = "http://www.idpf.org/2007/ops"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XHTML_NS = "http://www.w3.org/1999/xhtml"
RESOURCE_TAGS = {"img", "picture", "source", "svg", "audio", "video", "canvas", "iframe", "object", "embed"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
RESOURCE_ATTRS = {"src", "srcset", "poster", "data", "background"}
LIVE_URL_ATTRS = {"action", "formaction", "ping"}
EMPTY_RESOURCE_WRAPPERS = {"aside", "div", "figure", "p", "section", "span"}


class ConversionError(Exception):
    def __init__(self, code: str, message: str, warnings: list[str] | None = None):
        super().__init__(message)
        self.code, self.message, self.warnings = code, message, warnings or []


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    text: str = ""
    children: list["Node"] = field(default_factory=list)
    tail: str = ""


@dataclass
class ManifestItem:
    ident: str
    href: str
    media_type: str
    properties: str = ""


@dataclass
class SpineItem:
    manifest: ManifestItem
    linear: bool


@dataclass
class Book:
    title: str
    author: str | None
    manifest: dict[str, ManifestItem]
    spine: list[SpineItem]
    opf_path: str
    nav_href: str | None
    ncx_href: str | None
    fixed_layout: bool


def local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def qname(value: str) -> str:
    if not value.startswith("{"):
        return value.lower()
    namespace, name = value[1:].split("}", 1)
    if namespace == EPUB_NS:
        return "epub:" + name.lower()
    if namespace == XML_NS:
        return "xml:" + name.lower()
    return name.lower()


def posix_norm(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/")).lstrip("./")


def href_parts(href: str) -> tuple[str, str]:
    parsed = urlsplit(href.strip())
    return unquote(parsed.path), unquote(parsed.fragment)


def relative_path(base: str, href: str) -> str:
    path, _ = href_parts(href)
    return posix_norm(posixpath.join(posixpath.dirname(base), path))


def is_remote(value: str) -> bool:
    value = value.strip()
    return bool(re.match(r"(?:[a-z][a-z0-9+.-]*:|//)", value, re.I)) and not value.lower().startswith("data:")


def slugify(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-") or "untitled"


def text_words(value: str) -> int:
    return len(re.findall(r"\S+", value))


def node_text(node: Node) -> str:
    return node.text + "".join(node_text(child) for child in node.children) + node.tail


def find_all(node: Node, tags: set[str]) -> Iterable[Node]:
    if node.tag in tags:
        yield node
    for child in node.children:
        yield from find_all(child, tags)


def element_to_node(element: ET.Element) -> Node:
    node = Node(qname(element.tag), {qname(k): v for k, v in element.attrib.items()}, element.text or "")
    for child in element:
        child_node = element_to_node(child)
        child_node.tail = child.tail or ""
        node.children.append(child_node)
    return node


class BodyParser(HTMLParser):
    """Deliberately small recovery parser used only after XML parsing fails."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.in_body = False
        self.seen_body = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        if tag == "body":
            self.in_body, self.seen_body = True, True
            return
        if not self.in_body and self.seen_body:
            return
        if self.in_body or not self.seen_body:
            node = Node(tag, {k.lower(): v or "" for k, v in attrs})
            self.stack[-1].children.append(node)
            if tag not in VOID_TAGS:
                self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag == "body":
            self.in_body = False
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str):
        if self.in_body or not self.seen_body:
            self.stack[-1].children.append(Node("#tail", text=data))


def parse_body_stdlib(raw: bytes, path: str, allow_recovery: bool) -> tuple[list[Node], bool]:
    try:
        root = ET.fromstring(raw)
        body = next((el for el in root.iter() if local_name(el.tag) == "body"), None)
        if body is None:
            raise ConversionError("unreadable-content", f"No body element in {path}")
        nodes: list[Node] = []
        if body.text:
            nodes.append(Node("#tail", text=body.text))
        for child in body:
            nodes.append(element_to_node(child))
        return nodes, False
    except ET.ParseError as error:
        if not allow_recovery:
            raise ConversionError("malformed-content", f"Malformed body markup in {path}: {error}")
        parser = BodyParser()
        parser.feed(raw.decode("utf-8", "replace"))
        parser.close()
        if not parser.root.children:
            raise ConversionError("unreadable-content", f"No recoverable body markup in {path}")
        return parser.root.children, True


def parse_body_ebooklib(raw: bytes, path: str, allow_recovery: bool) -> tuple[list[Node], bool]:
    """A Beautiful Soup XML adapter, deliberately independent of ElementTree."""
    from bs4 import BeautifulSoup, NavigableString, Tag

    recovered = False
    try:
        ET.fromstring(raw)
    except ET.ParseError as error:
        if not allow_recovery:
            raise ConversionError("malformed-content", f"Malformed body markup in {path}: {error}")
        recovered = True

    soup = BeautifulSoup(raw, "xml")
    body = soup.find("body")
    if body is None:
        raise ConversionError("unreadable-content", f"No body element in {path}")

    def to_node(value):
        if isinstance(value, NavigableString):
            return Node("#tail", text=str(value))
        if not isinstance(value, Tag):
            return None
        attrs = {
            str(key).lower(): " ".join(value) if isinstance(value, list) else str(value)
            for key, value in value.attrs.items()
            if str(key).lower() != "xmlns" and not str(key).lower().startswith("xmlns:")
        }
        node = Node(value.name.lower(), attrs)
        children = [to_node(child) for child in value.contents]
        node.children = [child for child in children if child is not None]
        return node

    nodes = [to_node(child) for child in body.contents]
    nodes = [node for node in nodes if node is not None]
    if not nodes:
        raise ConversionError("unreadable-content", f"No recoverable body markup in {path}")
    return nodes, recovered


def load_ebooklib_book(input_path: Path, tolerate_navigation_failure: bool = False) -> None:
    """Exercise EbookLib's package/spine loader before its BS4 body adapter runs."""
    from ebooklib import epub
    try:
        loaded = epub.read_epub(str(input_path), options={"ignore_ncx": False})
        if not list(loaded.get_items()):
            raise ValueError("EPUB contains no items")
    except Exception as error:
        if tolerate_navigation_failure:
            return
        raise ConversionError("unreadable-package", f"EbookLib could not read EPUB: {error}")


def parse_opf(archive: zipfile.ZipFile) -> Book:
    try:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next((x.attrib.get("full-path") for x in container.iter() if local_name(x.tag) == "rootfile"), None)
        if not rootfile:
            raise ValueError("rootfile missing")
        opf_path = posix_norm(rootfile)
        package = ET.fromstring(archive.read(opf_path))
    except (KeyError, ET.ParseError, ValueError) as error:
        raise ConversionError("unreadable-package", f"Could not read EPUB package data: {error}")
    metadata = next((x for x in package if local_name(x.tag) == "metadata"), None)
    title = "Untitled"
    author = None
    if metadata is not None:
        for child in metadata.iter():
            if local_name(child.tag) == "title" and (child.text or "").strip():
                title = (child.text or "").strip(); break
        for child in metadata.iter():
            if local_name(child.tag) in {"creator", "author"} and (child.text or "").strip():
                author = (child.text or "").strip(); break
    manifest_element = next((x for x in package if local_name(x.tag) == "manifest"), None)
    spine_element = next((x for x in package if local_name(x.tag) == "spine"), None)
    if manifest_element is None or spine_element is None:
        raise ConversionError("unreadable-package", "EPUB package has no manifest or spine")
    manifest: dict[str, ManifestItem] = {}
    nav_href = ncx_href = None
    for item in manifest_element:
        ident, href = item.attrib.get("id"), item.attrib.get("href")
        if not ident or not href:
            continue
        record = ManifestItem(ident, relative_path(opf_path, href), item.attrib.get("media-type", ""), item.attrib.get("properties", ""))
        manifest[ident] = record
        if "nav" in record.properties.split(): nav_href = record.href
        if record.media_type == "application/x-dtbncx+xml": ncx_href = record.href
    spine: list[SpineItem] = []
    for itemref in spine_element:
        ident = itemref.attrib.get("idref")
        linear = itemref.attrib.get("linear", "yes").lower() != "no"
        if not ident or ident not in manifest:
            if linear:
                raise ConversionError("unreadable-spine", "Linear spine references a missing manifest item")
            continue
        spine.append(SpineItem(manifest[ident], linear))
    if not spine or not any(x.linear for x in spine):
        raise ConversionError("unreadable-spine", "EPUB has an empty or all-non-linear spine")
    fixed = any(
        local_name(node.tag) == "meta"
        and node.attrib.get("property", "").lower() == "rendition:layout"
        and (node.text or node.attrib.get("content", "")).strip().lower() == "pre-paginated"
        for node in package.iter()
    )
    return Book(title, author, manifest, spine, opf_path, nav_href, ncx_href, fixed)


def encrypted_content(archive: zipfile.ZipFile, book: Book) -> bool:
    try: encryption = ET.fromstring(archive.read("META-INF/encryption.xml"))
    except KeyError: return False
    except ET.ParseError: return False
    hrefs = {item.href for item in book.manifest.values() if "html" in item.media_type or "xhtml" in item.media_type}
    return any(posix_norm((next((x.attrib.get("URI") for x in node.iter() if local_name(x.tag) == "cipherreference"), ""))) in hrefs for node in encryption.iter() if local_name(node.tag) == "encrypteddata")


def is_content(item: ManifestItem) -> bool:
    return "html" in item.media_type or "xhtml" in item.media_type or item.href.lower().endswith((".xhtml", ".html", ".htm"))


def local_link_targets(nodes: list[Node], source: str) -> set[str]:
    targets = set()
    for root in nodes:
        for node in find_all(root, {"a"}):
            href = node.attrs.get("href", "")
            if href and not href.startswith("#") and not is_remote(href):
                target = relative_path(source, href)
                if target: targets.add(target)
    return targets


def select_occurrences(book: Book, parsed: dict[str, list[Node]]) -> list[SpineItem]:
    selected_non_linear = {href for href in parsed if not any(item.linear and item.manifest.href == href for item in book.spine)}
    emitted_non_linear: set[str] = set()
    occurrences: list[SpineItem] = []
    for item in book.spine:
        href = item.manifest.href
        if item.linear:
            occurrences.append(item)
        elif href in selected_non_linear and href not in emitted_non_linear:
            emitted_non_linear.add(href)
            occurrences.append(item)
    return occurrences


def clean_nodes(nodes: list[Node], omissions: dict[str, int]) -> list[Node]:
    def contains_resource(node: Node) -> bool:
        return node.tag in RESOURCE_TAGS or any(contains_resource(child) for child in node.children)

    def fallback_text(node: Node) -> str:
        if node.tag == "#tail":
            return node.text + node.tail
        parts = [node.text]
        if node.attrs.get("alt"):
            parts.append(node.attrs["alt"])
        parts.extend(fallback_text(child) for child in node.children)
        parts.append(node.tail)
        return "".join(parts)

    def inner_text(node: Node) -> str:
        return node.text + "".join(node_text(child) for child in node.children)

    def clean(node: Node) -> Node | None:
        if node.tag == "#tail": return copy.deepcopy(node)
        if node.tag in RESOURCE_TAGS:
            key = "images" if node.tag in {"img", "picture", "svg"} else "multimedia" if node.tag in {"audio", "video", "source", "canvas"} else "embeds"
            omissions[key] += 1
            return Node("#tail", text=fallback_text(node))
        if node.tag in {"script", "style"}:
            omissions["styles"] += 1
            return Node("#tail", text=node.tail)
        if node.tag == "link" and "stylesheet" in node.attrs.get("rel", "").lower():
            omissions["styles"] += 1
            return Node("#tail", text=node.tail)
        attrs: dict[str, str] = {}
        for key, value in node.attrs.items():
            low = key.lower()
            if low == "style" or low.startswith("on"):
                omissions["styles"] += 1; continue
            if low in RESOURCE_ATTRS:
                omissions["images"] += 1; continue
            if low == "href" and is_remote(value):
                omissions["remote_references"] += 1; continue
            if low in LIVE_URL_ATTRS and (low == "ping" or is_remote(value)):
                omissions["remote_references"] += 1; continue
            attrs[key] = value
        output = Node(node.tag, attrs, node.text, tail=node.tail)
        for child in node.children:
            result = clean(child)
            if result is not None: output.children.append(result)
        if (
            node.tag in EMPTY_RESOURCE_WRAPPERS
            and contains_resource(node)
            and not inner_text(output).strip()
            and "id" not in output.attrs
        ):
            return Node("#tail", text=output.tail)
        return output
    return [x for node in nodes if (x := clean(node)) is not None]


def rewrite_nodes(nodes: list[Node], source: str, occurrence: str, target_sections: dict[str, str], first_ids: dict[tuple[str, str], str], warnings: list[str]) -> None:
    used: set[str] = set()
    def walk(node: Node):
        if node.tag == "#tail": return
        old_id = node.attrs.get("id")
        if old_id:
            base = f"{occurrence}-{slugify(old_id)}"
            new = base; suffix = 2
            while new in used:
                new = f"{base}-{suffix}"; suffix += 1
            used.add(new); node.attrs["id"] = new
            first_ids.setdefault((source, old_id), new)
        href = node.attrs.get("href")
        if href is not None and not is_remote(href):
            path, fragment = href_parts(href)
            target = source if not path else relative_path(source, href)
            if target in target_sections:
                if fragment and (target, fragment) in first_ids:
                    node.attrs["href"] = "#" + first_ids[(target, fragment)]
                elif fragment:
                    # Forward targets are fixed in a second deterministic pass.
                    node.attrs["data-epub-link"] = target + "#" + fragment
                else: node.attrs["href"] = "#" + target_sections[target]
            else:
                node.attrs.pop("href", None)
        for child in node.children: walk(child)
    for node in nodes: walk(node)


def finish_links(nodes: list[Node], first_ids: dict[tuple[str, str], str]) -> None:
    def walk(node: Node):
        if node.tag == "#tail": return
        pending = node.attrs.pop("data-epub-link", None)
        if pending:
            target, _, fragment = pending.partition("#")
            if (target, fragment) in first_ids: node.attrs["href"] = "#" + first_ids[(target, fragment)]
            else: node.attrs.pop("href", None)
        for child in node.children: walk(child)
    for node in nodes: walk(node)


def serialize(node: Node) -> str:
    if node.tag == "#tail": return html.escape(node.text, quote=False)
    attrs = "".join(f' {key}="{html.escape(value, quote=True)}"' for key, value in sorted(node.attrs.items()))
    if node.tag in VOID_TAGS: return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>{html.escape(node.text, quote=False)}{''.join(serialize(x) for x in node.children)}</{node.tag}>{html.escape(node.tail, quote=False)}"


def first_heading(nodes: list[Node], fallback: str) -> str:
    for node in nodes:
        for heading in find_all(node, {"h1", "h2"}):
            value = re.sub(r"\s+", " ", node_text(heading)).strip()
            if value: return value
    return fallback


def heading_fallback(nodes: list[Node], section: str, fallback: str) -> tuple[str, list[tuple[str, str]]]:
    headings = [heading for node in nodes for heading in find_all(node, {"h1", "h2"})]
    if not headings:
        return fallback, []
    label = re.sub(r"\s+", " ", node_text(headings[0])).strip() or fallback
    used_ids = {node.attrs["id"] for root in nodes for node in find_all(root, {"h1", "h2"}) if node.attrs.get("id")}
    subitems: list[tuple[str, str]] = []
    for index, heading in enumerate(headings[1:], 1):
        if heading.tag != "h2":
            continue
        text = re.sub(r"\s+", " ", node_text(heading)).strip()
        if not text:
            continue
        anchor = heading.attrs.get("id")
        if not anchor:
            base = f"{section}-heading-{index:02d}"
            anchor = base
            suffix = 2
            while anchor in used_ids:
                anchor = f"{base}-{suffix}"
                suffix += 1
            heading.attrs["id"] = anchor
            used_ids.add(anchor)
        subitems.append((anchor, text))
    return label, subitems


def parse_navigation(archive: zipfile.ZipFile, book: Book, warnings: list[str]) -> tuple[str, list[tuple[str, str, str, int]]]:
    """Return navigation provenance and source/fragment/label/depth records."""
    def records(root: ET.Element, source: str, ncx: bool = False) -> list[tuple[str, str, str, int]]:
        parent = {child: node for node in root.iter() for child in node}
        output: list[tuple[str, str, str, int]] = []
        for anchor in root.iter():
            if local_name(anchor.tag) != ("content" if ncx else "a"):
                continue
            if ncx:
                href = anchor.attrib.get("src", "")
                point = parent.get(anchor)
                while point is not None and local_name(point.tag) != "navpoint": point = parent.get(point)
                label = next((re.sub(r"\s+", " ", "".join(x.itertext())).strip() for x in point.iter() if local_name(x.tag) == "text"), "") if point is not None else ""
                depth = sum(1 for x in parent_chain(point, parent) if local_name(x.tag) == "navpoint")
            else:
                href = anchor.attrib.get("href", "")
                label = re.sub(r"\s+", " ", "".join(anchor.itertext())).strip()
                depth = sum(1 for x in parent_chain(anchor, parent) if local_name(x.tag) == "ol")
            if href and label and not is_remote(href):
                path, fragment = href_parts(href)
                output.append((relative_path(source, href) if path else source, fragment, label, max(1, depth)))
        return output

    def parent_chain(node: ET.Element | None, parent: dict[ET.Element, ET.Element]) -> Iterable[ET.Element]:
        while node is not None:
            yield node
            node = parent.get(node)

    if book.nav_href:
        try:
            root = ET.fromstring(archive.read(book.nav_href))
            nav = next((x for x in root.iter() if local_name(x.tag) == "nav" and ("toc" in x.attrib.get("{" + EPUB_NS + "}type", "") or x.attrib.get("role") == "doc-toc")), None)
            labels = records(nav, book.nav_href) if nav is not None else []
            if labels: return "nav", labels
        except (KeyError, ET.ParseError): warnings.append("nav-unreadable")
    if book.ncx_href:
        try:
            root = ET.fromstring(archive.read(book.ncx_href))
            labels = records(root, book.ncx_href, ncx=True)
            if labels: return "ncx", labels
        except (KeyError, ET.ParseError): warnings.append("ncx-unreadable")
    return "headings", []


def replace_slot(template: str, slot: str, value: str) -> str:
    opener = re.search(rf'<([A-Za-z][\w:-]*)\b[^>]*\bdata-slot="{re.escape(slot)}"[^>]*>', template, re.I)
    if opener is None:
        raise ConversionError("invalid-template", f"Template has no {slot!r} slot")
    tag = opener.group(1)
    depth, position = 1, opener.end()
    token = re.compile(rf'</?{re.escape(tag)}\b[^>]*>', re.I)
    while (match := token.search(template, position)) is not None:
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return template[:opener.end()] + value + template[match.start():]
        elif not match.group(0).rstrip().endswith("/>"):
            depth += 1
        position = match.end()
    raise ConversionError("invalid-template", f"Template has an unclosed {slot!r} slot")


def replace_text_slots(template: str, slot: str, value: str) -> str:
    pattern = re.compile(rf'(<(?P<tag>[A-Za-z][\w:-]*)\b[^>]*\bdata-slot="{re.escape(slot)}"[^>]*>).*?(</(?P=tag)\s*>)', re.I | re.S)
    replaced, count = pattern.subn(lambda match: match.group(1) + value + match.group(3), template)
    if not count: raise ConversionError("invalid-template", f"Template has no {slot!r} slot")
    return replaced


def build_html(template: str, book: Book, chunks: list[tuple[str, str, str, int]], subitems: dict[str, list[tuple[str, str]]]) -> str:
    title = html.escape(book.title)
    author = html.escape(book.author or "")
    total = sum(x[3] for x in chunks)
    facts = f'{len(chunks)} chapters · {total} words · {max(1, math.ceil(total / 250))} min'
    toc = ['<li class="toc-front" data-target="title"><a href="#title">Title</a></li>']
    chapters = []
    for index, (section_id, label, body, words) in enumerate(chunks, 1):
        children = "".join(f'<li><a href="#{anchor}">{html.escape(text)}</a></li>' for anchor, text in subitems.get(section_id, []))
        nested = f'<ol class="toc-sub">{children}</ol>' if children else ""
        toc.append(f'<li class="toc-ch" data-target="{section_id}" data-words="{words}"><a href="#{section_id}"><span class="book-rail" aria-hidden="true"></span><span class="toc-meta"><span class="toc-num">{index:02d}</span><span class="toc-label">{html.escape(label)}</span></span></a>{nested}</li>')
        chapters.append(f'<section class="reader-chapter" id="{section_id}" data-words="{words}"><p class="chapter-kicker">{index:02d}</p>{body}</section>')
    template = replace_text_slots(template, "head-title", title + (" — " + author if author else ""))
    template = replace_text_slots(template, "title", title)
    template = replace_text_slots(template, "author", author)
    template = replace_text_slots(template, "facts", html.escape(facts))
    template = template.replace('data-slot="facts"', 'data-slot="facts" data-converter-owned="true"', 1)
    template = replace_slot(template, "toc", "".join(toc))
    template = replace_slot(template, "chapters", "".join(chapters))
    return template.replace("\r\n", "\n").replace("\r", "\n")


def optional_available() -> bool:
    try:
        import ebooklib  # noqa: F401
        import bs4  # noqa: F401
        return True
    except ImportError: return False


def parse_documents(archive: zipfile.ZipFile, book: Book, adapter: str, allow_recovery: bool) -> tuple[dict[str, list[Node]], bool]:
    """Parse the linear spine and the transitive closure of linked non-linear spine items."""
    parsed: dict[str, list[Node]] = {}
    recovered = False
    spine_by_href: dict[str, ManifestItem] = {}
    for occurrence in book.spine:
        if is_content(occurrence.manifest):
            spine_by_href.setdefault(occurrence.manifest.href, occurrence.manifest)
        elif occurrence.linear:
            raise ConversionError("unreadable-spine", f"Unsupported linear spine content: {occurrence.manifest.href}")
    frontier = list(dict.fromkeys(item.manifest.href for item in book.spine if item.linear))
    queued = set(frontier)
    while frontier:
        href = frontier.pop(0)
        item = spine_by_href[href]
        try:
            raw = archive.read(item.href)
        except KeyError:
            raise ConversionError("unreadable-spine", f"Missing spine content: {item.href}")
        if adapter == "stdlib":
            nodes, did_recover = parse_body_stdlib(raw, item.href, allow_recovery)
        else:
            nodes, did_recover = parse_body_ebooklib(raw, item.href, allow_recovery)
        parsed[item.href] = nodes
        recovered = recovered or did_recover
        for target in sorted(local_link_targets(nodes, item.href)):
            if target in spine_by_href and target not in queued:
                queued.add(target)
                frontier.append(target)
    return parsed, recovered


def normalized_ir(
    book: Book,
    parsed: dict[str, list[Node]],
    navigation: str,
    nav_records: list[tuple[str, str, str, int]],
    warnings: list[str],
) -> tuple:
    """Canonical comparison unit: package, content, navigation, and warning state."""
    return (
        book.title,
        book.author,
        tuple((item.manifest.href, item.linear) for item in book.spine),
        tuple((path, "".join(serialize(node) for node in nodes)) for path, nodes in sorted(parsed.items())),
        navigation,
        tuple(nav_records),
        tuple(warnings),
    )


def convert(input_path: Path, template_path: Path, parser_name: str) -> tuple[str, dict]:
    if parser_name == "ebooklib" and not optional_available():
        raise ConversionError("parser-unavailable", "ebooklib and beautifulsoup4 are not installed")
    if not input_path.is_file(): raise ConversionError("input-not-found", f"Input EPUB not found: {input_path}")
    try: archive = zipfile.ZipFile(input_path)
    except (OSError, zipfile.BadZipFile) as error: raise ConversionError("invalid-epub", f"Could not open EPUB: {error}")
    with archive:
        book = parse_opf(archive)
        if encrypted_content(archive, book): raise ConversionError("encrypted-content", "EPUB content documents are encrypted")
        warnings: list[str] = ["fixed-layout-poor-fit"] if book.fixed_layout else []
        navigation, nav_records = parse_navigation(archive, book, warnings)
        tolerate_navigation_failure = any(warning in {"nav-unreadable", "ncx-unreadable"} for warning in warnings)
        recovered = False
        if parser_name == "ebooklib":
            load_ebooklib_book(input_path, tolerate_navigation_failure)
            parsed, recovered = parse_documents(archive, book, "ebooklib", False)
        elif parser_name == "auto" and optional_available():
            stdlib_parsed, stdlib_recovered = parse_documents(archive, book, "stdlib", True)
            load_ebooklib_book(input_path, tolerate_navigation_failure)
            ebooklib_parsed, ebooklib_recovered = parse_documents(archive, book, "ebooklib", True)
            stdlib_warnings = warnings + (["malformed-body-recovered"] if stdlib_recovered else [])
            ebooklib_warnings = warnings + (["malformed-body-recovered"] if ebooklib_recovered else [])
            if normalized_ir(book, stdlib_parsed, navigation, nav_records, stdlib_warnings) != normalized_ir(book, ebooklib_parsed, navigation, nav_records, ebooklib_warnings):
                raise ConversionError("parser-disagreement", "stdlib and EbookLib/Beautiful Soup produced different normalized IR")
            parsed, recovered = stdlib_parsed, stdlib_recovered or ebooklib_recovered
        else:
            parsed, recovered = parse_documents(archive, book, "stdlib", False)
        occurrences = select_occurrences(book, parsed)
        if not occurrences: raise ConversionError("unreadable-spine", "No readable linear spine content")
        target_sections: dict[str, str] = {}
        for index, item in enumerate(occurrences, 1): target_sections.setdefault(item.manifest.href, f"ch-{index:04d}")
        for href in sorted({item.manifest.href for item in occurrences}):
            if sum(item.manifest.href == href for item in occurrences) > 1:
                warnings.append(f"ambiguous-href-target:{href}")
        omissions = {"images": 0, "multimedia": 0, "embeds": 0, "styles": 0, "remote_references": 0}
        first_ids: dict[tuple[str, str], str] = {}
        prepared: list[tuple[str, str, list[Node]]] = []
        for index, item in enumerate(occurrences, 1):
            source = item.manifest.href; section = f"ch-{index:04d}"
            nodes = clean_nodes(parsed.get(source, []), omissions)
            rewrite_nodes(nodes, source, section, target_sections, first_ids, warnings)
            prepared.append((section, source, nodes))
        for _, _, nodes in prepared: finish_links(nodes, first_ids)
        if navigation == "headings" and not any(any(find_all(node, {"h1", "h2"}) for node in nodes) for _, _, nodes in prepared):
            navigation = "sections"
        nav_labels: dict[str, str] = {}
        subitems: dict[str, list[tuple[str, str]]] = {}
        parent_source: str | None = None
        for source, fragment, label, depth in nav_records:
            if depth == 1:
                parent_source = source
                nav_labels.setdefault(source, label)
                continue
            anchor = first_ids.get((source, fragment)) if fragment else target_sections.get(source)
            parent_section = target_sections.get(parent_source or source)
            if anchor and parent_section:
                subitems.setdefault(parent_section, []).append((anchor, label))
        chunks: list[tuple[str, str, str, int]] = []
        for index, (section, source, nodes) in enumerate(prepared, 1):
            fallback = f"Section {index:02d}"
            if navigation == "headings":
                label, heading_items = heading_fallback(nodes, section, fallback)
                if heading_items:
                    subitems[section] = heading_items
            else:
                label = nav_labels.get(source, first_heading(nodes, fallback))
            content = "".join(serialize(n) for n in nodes)
            chunks.append((section, label, content, text_words(re.sub(r"<[^>]+>", " ", content))))
        if not any(words for _, _, _, words in chunks):
            raise ConversionError("unreadable-content", "EPUB contains no readable text")
    if recovered and "malformed-body-recovered" not in warnings: warnings.append("malformed-body-recovered")
    text_bytes = sum(len(re.sub(r"<[^>]+>", " ", x[2]).encode("utf-8")) for x in chunks)
    if text_bytes > 5_000_000: warnings.append("large-text-over-5000000-bytes")
    template = template_path.read_text(encoding="utf-8")
    output = build_html(template, book, chunks, subitems)
    parser_label = "auto-parity" if parser_name == "auto" and optional_available() else parser_name
    summary = {"status": "success", "slug": slugify(book.title), "title": book.title, "author": book.author, "chapters": len(chunks), "words": sum(x[3] for x in chunks), "reading_minutes": max(1, math.ceil(sum(x[3] for x in chunks) / 250)), "bytes": len(output.encode("utf-8")), "navigation_source": navigation, "parser": parser_label, "warnings": sorted(set(warnings)), "omissions": omissions}
    return output, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path); parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--template", type=Path, default=Path(__file__).with_name("template.html"))
    parser.add_argument("--parser", choices=("auto", "ebooklib", "stdlib"), default="auto")
    args = parser.parse_args(argv)
    try:
        output, summary = convert(args.input, args.template, args.parser)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=args.out.parent, delete=False) as handle:
            handle.write(output); temporary = Path(handle.name)
        os.replace(temporary, args.out)
        summary["output"] = str(args.out)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True)); return 0
    except ConversionError as error:
        print(json.dumps({"status": "error", "code": error.code, "message": error.message, "warnings": sorted(set(error.warnings))}, ensure_ascii=False, sort_keys=True)); return 1
    except Exception as error:
        print(json.dumps({"status": "error", "code": "unexpected", "message": str(error), "warnings": []}, ensure_ascii=False, sort_keys=True)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
