"""Aggregate ORM model imports so Alembic can discover all tables."""
from __future__ import annotations

from copilot.infrastructure.db.models_core import (  # noqa: F401
    ChunkORM,
    DocumentORM,
    JobORM,
    UserORM,
)
from copilot.infrastructure.db.models_rubric import RubricCriterionORM, RubricORM  # noqa: F401
from copilot.infrastructure.db.models_screening import (  # noqa: F401
    CandidateORM,
    EvidenceORM,
    RubricScoreORM,
)
from copilot.infrastructure.db.models_workflow import (  # noqa: F401
    AuditEventORM,
    ReviewTaskORM,
    ShortlistEntryORM,
    ShortlistORM,
    SLARuleORM,
)
