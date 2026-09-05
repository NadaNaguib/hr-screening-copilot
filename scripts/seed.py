"""Idempotent seed script for local development and demo.

Usage:
    cd /root/main/hobby
    . .venv/bin/activate
    python scripts/seed.py
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from copilot.infrastructure.auth.service import hash_password
from copilot.infrastructure.config.settings import get_settings
from copilot.infrastructure.db.base import Base
from copilot.infrastructure.db.models import (
    CandidateORM,
    JobORM,
    ReviewTaskORM,
    RubricCriterionORM,
    RubricORM,
    SLARuleORM,
    UserORM,
)

DEFAULT_USERS = [
    ("admin@example.com", "Admin User", "admin"),
    ("recruiter@example.com", "HR Recruiter", "hr_recruiter"),
    ("manager@example.com", "Hiring Manager", "hiring_manager"),
]
DEFAULT_PASSWORD = "password123"

DEMO_JOBS = [
    {
        "title": "Senior Python Backend Engineer",
        "department": "Engineering",
        "description": "Build scalable backend services using Python, FastAPI, PostgreSQL.",
        "location": "Remote",
        "priority": "HIGH",
    },
    {
        "title": "Frontend React Developer",
        "department": "Engineering",
        "description": "Develop modern React/TypeScript user interfaces with Tailwind CSS.",
        "location": "Remote",
        "priority": "MEDIUM",
    },
    {
        "title": "DevOps Engineer",
        "department": "Platform",
        "description": "Maintain CI/CD pipelines, Docker, Kubernetes, and cloud infrastructure.",
        "location": "Hybrid",
        "priority": "LOW",
    },
]

RUBRIC_TEMPLATE = [
    ("Python proficiency", "Mastery of Python language and ecosystem.", "HIGH", True, ["python", "fastapi", "django"], 1, 5),
    ("System design", "Ability to design scalable, maintainable systems.", "HIGH", True, ["scalability", "architecture"], 1, 5),
    ("Communication", "Clear written and verbal communication.", "MEDIUM", False, ["communication", "teamwork"], 1, 5),
    ("Relevant experience", "Years and relevance of prior roles.", "MEDIUM", True, ["experience", "senior"], 1, 5),
]

CANDIDATE_NAMES = [
    ("Alice Johnson", "alice.johnson@example.com"),
    ("Bob Smith", "bob.smith@example.com"),
    ("Carol White", "carol.white@example.com"),
    ("David Brown", "david.brown@example.com"),
    ("Eva Green", "eva.green@example.com"),
]

CV_TEXTS = [
    "Senior Python engineer with 8 years of experience building FastAPI microservices and PostgreSQL data pipelines.",
    "Frontend developer specialized in React, TypeScript, and Tailwind CSS with a strong eye for UX.",
    "DevOps practitioner experienced with Docker, Kubernetes, Terraform, and AWS CI/CD pipelines.",
    "Full-stack developer comfortable with Python and React, leading small teams on SaaS products.",
    "Junior backend developer with Python and Django experience, eager to learn FastAPI.",
]


def _create_engine():
    url = get_settings().database_url
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Seed script requires an async PostgreSQL URL (postgresql+asyncpg://)")
    return create_async_engine(url, future=True)


async def _ensure_users(session: AsyncSession) -> list[UserORM]:
    users = []
    for email, full_name, role in DEFAULT_USERS:
        result = await session.execute(select(UserORM).where(UserORM.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = UserORM(
                id=uuid4(),
                email=email,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                full_name=full_name,
                role=role,
                is_active=True,
            )
            session.add(user)
        users.append(user)
    await session.flush()
    return users


async def _ensure_jobs(session: AsyncSession) -> list[JobORM]:
    jobs = []
    for data in DEMO_JOBS:
        result = await session.execute(select(JobORM).where(JobORM.title == data["title"]))
        job = result.scalar_one_or_none()
        if job is None:
            job = JobORM(
                id=uuid4(),
                title=data["title"],
                department=data["department"],
                description=data["description"],
                location=data["location"],
                priority=data["priority"],
            )
            session.add(job)
        jobs.append(job)
    await session.flush()
    return jobs


async def _ensure_rubrics(session: AsyncSession, jobs: list[JobORM]) -> None:
    for job in jobs:
        result = await session.execute(select(RubricORM).where(RubricORM.job_id == job.id))
        rubric = result.scalar_one_or_none()
        if rubric is None:
            rubric = RubricORM(
                id=uuid4(),
                job_id=job.id,
                name=f"{job.title} Rubric",
                description="Default rubric for screening.",
            )
            session.add(rubric)
            await session.flush()
            for name, desc, weight, required, keywords, min_score, max_score in RUBRIC_TEMPLATE:
                session.add(
                    RubricCriterionORM(
                        id=uuid4(),
                        rubric_id=rubric.id,
                        name=name,
                        description=desc,
                        weight=weight,
                        required=required,
                        keywords=keywords,
                        min_score=min_score,
                        max_score=max_score,
                    )
                )
    await session.flush()


async def _ensure_sla_rules(session: AsyncSession, jobs: list[JobORM]) -> None:
    defaults = [
        ("GLOBAL", None, "TRIAGE", "HIGH", 24),
        ("GLOBAL", None, "TRIAGE", "MEDIUM", 48),
        ("GLOBAL", None, "TRIAGE", "LOW", 72),
        ("GLOBAL", None, "DECISION", "HIGH", 24),
        ("GLOBAL", None, "DECISION", "MEDIUM", 48),
        ("GLOBAL", None, "DECISION", "LOW", 72),
    ]
    for scope_type, job_id, stage, priority, hours in defaults:
        result = await session.execute(
            select(SLARuleORM).where(
                SLARuleORM.scope_type == scope_type,
                SLARuleORM.job_id.is_(None),
                SLARuleORM.stage == stage,
                SLARuleORM.priority == priority,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(
                SLARuleORM(
                    id=uuid4(),
                    scope_type=scope_type,
                    scope_id="",
                    job_id=job_id,
                    stage=stage,
                    priority=priority,
                    duration_hours=hours,
                    active=True,
                )
            )
    if jobs:
        job = jobs[0]
        result = await session.execute(
            select(SLARuleORM).where(
                SLARuleORM.scope_type == "JOB",
                SLARuleORM.job_id == job.id,
                SLARuleORM.stage == "TRIAGE",
                SLARuleORM.priority == "HIGH",
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(
                SLARuleORM(
                    id=uuid4(),
                    scope_type="JOB",
                    scope_id=str(job.id),
                    job_id=job.id,
                    stage="TRIAGE",
                    priority="HIGH",
                    duration_hours=12,
                    active=True,
                )
            )
    await session.flush()


async def _ensure_candidates(session: AsyncSession, jobs: list[JobORM]) -> None:
    for idx, (name, email) in enumerate(CANDIDATE_NAMES):
        job = jobs[idx % len(jobs)]
        result = await session.execute(select(CandidateORM).where(CandidateORM.email == email))
        candidate = result.scalar_one_or_none()
        if candidate is None:
            candidate = CandidateORM(
                id=uuid4(),
                job_id=job.id,
                name=name,
                email=email,
                phone="+1-555-0000",
                cv_text=CV_TEXTS[idx % len(CV_TEXTS)],
                cv_sha256=f"demo-sha-{idx:04d}",
                status="PENDING",
                overall_score=None,
                priority=job.priority,
                source="seed",
                metadata={"seeded": True, "index": idx},
            )
            session.add(candidate)
            await session.flush()
            result2 = await session.execute(
                select(ReviewTaskORM).where(ReviewTaskORM.candidate_id == candidate.id)
            )
            if result2.scalar_one_or_none() is None:
                session.add(
                    ReviewTaskORM(
                        id=uuid4(),
                        job_id=job.id,
                        candidate_id=candidate.id,
                        status="PENDING_TRIAGE",
                        stage="TRIAGE",
                        priority=job.priority,
                    )
                )
    await session.flush()


async def seed() -> None:
    engine = _create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        users = await _ensure_users(session)
        jobs = await _ensure_jobs(session)
        await _ensure_rubrics(session, jobs)
        await _ensure_sla_rules(session, jobs)
        await _ensure_candidates(session, jobs)
        await session.commit()
        print("Seed complete.")
        print("Users:")
        for user in users:
            print(f"  {user.role:20s} {user.email} / password: {DEFAULT_PASSWORD}")
        print(f"Jobs: {len(jobs)}")
        print("Login as any user to start the demo.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
