"""Generate and ingest a realistic sample candidate CV matching a job."""

from __future__ import annotations

import random
from uuid import UUID

from copilot.application.use_cases.run_screening_pipeline import run_screening_pipeline
from copilot.application.use_cases.upload_candidate import upload_candidate
from copilot.domain.errors import NotFoundError
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id

_SAMPLE_NAMES = [
    "Alex Rivera",
    "Maya Chen",
    "Jordan Taylor",
    "Samira El-Sayed",
    "Marcus Vance",
    "Elena Rostova",
    "Liam O'Connor",
    "Priya Sharma",
    "Zaid Mansour",
    "Clara Beaumont",
]


def _build_mimic_cv(name: str, job_title: str, department: str, skills: list[str]) -> str:
    primary_skills = skills if skills else ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]
    skills_str = ", ".join(primary_skills)

    return f"""CURRICULUM VITAE

FULL NAME: {name}
CONTACT: {name.lower().replace(" ", ".")}@example.com | +1 (555) 019-2834
TARGET ROLE: {job_title} ({department or "Engineering"})

PROFESSIONAL SUMMARY:
Accomplished and proactive professional with 5+ years of demonstrable hands-on experience in {job_title}. Proven expertise in building robust, scalable production systems, collaborating across cross-functional teams, and applying best practices in {skills_str}. Strong advocate for clean architecture, automated testing, and continuous delivery.

CORE TECHNICAL SKILLS:
- Core Technologies: {skills_str}
- Architecture & Patterns: Clean Architecture, REST APIs, Microservices, Event-driven systems
- Databases & Storage: PostgreSQL, Redis, Query Optimization, pgvector
- DevOps & CI/CD: Docker, Kubernetes, GitHub Actions, Linux, Monitoring

WORK EXPERIENCE:

Senior Specialist | CloudTech Solutions (2022 – Present)
- Led end-to-end technical implementation of core features directly leveraging {skills_str}.
- Improved system throughput by 40% through indexing, caching strategies, and database refactoring.
- Designed comprehensive test suites with >85% code coverage, reducing production defect rate by 30%.
- Mentored junior engineers and conducted peer code reviews adhering to stringent quality standards.

Software Engineer | Innovatech Labs (2019 – 2022)
- Built high-performance backend and integration services in a fast-paced agile environment.
- Contributed to microservices migration and modernized legacy codebase with automated CI pipelines.
- Collaborated with product managers and recruiters to deliver reliable user-facing features on schedule.

EDUCATION:
- B.Sc. in Computer Science & Engineering | Tech University (2015 – 2019)
  Honors: Magna Cum Laude, Dean's Honor List

CERTIFICATIONS & PROJECTS:
- Certified Solutions Architect
- Active open-source contributor to developer tooling and screening automation repositories
"""


async def mimic_candidate_for_job(
    container: Container,
    job_id: UUID,
    correlation_id: str = "",
) -> dict:
    """Generate a realistic CV matching job requirements and run full screening pipeline."""
    correlation_id = correlation_id or get_correlation_id()
    job = await container.document_repository.get_job(job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found")

    candidate_name = random.choice(_SAMPLE_NAMES)
    cv_text = _build_mimic_cv(
        name=candidate_name,
        job_title=job.title,
        department=job.department,
        skills=job.skills,
    )
    filename = f"{candidate_name.replace(' ', '_')}_Resume.txt"

    # Ingest candidate CV
    upload_result = await upload_candidate(
        container=container,
        filename=filename,
        content=cv_text.encode("utf-8"),
        mime_type="text/plain",
        job_id=job.id,
        full_name=candidate_name,
        correlation_id=correlation_id,
    )

    candidate_id = UUID(upload_result["candidate_id"])

    # Automatically run the screening pipeline so candidate is scored & queued
    try:
        pipeline_result = await run_screening_pipeline(
            container=container,
            candidate_id=candidate_id,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        pipeline_result = {"status": "error", "message": str(exc)}

    return {
        "candidate_id": str(candidate_id),
        "full_name": candidate_name,
        "job_id": str(job.id),
        "job_title": job.title,
        "extracted_skills": upload_result.get("extracted_skills", []),
        "years_of_experience": upload_result.get("years_of_experience", 5.0),
        "pipeline": pipeline_result,
    }
