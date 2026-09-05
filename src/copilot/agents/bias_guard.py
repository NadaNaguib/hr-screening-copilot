"""Deterministic bias guard with audit trail."""
from __future__ import annotations

from copilot.domain.bias_rules import BiasFinding, BiasRules
from copilot.domain.candidate import Candidate


class BiasGuard:
    """Redact protected attributes and record findings."""

    def __init__(self, rules: BiasRules | None = None) -> None:
        self.rules = rules or BiasRules()

    def redact(self, candidate: Candidate) -> tuple[str, list[BiasFinding]]:
        """Return redacted text and list of bias findings."""
        findings = self.rules.check(candidate.raw_text)
        redacted = candidate.raw_text
        for finding in findings:
            redacted = redacted.replace(finding.trigger, "[REDACTED]")
        return redacted, findings
