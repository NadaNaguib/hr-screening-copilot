"""Review task repository port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from copilot.domain.review_task import ReviewTask
from copilot.domain.sla_rule import SLARule


class ReviewTaskRepositoryPort(ABC):
    """Persistence for review tasks and SLA rule resolution."""

    @abstractmethod
    async def create_task(self, task: ReviewTask) -> ReviewTask:
        """Persist a new review task."""

    @abstractmethod
    async def get_task(self, task_id: UUID) -> ReviewTask | None:
        """Fetch a task by id."""

    @abstractmethod
    async def get_task_by_candidate(self, candidate_id: UUID) -> ReviewTask | None:
        """Fetch the task for a candidate."""

    @abstractmethod
    async def update_task(self, task: ReviewTask) -> ReviewTask:
        """Persist task changes."""

    @abstractmethod
    async def query_tasks(
        self,
        job_id: UUID | None = None,
        status: list[str] | None = None,
        role: str | None = None,
        assignee_id: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReviewTask]:
        """Query tasks according to role-aware filters."""

    @abstractmethod
    async def get_sla_rule_for_job(self, job_id: UUID | None) -> SLARule | None:
        """Return job-specific SLA rule if any."""
