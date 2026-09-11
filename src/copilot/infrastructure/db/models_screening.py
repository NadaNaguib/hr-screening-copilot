"""Screening ORM models: candidates, evidence, rubric scores."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from copilot.infrastructure.db.base import Base

if TYPE_CHECKING:
    from copilot.infrastructure.db.models_core import JobORM
    from copilot.infrastructure.db.models_workflow import ReviewTaskORM


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class CandidateORM(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    years_of_experience: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    work_experience: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cv_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    interview_probes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    probes_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    job: Mapped[JobORM] = relationship(back_populates="candidates")
    review_tasks: Mapped[list[ReviewTaskORM]] = relationship(back_populates="candidate")
    evidence: Mapped[list[EvidenceORM]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    scores: Mapped[list[RubricScoreORM]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("job_id", "cv_sha256", name="uix_candidate_job_hash"),)


class EvidenceORM(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubric_criteria.id"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_chunk_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    candidate: Mapped[CandidateORM] = relationship(back_populates="evidence")


class RubricScoreORM(Base):
    __tablename__ = "rubric_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rubric_criteria.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    candidate: Mapped[CandidateORM] = relationship(back_populates="scores")
