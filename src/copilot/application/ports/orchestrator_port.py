"""Orchestrator port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class OrchestratorResult:
    answer: str
    citations: list[dict[str, Any]]
    events: list[dict[str, Any]]
    degraded: bool = False


class OrchestratorPort(ABC):
    """Abstract agentic orchestrator."""

    @abstractmethod
    def run_screening(
        self,
        candidate_id: UUID,
        job_id: UUID | None,
        rubric_id: UUID | None,
        correlation_id: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield agent events and final result for a screening."""

    @abstractmethod
    def ask(
        self,
        question: str,
        job_id: UUID | None = None,
        correlation_id: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield chat answer chunks and citations."""
