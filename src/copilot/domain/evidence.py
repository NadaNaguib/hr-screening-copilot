"""Evidence domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EvidenceType(str, Enum):
    """Type of evidence extracted from a CV."""

    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    PROJECT = "project"
    OTHER = "other"


@dataclass
class Evidence:
    """A single piece of extracted evidence tied to a rubric criterion."""

    id: int | None = None
    candidate_id: int | None = None
    criterion_id: int | None = None
    evidence_type: EvidenceType = EvidenceType.OTHER
    quote: str = ""
    source_chunk_id: str | None = None
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None
