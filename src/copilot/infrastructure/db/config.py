"""Database URL helper."""

from __future__ import annotations

from copilot.infrastructure.config.settings import get_settings


def get_database_url() -> str:
    """Return the configured async database URL."""
    return get_settings().database_url
