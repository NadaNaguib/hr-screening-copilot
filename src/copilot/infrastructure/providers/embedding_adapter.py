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

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.environ.get("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
        self.api_key = api_key
        self._configured = False

    def _ensure_config(self) -> None:
        from copilot.infrastructure.config.ai_config import AIConfigManager

        manager = AIConfigManager()
        if self.api_key is None:
            self.api_key = manager.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    def name(self) -> str:
        return "gemini-embedding"

    def dimensions(self) -> int:
        return DIMENSIONS

    async def embed(self, texts: list[str], correlation_id: str = "") -> list[list[float]]:
        import asyncio
        from copilot.infrastructure.config.ai_config import AIConfigManager

        ai_config = AIConfigManager().config
        if not ai_config.ai_enabled:
            return [_deterministic_embedding(t) for t in texts]
        self._ensure_config()
        if not self.api_key:
            return [_deterministic_embedding(t) for t in texts]
        try:
            import google.generativeai as genai

            if not self._configured:
                genai.configure(api_key=self.api_key)
                self._configured = True

            result = await asyncio.to_thread(
                genai.embed_content,
                model=self.model,
                content=texts if len(texts) > 1 else texts[0],
                task_type="retrieval_document",
                output_dimensionality=self.dimensions(),
            )
            if "embedding" in result:
                val = result["embedding"]
                if val and isinstance(val[0], list):
                    return val  # type: ignore[return-value]
                return [val]  # type: ignore[return-value]
            if "embeddings" in result:
                return result["embeddings"]  # type: ignore[return-value]
            return [_deterministic_embedding(t) for t in texts]
        except Exception:
            # Degrade to deterministic embeddings on failure.
            return [_deterministic_embedding(t) for t in texts]
