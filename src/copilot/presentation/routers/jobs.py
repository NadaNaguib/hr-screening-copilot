"""Job and rubric endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from copilot.application.use_cases.ensure_job_rubric import ensure_job_rubric
from copilot.application.use_cases.ingest_document import ingest_document
from copilot.domain.errors import NotFoundError
from copilot.domain.job import Job
from copilot.domain.rubric import CriterionWeight, Rubric, RubricCriterion
from copilot.domain.sla_rule import normalize_priority
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


def _job_payload(job: Job) -> dict:
    """Serialize a Job domain object for API responses."""
    return {
        "id": str(job.id),
        "title": job.title,
        "department": job.department,
        "description": job.description,
        "location": job.location,
        "priority": job.priority,
        "skills": job.skills,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    department: str = ""
    description: str = ""
    location: str = ""
    priority: str = Field(default="MEDIUM", min_length=1, max_length=20)
    skills: list[str] = Field(default_factory=list)


class JobUpdate(BaseModel):
    """Partial update payload for the Job Details modal.

    Every field is optional so the client can send just the values it changed
    (a ``PATCH``); omitted fields keep their current value.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = None
    description: str | None = None
    location: str | None = None
    priority: str | None = Field(default=None, min_length=1, max_length=20)
    skills: list[str] | None = None


class RubricCriterionCreate(BaseModel):
    name: str
    description: str = ""
    weight: CriterionWeight = CriterionWeight.MEDIUM
    required: bool = False
    keywords: list[str] = Field(default_factory=list)
    min_score: int = 1
    max_score: int = 5


class RubricCreate(BaseModel):
    name: str
    description: str = ""
    criteria: list[RubricCriterionCreate]


@router.post("/jobs")
async def create_job(
    request: JobCreate,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    job = Job(
        title=request.title,
        department=request.department,
        description=request.description,
        location=request.location,
        priority=normalize_priority(request.priority),
        skills=request.skills,
    )
    saved = await container.document_repository.create_job(job)
    # Provision a default rubric so newly created jobs can be scored immediately.
    await ensure_job_rubric(container, saved)
    return _job_payload(saved)


@router.get("/jobs")
async def list_jobs(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    jobs = await container.document_repository.list_jobs()
    return [_job_payload(j) for j in jobs]


@router.get("/jobs/{job_id}")
async def get_job_endpoint(
    job_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> dict:
    """Return the full details of a single job (used by the Job Details modal)."""
    job = await container.document_repository.get_job(job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found")
    return _job_payload(job)


@router.patch("/jobs/{job_id}")
async def update_job_endpoint(
    job_id: UUID,
    request: JobUpdate,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    """Partially update a job vacancy (edit from the Job Details modal)."""
    job = await container.document_repository.get_job(job_id)
    if job is None:
        raise NotFoundError(f"Job {job_id} not found")

    changed: dict = {}
    if request.title is not None:
        job.title = request.title
        changed["title"] = job.title
    if request.department is not None:
        job.department = request.department
        changed["department"] = job.department
    if request.description is not None:
        job.description = request.description
        changed["description"] = job.description
    if request.location is not None:
        job.location = request.location
        changed["location"] = job.location
    if request.priority is not None:
        job.priority = normalize_priority(request.priority)
        changed["priority"] = job.priority
    if request.skills is not None:
        # Drop blanks so a saved skills list is always clean.
        job.skills = [s.strip() for s in request.skills if s and s.strip()]
        changed["skills"] = job.skills

    job.updated_at = datetime.utcnow()
    updated = await container.document_repository.update_job(job)
    if updated is None:
        raise NotFoundError(f"Job {job_id} not found")

    await container.audit.log(
        action="update_job",
        target_type="job",
        target_id=str(job_id),
        actor_id=user["id"],
        actor_role=user["role"],
        details={"fields": sorted(changed.keys())},
        correlation_id=get_correlation_id(),
    )
    return _job_payload(updated)


@router.post("/jobs/{job_id}/rubrics")
async def create_rubric(
    job_id: UUID,
    request: RubricCreate,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    criteria = [
        RubricCriterion(
            name=c.name,
            description=c.description,
            weight=c.weight,
            required=c.required,
            keywords=c.keywords,
            min_score=c.min_score,
            max_score=c.max_score,
        )
        for c in request.criteria
    ]
    rubric = Rubric(
        job_id=job_id, name=request.name, description=request.description, criteria=criteria
    )
    saved = await container.document_repository.create_rubric(rubric)
    return {"id": str(saved.id), "criteria_count": len(saved.criteria)}


@router.post("/jobs/{job_id}/documents")
async def upload_job_document(
    job_id: UUID,
    filename: str,
    content: bytes,
    mime_type: str = "application/pdf",
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    return await ingest_document(
        container=container,
        filename=filename,
        content=content,
        mime_type=mime_type,
        job_id=job_id,
        correlation_id=get_correlation_id(),
    )


@router.delete("/jobs/{job_id}")
async def delete_job_endpoint(
    job_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    success = await container.document_repository.delete_job(job_id)
    if not success:
        raise NotFoundError(f"Job {job_id} not found")
    await container.audit.log(
        action="delete_job",
        target_type="job",
        target_id=str(job_id),
        actor_id=user["id"],
        actor_role=user["role"],
        details={"deleted": True},
        correlation_id=get_correlation_id(),
    )
    return {"message": f"Job {job_id} deleted successfully"}


@router.post("/jobs/{job_id}/mimic-candidate")
async def mimic_candidate_endpoint(
    job_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    from copilot.application.use_cases.mimic_candidate import mimic_candidate_for_job

    return await mimic_candidate_for_job(
        container=container,
        job_id=job_id,
        correlation_id=get_correlation_id(),
    )
