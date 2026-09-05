"""Rubric domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class CriterionWeight(str, Enum):
    """Priority / weight of a rubric criterion."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RubricCriterion:
    """A single scoring criterion inside a rubric."""

    id: UUID = field(default_factory=uuid4)
    rubric_id: UUID | None = None
    name: str = ""
    description: str = ""
    weight: CriterionWeight = CriterionWeight.MEDIUM
    required: bool = False
    keywords: list[str] = field(default_factory=list)
    min_score: int = 1
    max_score: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Rubric:
    """A scoring rubric attached to a job."""

    id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None
    name: str = ""
    description: str = ""
    criteria: list[RubricCriterion] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
