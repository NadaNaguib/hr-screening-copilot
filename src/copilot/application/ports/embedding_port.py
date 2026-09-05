"""Embedding port interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed(self, texts: list[str], correlation_id: str = "") -> list[list[float]]:
        """Return an embedding vector for each input text."""

    @abstractmethod
    def dimensions(self) -> int:
        """Return vector dimensions."""

    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
