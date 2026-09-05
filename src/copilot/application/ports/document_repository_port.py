"""Document repository port interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from copilot.domain.job import Job
from copilot.domain.rubric import Rubric
from copilot.domain.sla_rule import SLARule


class DocumentRepositoryPort(ABC):
    """Persistence for documents, jobs, rubrics, SLA rules."""

    @abstractmethod
    async def create_job(self, job: Job) -> Job:
        """Persist a new job."""

    @abstractmethod
    async def get_job(self, job_id: UUID) -> Job | None:
        """Fetch a job by id."""

    @abstractmethod
    async def list_jobs(self) -> list[Job]:
        """Return all jobs."""

    @abstractmethod
    async def create_rubric(self, rubric: Rubric) -> Rubric:
        """Persist a rubric."""

    @abstractmethod
    async def get_rubric_for_job(self, job_id: UUID) -> Rubric | None:
        """Fetch rubric for a job."""

    @abstractmethod
    async def save_sla_rule(self, rule: SLARule) -> SLARule:
        """Persist or update an SLA rule."""

    @abstractmethod
    async def get_sla_rule_for_job(self, job_id: UUID | None) -> SLARule | None:
        """Fetch SLA rule for a job (or None if only global defaults exist)."""
