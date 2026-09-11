"""Workflow ORM models: review tasks, SLA rules, shortlists, audit events."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from copilot.domain.review_task import ReviewStatus
from copilot.infrastructure.db.base import Base

if TYPE_CHECKING:
    from copilot.infrastructure.db.models_core import JobORM
    from copilot.infrastructure.db.models_screening import CandidateORM


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ReviewTaskORM(Base):
    __tablename__ = "review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.PENDING_TRIAGE,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    triage_deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triage_escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triage_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sla_outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    probes_edited: Mapped[bool] = mapped_column(default=False, nullable=False)
    audit_log: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    candidate: Mapped[CandidateORM] = relationship(back_populates="review_tasks")
    job: Mapped[JobORM] = relationship(back_populates="review_tasks")


class SLARuleORM(Base):
    __tablename__ = "sla_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, unique=True
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    triage_hours: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    decision_hours: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    job: Mapped[JobORM] = relationship(back_populates="sla_rules")


class ShortlistORM(Base):
    __tablename__ = "shortlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    entries: Mapped[list[ShortlistEntryORM]] = relationship(
        back_populates="shortlist", cascade="all, delete-orphan"
    )


class ShortlistEntryORM(Base):
    __tablename__ = "shortlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    shortlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shortlists.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    shortlist: Mapped[ShortlistORM] = relationship(back_populates="entries")


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
