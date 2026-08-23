"""Fail-closed lxml implementation of the fixture-v1 selection policy."""

from __future__ import annotations

from html.parser import HTMLParser

from lxml import etree

from librarianlm_i18n.kernel.contracts import (
    CanonicalSourcePackage, ContentClass, Eligibility, SlotDisposition,
    StructuralLocation, TypedLocator,
)
from librarianlm_i18n.kernel.errors import Retryability, actionable_error
from librarianlm_i18n.kernel.identity import derive_typed_id, source_text_digest
from librarianlm_i18n.ports.html_document import HtmlSelectionResult, SelectedSourceSlot


class LxmlHtmlDocument:
    """Select exact values without accepting repaired or remotely loaded HTML."""

    def select(self, package: CanonicalSourcePackage) -> HtmlSelectionResult:
        try:
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
            return self._failure("invalid-source-classification", "source-profile", "inherited-fixture-ownership", "a unique compatible ownership profile", str(error) or type(error).__name__)
        except Exception as error:  # no parser exception crosses a workflow boundary
            return self._failure("html-document-failure", "source-html", "secured-lxml-selection", "successful fixture selection", f"{type(error).__name__}: {error}", retryable=True)

    @staticmethod
    def _failure(code: str, subject: str, rule: str, expected: str, observed: str, *, retryable: bool = False) -> HtmlSelectionResult:
        return HtmlSelectionResult(error=actionable_error(
            code=code, workflow="prepare", subject=subject, rule=rule,
            expected=expected, observed=observed or "unknown", retryability=Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
            next_action="Correct the canonical source package or fixture profile and restart preparation.",
        ))

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

        def append_value(element: etree._Element, path: tuple[int, ...], slot: str, text: str | None, cls: ContentClass, disposition: SlotDisposition, reason: str) -> None:
            if text is None or not text.strip():
                return
            location = StructuralLocation(owned_root_id=root_id, path=path, slot=slot)
            shape = self._shape(root, path)
            fingerprint = derive_typed_id("structural-fingerprint", {"location": location.model_dump(mode="json"), "shape": shape})
            locator = TypedLocator(locator=f"dom:{root_id}:{'.'.join(map(str, path)) or 'root'}:{slot}", kind=cls.value)
            result.append(SelectedSourceSlot(
                location=location, locator=locator, structural_fingerprint=fingerprint,
                text=text, text_digest=source_text_digest(text), content_class=cls,
                eligibility=Eligibility(disposition.value), eligibility_reason=reason,
            ))

        def visit(element: etree._Element, path: tuple[int, ...], inherited: SlotDisposition, inherited_reason: str) -> None:
            disposition, reason = state(element, inherited, inherited_reason)
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


class _MalformedHtml(ValueError):
    pass


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
