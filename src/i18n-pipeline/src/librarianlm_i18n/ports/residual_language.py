"""Deterministic residual-language detection boundary used by validation."""

from __future__ import annotations

from typing import Protocol

from librarianlm_i18n.kernel.contracts import ComponentIdentity, ResidualLanguageEvidence
from librarianlm_i18n.kernel.errors import ActionableError


class ResidualLanguageResult:
    def __init__(self, *, evidence: ResidualLanguageEvidence | None = None, error: ActionableError | None = None) -> None:
        if (evidence is None) == (error is None):
            raise ValueError("residual language results require exactly one evidence value or error")
        self.evidence = evidence
        self.error = error


class ResidualLanguageDetector(Protocol):
    @property
    def identity(self) -> ComponentIdentity: ...

    def inspect(self, *, source_unit_id: str, source_text: str, target_text: str) -> ResidualLanguageResult: ...
