"""Async database session management."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from copilot.infrastructure.db.config import get_database_url

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=False,
            future=True,
        )
    return _engine


async_session_factory = async_sessionmaker(
    _get_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        yield session


async def close_engine() -> None:
    """Dispose the engine; used during graceful shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
