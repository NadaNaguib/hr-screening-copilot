"""Optional reranker (placeholder / identity)."""
from __future__ import annotations

from copilot.domain.evidence import Evidence


class Reranker:
    """Rerank evidence by a simple heuristic."""

    async def rerank(self, query: str, evidence: list[Evidence], top_k: int = 10) -> list[Evidence]:
        # Placeholder: sort by confidence descending.
        scored = sorted(evidence, key=lambda e: e.confidence, reverse=True)
        return scored[:top_k]
