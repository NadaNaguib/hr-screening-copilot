"""Evidence domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


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

    id: UUID = field(default_factory=uuid4)
    candidate_id: UUID | None = None
    criterion_id: UUID | None = None
    evidence_type: EvidenceType = EvidenceType.OTHER
    quote: str = ""
    source_chunk_id: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
