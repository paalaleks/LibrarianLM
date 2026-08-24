"""Strict document-selection boundary used only by fixture preparation."""

from __future__ import annotations

from typing import Protocol

from librarianlm_i18n.kernel.contracts import CanonicalSourcePackage, ContentClass, Eligibility, InlineBindingMap, ProtectedBlockSegments, StructuralLocation, TypedLocator, UnitRecord
from librarianlm_i18n.kernel.errors import ActionableError
from librarianlm_i18n.kernel.identity import Sha256Digest, StructuralFingerprint


class SelectedSourceSlot:
    """A parser-owned, exact source value.  It is deliberately not mutable."""

    def __init__(
        self, *, location: StructuralLocation, locator: TypedLocator,
        structural_fingerprint: StructuralFingerprint, text: str,
        text_digest: Sha256Digest, content_class: ContentClass,
        eligibility: Eligibility, eligibility_reason: str, protected_block: bool = False,
    ) -> None:
        self.location = location
        self.locator = locator
        self.structural_fingerprint = structural_fingerprint
        self.text = text
        self.text_digest = text_digest
        self.content_class = content_class
        self.eligibility = eligibility
        self.eligibility_reason = eligibility_reason
        self.protected_block = protected_block


class HtmlSelectionResult:
    def __init__(self, *, slots: tuple[SelectedSourceSlot, ...] = (), error: ActionableError | None = None) -> None:
        if (error is None) != bool(slots) and error is None:
            # Empty is a valid successful selection (Prepare turns it into an
            # actionable empty-required finding), so this check remains minimal.
            pass
        self.slots = slots
        self.error = error


class ProtectedBlockResult:
    def __init__(self, *, source_text: str | None = None, binding_map: InlineBindingMap | None = None, segments: ProtectedBlockSegments | None = None, error: ActionableError | None = None) -> None:
        successful = source_text is not None and binding_map is not None and segments is not None
        if successful == (error is not None):
            raise ValueError("protected block results require exact artifacts or an error")
        self.source_text = source_text
        self.binding_map = binding_map
        self.segments = segments
        self.error = error


class HtmlCloneResult:
    def __init__(self, *, document: object | None = None, error: ActionableError | None = None) -> None:
        if (document is None) == (error is None):
            raise ValueError("HTML clone results require exactly one document or error")
        self.document = document
        self.error = error


class HtmlMutationResult:
    def __init__(self, *, error: ActionableError | None = None) -> None:
        self.error = error


class HtmlSerializationResult:
    def __init__(self, *, html: str | None = None, error: ActionableError | None = None) -> None:
        if (html is None) == (error is None):
            raise ValueError("HTML serialization results require exactly one HTML value or error")
        self.html = html
        self.error = error


class HtmlObservation:
    """Read-only candidate/source facts; no parsed document leaves this boundary."""

    def __init__(
        self,
        *,
        slots: tuple[SelectedSourceSlot, ...],
        structure_digest: Sha256Digest,
        root_language: str | None,
        root_direction: str | None,
        heading_levels: tuple[int, ...],
        landmarks: tuple[str, ...],
        focus_order: tuple[str, ...],
        element_ids: tuple[str, ...],
        fragment_references: tuple[tuple[str, str], ...],
        language_metadata: tuple[tuple[str, str | None, str | None], ...],
    ) -> None:
        self.slots = slots
        self.structure_digest = structure_digest
        self.root_language = root_language
        self.root_direction = root_direction
        self.heading_levels = heading_levels
        self.landmarks = landmarks
        self.focus_order = focus_order
        self.element_ids = element_ids
        self.fragment_references = fragment_references
        self.language_metadata = language_metadata


class HtmlObservationResult:
    def __init__(self, *, observation: HtmlObservation | None = None, error: ActionableError | None = None) -> None:
        if (observation is None) == (error is None):
            raise ValueError("HTML observation results require exactly one observation or error")
        self.observation = observation
        self.error = error


class HtmlDocument(Protocol):
    def select(self, package: CanonicalSourcePackage) -> HtmlSelectionResult: ...
    def protected_block(self, package: CanonicalSourcePackage, slot: SelectedSourceSlot, source_unit_id: str) -> ProtectedBlockResult: ...
    def clone(self, package: CanonicalSourcePackage) -> HtmlCloneResult: ...
    def rebind(self, document: object, unit: UnitRecord, binding_map: InlineBindingMap, target: str) -> HtmlMutationResult: ...
    def apply_plain(self, document: object, unit: UnitRecord, target: str) -> HtmlMutationResult: ...
    def serialize(self, document: object) -> HtmlSerializationResult: ...
    def observe(self, package: CanonicalSourcePackage, html: str) -> HtmlObservationResult: ...
    def project_root_locale(self, document: object, language: str, direction: str) -> HtmlMutationResult: ...
