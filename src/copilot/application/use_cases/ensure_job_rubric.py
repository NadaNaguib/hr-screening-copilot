"""Ensure every job has a rubric so candidates can always be scored.

Jobs created through the UI (or legacy jobs without an explicit rubric) have no
scoring criteria, which previously caused ``run_screening_pipeline`` to leave
``overall_score`` at ``0``. This module derives a sensible default rubric from
the job's required skills so the pipeline always produces a Match Score.
"""
from __future__ import annotations

from copilot.domain.job import Job
from copilot.domain.rubric import CriterionWeight, Rubric, RubricCriterion
from copilot.infrastructure.di import Container


def build_default_rubric(job: Job) -> Rubric:
    """Build a deterministic rubric from a job's required skills."""
    skills = [s.strip() for s in (job.skills or []) if s and s.strip()]
    criteria: list[RubricCriterion] = []

    if skills:
        for index, skill in enumerate(skills[:6]):
            criteria.append(
                RubricCriterion(
                    name=f"{skill} proficiency",
                    description=f"Demonstrated hands-on experience with {skill}.",
                    weight=CriterionWeight.HIGH if index < 2 else CriterionWeight.MEDIUM,
                    required=index < 2,
                    keywords=[skill.lower()],
                    min_score=1,
                    max_score=5,
                )
            )
    else:
        criteria.append(
            RubricCriterion(
                name="Core technical skills",
                description="Relevant technical skills for the role.",
                weight=CriterionWeight.HIGH,
                required=True,
                keywords=["python", "javascript", "sql", "docker"],
                min_score=1,
                max_score=5,
            )
        )

    criteria.append(
        RubricCriterion(
            name="Relevant experience",
            description="Years and relevance of prior professional experience.",
            weight=CriterionWeight.HIGH,
            required=True,
            keywords=["experience", "years", "senior"],
            min_score=1,
            max_score=5,
        )
    )
    criteria.append(
        RubricCriterion(
            name="Communication & collaboration",
            description="Clear communication, teamwork, and collaboration.",
            weight=CriterionWeight.MEDIUM,
            required=False,
            keywords=["communication", "teamwork", "collaboration", "leadership", "mentor"],
            min_score=1,
            max_score=5,
        )
    )

    return Rubric(
        job_id=job.id,
        name=f"{job.title or 'Role'} — Default Rubric",
        description="Auto-generated rubric derived from the job's required skills.",
        criteria=criteria,
    )


async def ensure_job_rubric(container: Container, job: Job) -> Rubric | None:
    """Return the job's rubric, creating a sensible default when none exists."""
    if job is None or job.id is None:
        return None
    existing = await container.document_repository.get_rubric_for_job(job.id)
    if existing is not None:
        return existing
    return await container.document_repository.create_rubric(build_default_rubric(job))
