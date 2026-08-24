"""Small, declared-limitation residual detector for fixture mode only."""

from __future__ import annotations

import re

from librarianlm_i18n.kernel.contracts import ComponentIdentity, ResidualLanguageEvidence
from librarianlm_i18n.kernel.errors import Retryability, actionable_error
from librarianlm_i18n.ports.residual_language import ResidualLanguageDetector, ResidualLanguageResult


class FixtureResidualLanguageDetector(ResidualLanguageDetector):
    """Exact token overlap, not language identification or a probabilistic detector."""

    def __init__(self, identity: ComponentIdentity) -> None:
        self._identity = identity

    @property
    def identity(self) -> ComponentIdentity:
        return self._identity

    def inspect(self, *, source_unit_id: str, source_text: str, target_text: str) -> ResidualLanguageResult:
        try:
            source_words = frozenset(re.findall(r"[A-Za-z]{3,}", source_text.casefold()))
            matched = tuple(sorted(word for word in frozenset(re.findall(r"[A-Za-z]{3,}", target_text.casefold())) if word in source_words))
            return ResidualLanguageResult(evidence=ResidualLanguageEvidence(
                source_unit_id=source_unit_id, detector=self.identity, residual_count=len(matched),
                matched_terms=matched,
                limitation="fixture exact-token overlap only; it does not identify natural language or infer terminology",
            ))
        except Exception as error:
            return ResidualLanguageResult(error=actionable_error(
                code="residual-detector-failure", workflow="validate", subject="residual-language",
                rule="fixture-exact-token-overlap", expected="deterministic fixture detector input",
                observed=f"{type(error).__name__}: {error}", retryability=Retryability.NOT_RETRYABLE,
                next_action="Repair the frozen candidate text or detector configuration and rerun validation.",
            ))
