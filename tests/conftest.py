"""Shared pytest fixtures."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from copilot.infrastructure.db.base import Base
from copilot.infrastructure.db.models import (
    CandidateORM,
    JobORM,
    ReviewTaskORM,
    SLARuleORM,
    UserORM,
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://copilot:copilot@localhost:5432/hr_screening_test",
)

# Ensure the application and its global session factory bind to the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        echo=False,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def job(session: AsyncSession) -> JobORM:
    job = JobORM(
        id=uuid4(),
        title="Senior Python Backend Engineer",
        department="Engineering",
        description="Build scalable backend services.",
        location="Remote",
        priority="HIGH",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


@pytest_asyncio.fixture
async def candidate(session: AsyncSession, job: JobORM) -> CandidateORM:
    candidate = CandidateORM(
        id=uuid4(),
        job_id=job.id,
        name="Alice Johnson",
        email="alice.johnson@example.com",
        phone="+1-555-0001",
        cv_text="Senior Python engineer with FastAPI experience.",
        cv_sha256="sha256-alice",
        status="PENDING",
        priority="HIGH",
        source="test",
    )
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


@pytest_asyncio.fixture
async def review_task(session: AsyncSession, job: JobORM, candidate: CandidateORM) -> ReviewTaskORM:
    task = ReviewTaskORM(
        id=uuid4(),
        job_id=job.id,
        candidate_id=candidate.id,
        status="PENDING_TRIAGE",
        stage="TRIAGE",
        priority="HIGH",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task
