"""Candidate repository port interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from copilot.domain.candidate import Candidate
from copilot.domain.evidence import Evidence
from copilot.domain.rubric_score import RubricScore


class CandidateRepositoryPort(ABC):
    """Persistence for candidates, evidence, and rubric scores."""

    @abstractmethod
    async def get_by_hash(self, job_id: UUID | None, sha256: str) -> Candidate | None:
        """Find a candidate by job + document hash."""

    @abstractmethod
    async def create_candidate(self, candidate: Candidate) -> Candidate:
        """Persist a new candidate."""

    @abstractmethod
    async def update_candidate(self, candidate: Candidate) -> Candidate:
        """Update an existing candidate."""

    @abstractmethod
    async def get_candidate(self, candidate_id: UUID) -> Candidate | None:
        """Fetch a candidate by id."""

    @abstractmethod
    async def list_candidates(self, job_id: UUID | None = None) -> list[Candidate]:
        """List candidates, optionally filtered by job."""

    @abstractmethod
    async def add_evidence(self, candidate_id: UUID, evidence: list[Evidence]) -> None:
        """Add evidence rows to a candidate."""

    @abstractmethod
    async def add_scores(self, candidate_id: UUID, scores: list[RubricScore]) -> None:
        """Add rubric scores to a candidate."""
