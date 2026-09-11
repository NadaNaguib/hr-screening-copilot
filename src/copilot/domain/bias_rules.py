"""Bias detection rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BIAS_KEYWORDS = {
    "gender": ["male", "female", "he", "she", "him", "her", "man", "woman"],
    "ethnicity": ["nationality", "ethnic", "race", "racial"],
    "age": ["age", "young", "old", "senior", "junior"],
    "marital": ["married", "single", "children", "kids", "pregnant"],
    "religion": ["religion", "religious", "muslim", "christian", "jewish"],
    "photo": ["photo", "picture", "image", "portrait"],
}


@dataclass
class BiasFinding:
    category: str
    trigger: str
    quote: str
    severity: str


class BiasRules:
    def __init__(self, rules: dict[str, list[str]] | None = None) -> None:
        self.rules = rules or BIAS_KEYWORDS

    def check(self, text: str) -> list[BiasFinding]:
        text_lower = text.lower()
        findings: list[BiasFinding] = []
        for category, keywords in self.rules.items():
            for keyword in keywords:
                if keyword in text_lower:
                    findings.append(
                        BiasFinding(
                            category=category,
                            trigger=keyword,
                            quote=text[:200],
                            severity="medium",
                        )
                    )
        return findings

    def to_dict(self) -> dict[str, Any]:
        return {"rules": self.rules}
