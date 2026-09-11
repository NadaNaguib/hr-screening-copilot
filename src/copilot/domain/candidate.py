"""Candidate domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from copilot.domain.errors import ValidationError


class CandidateStatus(str, Enum):
    """High-level candidate lifecycle status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    SCREENED = "screened"
    FAILED = "failed"


@dataclass
class Candidate:
    """A job applicant with parsed profile data."""

    id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None
    full_name: str = ""
    email: str = ""
    phone: str = ""
    years_of_experience: float = 0.0
    skills: list[str] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    work_experience: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    cv_sha256: str = ""
    status: CandidateStatus = CandidateStatus.UPLOADED
    overall_score: float | None = None
    priority: str = "MEDIUM"
    interview_probes: list[dict[str, Any]] = field(default_factory=list)
    probes_generated: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def mark_processing(self) -> None:
        """Transition to processing."""
        self.status = CandidateStatus.PROCESSING

    def mark_screened(self, score: float | None = None) -> None:
        """Transition to screened."""
        self.status = CandidateStatus.SCREENED
        if score is not None:
            self.overall_score = score

    def mark_failed(self) -> None:
        """Transition to failed."""
        self.status = CandidateStatus.FAILED

    def set_interview_probes(self, probes: list[dict[str, Any]]) -> None:
        """Attach AI-generated interview probes and flag them as ready."""
        self.interview_probes = probes
        self.probes_generated = bool(probes)
        self.updated_at = datetime.utcnow()

    def add_job(self, job_id: UUID) -> None:
        """Assign to a job."""
        if job_id is None:
            raise ValidationError("Invalid job_id")
        self.job_id = job_id
