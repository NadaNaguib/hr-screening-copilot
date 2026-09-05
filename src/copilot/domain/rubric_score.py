"""Rubric score domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class RubricScore:
    """Score for a specific criterion for a specific candidate."""

    id: UUID = field(default_factory=uuid4)
    candidate_id: UUID | None = None
    criterion_id: UUID | None = None
    score: float = 0.0
    reasoning: str = ""
    evidence_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def score_value(self) -> float:
        """Return numeric score."""
        return self.score
