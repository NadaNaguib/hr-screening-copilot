"""Shared Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://copilot:change-me-in-production@db:5432/hr_screening",
        alias="DATABASE_URL",
    )

    # Security
    jwt_secret: str = Field(default="replace-with-a-long-random-secret", alias="JWT_SECRET")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = "HS256"

    # LLM
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # Observability / Testing
    simulate_agent_failure: bool = Field(default=False, alias="SIMULATE_AGENT_FAILURE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # SLA auto-escalation engine
    sla_scheduler_enabled: bool = Field(default=True, alias="SLA_SCHEDULER_ENABLED")
    sla_scheduler_interval_minutes: int = Field(
        default=5, alias="SLA_SCHEDULER_INTERVAL_MINUTES"
    )

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])

    @field_validator("database_url", mode="before")
    @classmethod
    def _ensure_asyncpg(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
