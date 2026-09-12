"""Vector store repository port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from copilot.domain.evidence import Evidence


class VectorStorePort(ABC):
    """Vector store + keyword retrieval operations."""

    @abstractmethod
    async def ingest_chunks(
        self,
        job_id: UUID | None,
        document_id: UUID,
        chunks: list[tuple[str, int | None, dict]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """Store text chunks (with optional embeddings)."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        query_text: str,
        job_id: UUID | None = None,
        top_k: int = 10,
        candidate_id: UUID | None = None,
    ) -> list[Evidence]:
        """Hybrid search returning evidence-like results.

        When ``candidate_id`` is supplied the query is hard-scoped to that
        candidate's chunks, so no other applicant's data can be retrieved.
        """
