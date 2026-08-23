"""Fail-closed lxml implementation of the fixture-v1 selection policy."""

from __future__ import annotations

from html.parser import HTMLParser
import re

from lxml import etree

from librarianlm_i18n.kernel.contracts import (
    CanonicalSourcePackage, ContentClass, Eligibility, InlineBindingMap,
    ProtectedBlockSegments, ProtectedSegment, SlotDisposition, StructuralLocation,
    TokenEntry, TypedLocator, UnitRecord,
)
from librarianlm_i18n.kernel.errors import Retryability, actionable_error
from librarianlm_i18n.kernel.identity import derive_token_id, derive_typed_id, render_protected_token, sha256_digest, source_text_digest
from librarianlm_i18n.kernel.canonical import canonical_bytes
from librarianlm_i18n.ports.html_document import HtmlCloneResult, HtmlMutationResult, HtmlSelectionResult, HtmlSerializationResult, ProtectedBlockResult, SelectedSourceSlot


class LxmlHtmlDocument:
    """Select exact values without accepting repaired or remotely loaded HTML."""

    def select(self, package: CanonicalSourcePackage) -> HtmlSelectionResult:
        try:
            if "[[[LLM:BIND:" in package.source_html:
                return HtmlSelectionResult(error=self._prepare_error("reserved-binding-token-source", "source-html", "canonical source contains the reserved protected-token namespace"))
            self._assert_no_repaired_structure(package.source_html)
            parser = etree.HTMLParser(
                recover=True, no_network=True,
                remove_comments=False, remove_pis=False,
            )
            raw = package.source_html.encode("utf-8")
            root = etree.fromstring(raw, parser=parser)
            # libxml's HTML4 vocabulary logs modern HTML5 elements (article,
            # section, etc.) as "Tag ... invalid" without changing the tree.
            # Those are not repairs.  Any other parser diagnostic is treated as
            # evidence that lxml would be inventing structure.
            repairs = tuple(item for item in parser.error_log if " invalid" not in item.message)
            if root is None or repairs:
                return self._failure("malformed-source-html", "source-html", "unrepaired-html", "HTML with no parser repairs", str(repairs))
            if etree.tostring(root, method="html", encoding="utf-8") is None:
                return self._failure("malformed-source-html", "source-html", "serializable-html", "serializable HTML", "parser produced no document")
            return HtmlSelectionResult(slots=self._select_roots(root, package))
        except (_MalformedHtml, etree.XMLSyntaxError, UnicodeError) as error:
            return self._failure("malformed-source-html", "source-html", "secured-strict-lxml-parse", "well-formed fixture HTML", str(error) or type(error).__name__)
        except (ValueError, TypeError) as error:
            if "protected blocks cannot absorb" in str(error):
                return self._prepare_failure("protected-block-unsupported", "protected-block", str(error))
            return self._failure("invalid-source-classification", "source-profile", "inherited-fixture-ownership", "a unique compatible ownership profile", str(error) or type(error).__name__)
        except Exception as error:  # no parser exception crosses a workflow boundary
            return self._failure("html-document-failure", "source-html", "secured-lxml-selection", "successful fixture selection", f"{type(error).__name__}: {error}", retryable=True)

    def clone(self, package: CanonicalSourcePackage) -> HtmlCloneResult:
        try:
            self._assert_no_repaired_structure(package.source_html)
            parser = etree.HTMLParser(recover=True, no_network=True, remove_comments=False, remove_pis=False)
            root = etree.fromstring(package.source_html.encode("utf-8"), parser=parser)
            repairs = tuple(item for item in parser.error_log if " invalid" not in item.message)
            if root is None or repairs:
                return HtmlCloneResult(error=self._assembly_error("malformed-source-html", "source-html", "unrepaired canonical source"))
            return HtmlCloneResult(document=_Clone(root, package))
        except Exception as error:
            return HtmlCloneResult(error=self._assembly_error("clone-failed", "source-html", f"{type(error).__name__}: {error}", retryable=True))

    def protected_block(self, package: CanonicalSourcePackage, slot: SelectedSourceSlot, source_unit_id: str) -> ProtectedBlockResult:
        try:
            cloned = self.clone(package)
            if cloned.error is not None:
                return ProtectedBlockResult(error=self._prepare_error(cloned.error.code, cloned.error.subject, cloned.error.observed))
            element = self._resolve_element(cloned.document.root, package, slot.location, slot.structural_fingerprint)
            if element is None:
                return ProtectedBlockResult(error=self._prepare_error("structural-resolution-failed", "protected-block", "source block no longer matches its fingerprint"))
            entries_data: list[dict] = []
            text_parts: list[str] = []

            def visit(node: etree._Element) -> None:
                text_parts.append(node.text or "")
                for child in list(node):
                    empty = not list(child) and not (child.text or "")
                    ordinal = len(entries_data)
                    kind = "empty" if empty else "open"
                    opening = {"kind": kind, "ordinal": ordinal, "tag": str(child.tag), "attributes": tuple(f"{name}={value}" for name, value in sorted(child.attrib.items())), "pair_ordinal": None}
                    entries_data.append(opening)
                    text_parts.append((kind, ordinal))
                    if not empty:
                        visit(child)
                        close_ordinal = len(entries_data)
                        entries_data.append({"kind": "close", "ordinal": close_ordinal, "tag": str(child.tag), "attributes": (), "pair_ordinal": ordinal})
                        opening["pair_ordinal"] = close_ordinal
                        text_parts.append(("close", close_ordinal))
                    text_parts.append(child.tail or "")

            visit(element)
            ids = {item["ordinal"]: derive_token_id(source_unit_id, item["kind"], item["ordinal"]) for item in entries_data}
            stream = "".join(render_protected_token(ids[part[1]]) if isinstance(part, tuple) else part for part in text_parts)
            digest = source_text_digest(stream)
            entries = tuple(TokenEntry(
                token_id=ids[item["ordinal"]], kind=item["kind"], source_order_ordinal=item["ordinal"],
                locator=TypedLocator(locator=f"{slot.locator.locator}:inline:{item['ordinal']}", kind="inline-binding"),
                source_node=item["tag"], source_attributes=item["attributes"],
                pair_id=ids[item["pair_ordinal"]] if item["pair_ordinal"] is not None else None,
                placement_rule="balanced-source-order",
            ) for item in entries_data)
            map_digest = sha256_digest(canonical_bytes({"schema_version": 1, "source_unit_id": source_unit_id, "source_digest": digest, "entries": tuple(entry.model_dump(mode="json") for entry in entries)}))
            binding_map = InlineBindingMap(source_unit_id=source_unit_id, source_digest=digest, entries=entries, map_digest=map_digest)
            segments = tuple(ProtectedSegment(ordinal=index, value=value) for index, value in enumerate(self._split_stream(stream)))
            segments_digest = sha256_digest(canonical_bytes({"schema_version": 1, "source_unit_id": source_unit_id, "source_digest": digest, "segments": tuple(item.model_dump(mode="json") for item in segments), "binding_map_digest": map_digest}))
            return ProtectedBlockResult(source_text=stream, binding_map=binding_map, segments=ProtectedBlockSegments(source_unit_id=source_unit_id, source_digest=digest, segments=segments, binding_map_digest=map_digest, segments_digest=segments_digest))
        except Exception as error:
            return ProtectedBlockResult(error=self._prepare_error("protected-block-invalid", "protected-block", f"{type(error).__name__}: {error}"))

    def rebind(self, document: object, unit: UnitRecord, binding_map: InlineBindingMap, target: str) -> HtmlMutationResult:
        try:
            if not isinstance(document, _Clone) or unit.structural_location is None or unit.structural_fingerprint is None:
                return HtmlMutationResult(error=self._assembly_error("structural-resolution-failed", "source-unit", "unit lacks an exact structural location and fingerprint"))
            element = self._resolve_element(document.root, document.package, unit.structural_location, unit.structural_fingerprint)
            if element is None:
                return HtmlMutationResult(error=self._assembly_error("structural-resolution-failed", "source-unit", "expected source fingerprint did not resolve"))
            if binding_map.source_unit_id != unit.source_unit_id:
                return HtmlMutationResult(error=self._assembly_error("binding-map-mismatch", "binding-map", "map source unit does not match unit"))
            tokens = tuple(render_protected_token(entry.token_id) for entry in binding_map.entries)
            token_matches = tuple(re.findall(r"\[\[\[LLM:BIND:[A-Z2-7]{26}\]\]\]", target))
            if "[[[LLM:BIND:" in target and len(token_matches) != target.count("[[[LLM:BIND:"):
                return HtmlMutationResult(error=self._assembly_error("malformed-binding-token", "fixture-target", "target contains malformed or foreign token syntax"))
            parts = re.split(r"(\[\[\[LLM:BIND:[A-Z2-7]{26}\]\]\])", target)
            supplied = tuple(part for part in parts if part.startswith("[[[LLM:BIND:"))
            expected_by_token = {render_protected_token(entry.token_id): entry for entry in binding_map.entries}
            if len(supplied) != len(tokens) or set(supplied) != set(tokens):
                return HtmlMutationResult(error=self._assembly_error("binding-token-sequence-invalid", "fixture-target", "tokens must occur exactly once and belong to the persisted binding map"))
            stack: list[TokenEntry] = []
            for token in supplied:
                entry = expected_by_token[token]
                if entry.kind == "open":
                    stack.append(entry)
                elif entry.kind == "close":
                    if not stack or stack.pop().pair_id != entry.token_id:
                        return HtmlMutationResult(error=self._assembly_error("binding-token-sequence-invalid", "fixture-target", "binding pairs must remain balanced, nested, and non-crossing"))
            if stack:
                return HtmlMutationResult(error=self._assembly_error("binding-token-sequence-invalid", "fixture-target", "binding pairs must remain balanced, nested, and non-crossing"))
            self._reconstruct_protected_tree(element, parts, expected_by_token, self._binding_nodes(element, binding_map))
            return HtmlMutationResult()
        except Exception as error:
            return HtmlMutationResult(error=self._assembly_error("rebind-failed", "fixture-target", f"{type(error).__name__}: {error}", retryable=True))

    def apply_plain(self, document: object, unit: UnitRecord, target: str) -> HtmlMutationResult:
        try:
            if "[[[LLM:BIND:" in target:
                return HtmlMutationResult(error=self._assembly_error("protected-token-in-plain-target", "fixture-target", "plain fixture targets cannot contain protected-token syntax"))
            if not isinstance(document, _Clone):
                return HtmlMutationResult(error=self._assembly_error("structural-resolution-failed", "source-unit", "clone is not an lxml document"))
            node = self._resolve_element(document.root, document.package, unit.structural_location, unit.structural_fingerprint) if unit.structural_location is not None and unit.structural_fingerprint is not None else None
            if node is None or unit.structural_location is None:
                return HtmlMutationResult(error=self._assembly_error("structural-resolution-failed", "source-unit", "expected source fingerprint did not resolve"))
            slot = unit.structural_location.slot
            if slot == "text":
                node.text = target
            elif slot.startswith("tail:"):
                index = int(slot.split(":", 1)[1])
                child = list(node)[index]
                child.tail = target
            elif slot.startswith("attribute:"):
                name = slot.split(":", 1)[1]
                if name not in node.attrib:
                    return HtmlMutationResult(error=self._assembly_error("structural-resolution-failed", "source-unit", "declared attribute is absent from clone"))
                node.set(name, target)
            else:
                return HtmlMutationResult(error=self._assembly_error("invalid-placement", "source-unit", f"unknown slot {slot!r}"))
            return HtmlMutationResult()
        except Exception as error:
            return HtmlMutationResult(error=self._assembly_error("apply-failed", "fixture-target", f"{type(error).__name__}: {error}", retryable=True))

    def serialize(self, document: object) -> HtmlSerializationResult:
        try:
            if not isinstance(document, _Clone):
                return HtmlSerializationResult(error=self._assembly_error("serialize-failed", "draft", "clone is not an lxml document"))
            return HtmlSerializationResult(html=etree.tostring(document.root, method="html", encoding="unicode", with_tail=False))
        except Exception as error:
            return HtmlSerializationResult(error=self._assembly_error("serialize-failed", "draft", f"{type(error).__name__}: {error}", retryable=True))

    @staticmethod
    def _failure(code: str, subject: str, rule: str, expected: str, observed: str, *, retryable: bool = False) -> HtmlSelectionResult:
        return HtmlSelectionResult(error=actionable_error(
            code=code, workflow="prepare", subject=subject, rule=rule,
            expected=expected, observed=observed or "unknown", retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Correct the canonical source package or fixture profile and restart preparation.",
        ))

    @staticmethod
    def _prepare_failure(code: str, subject: str, observed: str) -> HtmlSelectionResult:
        return HtmlSelectionResult(error=LxmlHtmlDocument._prepare_error(code, subject, observed))

    @staticmethod
    def _assert_no_repaired_structure(source: str) -> None:
        probe = _StructureProbe()
        try:
            probe.feed(source)
            probe.close()
        except Exception as error:
            raise _MalformedHtml(str(error) or type(error).__name__) from error
        if probe.stack:
            raise _MalformedHtml(f"unclosed HTML elements: {', '.join(probe.stack)}")


    def _select_roots(self, document: etree._Element, package: CanonicalSourcePackage) -> tuple[SelectedSourceSlot, ...]:
        roots: list[tuple[object, object]] = []
        for configured in package.ownership_profile.owned_roots:
            matches = [element for element in document.iter() if element.get("id") == configured.element_id]
            if len(matches) != 1:
                raise ValueError(f"owned root {configured.root_id!r} must resolve to exactly one durable id")
            roots.append((configured, matches[0]))
        slots: list[SelectedSourceSlot] = []
        for configured, element in roots:
            slots.extend(self._walk_root(element, package, configured.root_id, configured.disposition))
        locations = tuple(slot.location for slot in slots)
        if len(set(locations)) != len(locations):
            raise ValueError("source selection produced duplicate structural locations")
        return tuple(slots)

    def _walk_root(self, root: etree._Element, package: CanonicalSourcePackage, root_id: str, root_disposition: SlotDisposition) -> tuple[SelectedSourceSlot, ...]:
        rules = {rule.element_id: rule for rule in package.ownership_profile.slot_rules}
        result: list[SelectedSourceSlot] = []

        def state(element: etree._Element, inherited: SlotDisposition, inherited_reason: str) -> tuple[SlotDisposition, str]:
            if element.get(package.ownership_profile.application_owned_attribute) == "application":
                return SlotDisposition.EXCLUDED, "application-owned marker"
            rule = rules.get(element.get("id", ""))
            if rule is None:
                return inherited, inherited_reason
            if inherited in (SlotDisposition.EXCLUDED, SlotDisposition.UNSUPPORTED) and rule.disposition is SlotDisposition.REQUIRED:
                raise ValueError("required descendants cannot override excluded or unsupported ancestors")
            return rule.disposition, rule.reason

        def append_value(element: etree._Element, path: tuple[int, ...], slot: str, text: str | None, cls: ContentClass, disposition: SlotDisposition, reason: str, *, protected_block: bool = False) -> None:
            if (text is None or not text.strip()) and not protected_block:
                return
            location = StructuralLocation(owned_root_id=root_id, path=path, slot=slot)
            shape = self._shape(root, path)
            fingerprint = derive_typed_id("structural-fingerprint", {"location": location.model_dump(mode="json"), "shape": shape})
            locator = TypedLocator(locator=f"dom:{root_id}:{'.'.join(map(str, path)) or 'root'}:{slot}", kind=cls.value)
            result.append(SelectedSourceSlot(
                location=location, locator=locator, structural_fingerprint=fingerprint,
                text=text, text_digest=source_text_digest(text), content_class=cls,
                eligibility=Eligibility(disposition.value), eligibility_reason=reason, protected_block=protected_block,
            ))

        def visit(element: etree._Element, path: tuple[int, ...], inherited: SlotDisposition, inherited_reason: str) -> None:
            disposition, reason = state(element, inherited, inherited_reason)
            protected = (
                package.segmentation_profile.rule == "fixture-v2-protected-blocks"
                and disposition is SlotDisposition.REQUIRED
                and str(element.tag).lower() in {"p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "td", "th"}
                and bool(list(element))
            )
            if protected:
                for descendant in element.iterdescendants():
                    tag = str(descendant.tag).lower()
                    nested_rule = rules.get(descendant.get("id", ""))
                    if tag not in {"em", "strong", "i", "b", "a", "span", "small", "code", "sup", "sub", "br", "img", "wbr"} or nested_rule is not None or descendant.get(package.ownership_profile.application_owned_attribute) == "application":
                        raise ValueError("protected blocks cannot absorb independently classified or unsupported descendants")
                append_value(element, path, "text", element.text, ContentClass.TEXT, disposition, reason, protected_block=True)
                return
            append_value(element, path, "text", element.text, ContentClass.TEXT, disposition, reason)
            rule = rules.get(element.get("id", ""))
            if rule is not None:
                for name in rule.attribute_names:
                    if name not in element.attrib:
                        raise ValueError(f"declared book-owned attribute {name!r} is missing")
                    append_value(element, path, f"attribute:{name}", element.get(name), ContentClass.ATTRIBUTE, disposition, reason)
            children = list(element)
            for index, child in enumerate(children):
                child_path = path + (index,)
                visit(child, child_path, disposition, reason)
                # A tail belongs to its *parent* structurally and inherits the
                # parent classification, never the preceding child's state.
                append_value(element, path, f"tail:{index}", child.tail, ContentClass.TAIL, disposition, reason)

        visit(root, (), root_disposition, "owned root disposition")
        return tuple(result)

    @staticmethod
    def _shape(root: etree._Element, path: tuple[int, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
        node = root
        shape: list[tuple[str, tuple[str, ...]]] = [(str(node.tag), tuple(sorted(node.attrib)))]
        for index in path:
            node = list(node)[index]
            shape.append((str(node.tag), tuple(sorted(node.attrib))))
        return tuple(shape)

    @staticmethod
    def _split_stream(value: str) -> tuple[str, ...]:
        return tuple(re.split(r"(\[\[\[LLM:BIND:[A-Z2-7]{26}\]\]\])", value))

    @staticmethod
    def _collect_text_slots(element: etree._Element, slots: list[tuple[etree._Element, str]]) -> None:
        slots.append((element, "text"))
        for child in list(element):
            if list(child) or (child.text or ""):
                LxmlHtmlDocument._collect_text_slots(child, slots)
            slots.append((child, "tail"))

    @staticmethod
    def _binding_nodes(root: etree._Element, binding_map: InlineBindingMap) -> dict[str, etree._Element]:
        entries = iter(binding_map.entries)
        bound: dict[str, etree._Element] = {}

        def visit(parent: etree._Element) -> None:
            for child in list(parent):
                entry = next(entries)
                empty = not list(child) and not (child.text or "")
                if entry.kind != ("empty" if empty else "open") or entry.source_node != str(child.tag):
                    raise ValueError("clone inline structure no longer matches persisted binding map")
                bound[render_protected_token(entry.token_id)] = child
                if not empty:
                    visit(child)
                    closing = next(entries)
                    if closing.kind != "close" or closing.pair_id != entry.token_id:
                        raise ValueError("clone inline pair no longer matches persisted binding map")
                    bound[render_protected_token(closing.token_id)] = child

        visit(root)
        try:
            next(entries)
        except StopIteration:
            return bound
        raise ValueError("clone has extra persisted bindings")

    @staticmethod
    def _reconstruct_protected_tree(root: etree._Element, parts: list[str], entries: dict[str, TokenEntry], nodes: dict[str, etree._Element]) -> None:
        """Build mixed content only from target text and pre-existing clone nodes."""
        unique_nodes = tuple(dict.fromkeys(nodes.values()))
        for parent in (root, *unique_nodes):
            for child in list(parent):
                parent.remove(child)
            parent.text = None
        for node in unique_nodes:
            node.tail = None
        stack: list[etree._Element] = [root]
        previous: etree._Element | None = None

        def put_text(value: str) -> None:
            nonlocal previous
            if previous is None:
                stack[-1].text = value or None
            else:
                previous.tail = value or None

        for part in parts:
            if not part.startswith("[[[LLM:BIND:"):
                put_text(part)
                continue
            entry, node = entries[part], nodes[part]
            if entry.kind == "open":
                stack[-1].append(node)
                stack.append(node)
                previous = None
            elif entry.kind == "empty":
                stack[-1].append(node)
                previous = node
            else:
                closed = stack.pop()
                if closed is not node:
                    raise ValueError("validated protected pair resolves to a different clone node")
                previous = node

    @staticmethod
    def _assembly_error(code: str, subject: str, observed: str, *, retryable: bool = False):
        return actionable_error(
            code=code, workflow="assemble", subject=subject, rule="frozen-protected-block-assembly",
            expected="a complete canonical source graph with exact protected bindings", observed=observed or "unknown",
            retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Repair the confirmed preparation artifacts or fixture target and restart assembly.",
        )

    @staticmethod
    def _prepare_error(code: str, subject: str, observed: str, *, retryable: bool = False):
        return actionable_error(
            code=code, workflow="prepare", subject=subject, rule="frozen-protected-block-preparation",
            expected="a supported canonical source without reserved binding tokens", observed=observed or "unknown",
            retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Repair the canonical source/profile and restart preparation.",
        )

    def _resolve_element(self, document: object, package: CanonicalSourcePackage, location: StructuralLocation, fingerprint: str) -> etree._Element | None:
        if not isinstance(document, etree._Element):
            return None
        configured = next((item for item in package.ownership_profile.owned_roots if item.root_id == location.owned_root_id), None)
        if configured is None:
            return None
        roots = [node for node in document.iter() if node.get("id") == configured.element_id]
        if len(roots) != 1:
            return None
        root = roots[0]
        try:
            node = root
            for index in location.path:
                node = list(node)[index]
        except IndexError:
            return None
        actual = derive_typed_id("structural-fingerprint", {"location": location.model_dump(mode="json"), "shape": self._shape(root, location.path)})
        return node if actual == fingerprint else None


class _MalformedHtml(ValueError):
    pass


class _Clone:
    """Opaque clone carrying the immutable profile needed for exact rebinding."""

    def __init__(self, root: etree._Element, package: CanonicalSourcePackage) -> None:
        self.root = root
        self.package = package


class _StructureProbe(HTMLParser):
    """Small lexical guard that rejects markup lxml would silently repair."""

    _VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() not in self._VOID:
            self.stack.append(tag.lower())

    def handle_startendtag(self, tag: str, attrs) -> None:
        return None

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            raise _MalformedHtml(f"mismatched HTML closing tag: {tag}")
        self.stack.pop()
