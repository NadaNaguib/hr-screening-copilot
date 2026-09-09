"""Job and rubric endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from copilot.application.use_cases.ingest_document import ingest_document
from copilot.domain.job import Job
from copilot.domain.rubric import CriterionWeight, Rubric, RubricCriterion
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


class JobCreate(BaseModel):
    title: str
    department: str = ""
    description: str = ""
    location: str = ""
    priority: str = "MEDIUM"
    skills: list[str] = Field(default_factory=list)


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
        priority=request.priority,
        skills=request.skills,
    )
    saved = await container.document_repository.create_job(job)
    return {
        "id": str(saved.id),
        "title": saved.title,
        "department": saved.department,
        "description": saved.description,
        "location": saved.location,
        "priority": saved.priority,
        "skills": saved.skills,
    }


@router.get("/jobs")
async def list_jobs(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    jobs = await container.document_repository.list_jobs()
    return [
        {
            "id": str(j.id),
            "title": j.title,
            "department": j.department,
            "description": j.description,
            "location": j.location,
            "priority": j.priority,
            "skills": j.skills,
        }
        for j in jobs
    ]


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
    rubric = Rubric(job_id=job_id, name=request.name, description=request.description, criteria=criteria)
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
    from copilot.domain.errors import NotFoundError

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
