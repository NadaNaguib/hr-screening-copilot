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
    ) -> list[Evidence]:
        """Hybrid search returning evidence-like results."""
