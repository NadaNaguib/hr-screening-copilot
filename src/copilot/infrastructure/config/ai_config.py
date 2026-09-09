"""Mutable runtime AI configuration.

This module holds runtime-overridable AI settings. It is separate from the
Pydantic Settings object so that admin changes can take effect immediately
without restarting the process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copilot.infrastructure.config.settings import get_settings


@dataclass
class AIConfig:
    """Runtime AI/RAG configuration."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ai_enabled: bool = True
    plain_rag_enabled: bool = True
    agentic_rag_enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


class AIConfigManager:
    """Singleton runtime AI configuration manager."""

    _instance: AIConfigManager | None = None

    def __new__(cls) -> AIConfigManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            settings = get_settings()
            initial_model = settings.gemini_model or "gemini-2.5-flash"
            if initial_model == "gemini-2.5-pro":
                initial_model = "gemini-2.5-flash"
            cls._instance._config = AIConfig(
                gemini_api_key=settings.gemini_api_key,
                gemini_model=initial_model,
                ai_enabled=True,
                plain_rag_enabled=True,
                agentic_rag_enabled=True,
            )
        return cls._instance

    @property
    def config(self) -> AIConfig:
        return self._config

    def update(self, **kwargs: Any) -> None:
        if kwargs.get("gemini_model") == "gemini-2.5-pro":
            kwargs["gemini_model"] = "gemini-2.5-flash"
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                self._config.extra[key] = value

    def to_dict(self, include_key: bool = False) -> dict[str, Any]:
        return {
            "gemini_api_key": self._config.gemini_api_key if include_key else "***" if self._config.gemini_api_key else "",
            "gemini_model": self._config.gemini_model,
            "ai_enabled": self._config.ai_enabled,
            "plain_rag_enabled": self._config.plain_rag_enabled,
            "agentic_rag_enabled": self._config.agentic_rag_enabled,
            **self._config.extra,
        }


def get_ai_config() -> AIConfig:
    """Return the current runtime AI configuration."""
    return AIConfigManager().config
