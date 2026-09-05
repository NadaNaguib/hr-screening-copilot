"""Gemini embedding adapter with deterministic fallback."""
from __future__ import annotations

import hashlib
import os
from typing import Any

from copilot.application.ports.embedding_port import EmbeddingPort
from copilot.infrastructure.config.settings import get_settings

DIMENSIONS = 768


def _deterministic_embedding(text: str, dim: int = DIMENSIONS) -> list[float]:
    """Return a deterministic pseudo-random unit-ish vector for offline/demo use."""
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
    values: list[float] = []
    for _ in range(dim):
        # simple LCG
        seed = (1103515245 * seed + 12345) % (2**31)
        values.append((seed / (2**31)) * 2 - 1)
    return values


class GeminiEmbeddingAdapter(EmbeddingPort):
    """Embedding adapter using Gemini API or deterministic fallback."""

    def __init__(self, model: str = "models/text-embedding-004", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or get_settings().gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client: Any | None = None

    def name(self) -> str:
        return "gemini-embedding"

    def dimensions(self) -> int:
        return DIMENSIONS

    async def embed(self, texts: list[str], correlation_id: str = "") -> list[list[float]]:
        if not self.api_key:
            return [_deterministic_embedding(t) for t in texts]
        try:
            import google.generativeai as genai

            if self._client is None:
                genai.configure(api_key=self.api_key)
            result = await genai.embed_content_async(
                model=self.model,
                content=texts,
                task_type="retrieval_document",
            )
            embeddings = result.get("embedding", [])
            if not embeddings and "embeddings" in result:
                embeddings = result["embeddings"]
            return embeddings
        except Exception:
            # Degrade to deterministic embeddings on failure.
            return [_deterministic_embedding(t) for t in texts]
