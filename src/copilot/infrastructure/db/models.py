"""Aggregate ORM model imports so Alembic can discover all tables."""
from __future__ import annotations

from copilot.infrastructure.db.models_core import ChunkORM, DocumentORM, JobORM, UserORM  # noqa: F401
from copilot.infrastructure.db.models_rubric import RubricCriterionORM, RubricORM  # noqa: F401
from copilot.infrastructure.db.models_screening import CandidateORM, EvidenceORM, RubricScoreORM  # noqa: F401
from copilot.infrastructure.db.models_workflow import (  # noqa: F401
    AuditEventORM,
    ReviewTaskORM,
    SLARuleORM,
    ShortlistEntryORM,
    ShortlistORM,
)
