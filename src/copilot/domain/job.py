"""Job domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class Job:
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    department: str = ""
    description: str = ""
    location: str = ""
    priority: str = "MEDIUM"
    skills: list[str] = field(default_factory=list)
    rubric_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
