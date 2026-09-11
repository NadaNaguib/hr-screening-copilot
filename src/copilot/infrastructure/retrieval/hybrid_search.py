"""Hybrid search service."""

from __future__ import annotations

from uuid import UUID

from copilot.application.ports.embedding_port import EmbeddingPort
from copilot.application.ports.vector_store_port import VectorStorePort
from copilot.domain.evidence import Evidence


class HybridSearch:
    """Combines dense vector and keyword retrieval with RRF fusion."""

    def __init__(self, vector_store: VectorStorePort, embedding: EmbeddingPort) -> None:
        self.vector_store = vector_store
        self.embedding = embedding

    async def search(
        self,
        query: str,
        job_id: UUID | None = None,
        top_k: int = 10,
    ) -> list[Evidence]:
        embedding = (await self.embedding.embed([query]))[0]
        return await self.vector_store.search(
            query_embedding=embedding,
            query_text=query,
            job_id=job_id,
            top_k=top_k,
        )
