"""Shortlist domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class ShortlistFormat(str, Enum):
    """Export format."""

    CSV = "csv"
    PDF = "pdf"


@dataclass
class ShortlistEntry:
    """A candidate in a shortlist export."""

    candidate_id: UUID
    full_name: str
    email: str
    overall_score: float
    status: str
    manager_comment: str | None = None


@dataclass
class Shortlist:
    """Exportable shortlist for a job."""

    id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None
    name: str = ""
    entries: list[ShortlistEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: UUID | None = None

    def sort_by_score(self) -> None:
        """Sort entries descending by overall score."""
        self.entries.sort(key=lambda e: e.overall_score, reverse=True)
