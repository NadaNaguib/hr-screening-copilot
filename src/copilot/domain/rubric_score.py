"""Rubric score domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RubricScore:
    """Score for a specific criterion for a specific candidate."""

    id: int | None = None
    candidate_id: int | None = None
    criterion_id: int | None = None
    score: float = 0.0
    reasoning: str = ""
    evidence_ids: list[int] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def score_value(self) -> float:
        """Return numeric score."""
        return self.score
