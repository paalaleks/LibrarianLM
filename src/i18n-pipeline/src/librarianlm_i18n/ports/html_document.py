"""Strict document-selection boundary used only by fixture preparation."""

from __future__ import annotations

from typing import Protocol

from librarianlm_i18n.kernel.contracts import CanonicalSourcePackage, ContentClass, Eligibility, StructuralLocation, TypedLocator
from librarianlm_i18n.kernel.errors import ActionableError
from librarianlm_i18n.kernel.identity import Sha256Digest, StructuralFingerprint


class SelectedSourceSlot:
    """A parser-owned, exact source value.  It is deliberately not mutable."""

    def __init__(
        self, *, location: StructuralLocation, locator: TypedLocator,
        structural_fingerprint: StructuralFingerprint, text: str,
        text_digest: Sha256Digest, content_class: ContentClass,
        eligibility: Eligibility, eligibility_reason: str,
    ) -> None:
        self.location = location
        self.locator = locator
        self.structural_fingerprint = structural_fingerprint
        self.text = text
        self.text_digest = text_digest
        self.content_class = content_class
        self.eligibility = eligibility
        self.eligibility_reason = eligibility_reason


class HtmlSelectionResult:
    def __init__(self, *, slots: tuple[SelectedSourceSlot, ...] = (), error: ActionableError | None = None) -> None:
        if (error is None) != bool(slots) and error is None:
            # Empty is a valid successful selection (Prepare turns it into an
            # actionable empty-required finding), so this check remains minimal.
            pass
        self.slots = slots
        self.error = error


class HtmlDocument(Protocol):
    def select(self, package: CanonicalSourcePackage) -> HtmlSelectionResult: ...
