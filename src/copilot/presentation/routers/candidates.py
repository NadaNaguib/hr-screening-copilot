"""Candidate endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, UploadFile
from pydantic import BaseModel

from copilot.application.use_cases.upload_candidate import upload_candidate
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


class CandidateUploadResponse(BaseModel):
    candidate_id: UUID
    review_task_id: UUID
    is_new: bool
    status: str
    extracted_skills: list[str] = []
    years_of_experience: float = 0.0


@router.post("/candidates")
async def upload_candidate_endpoint(
    job_id: UUID | None = None,
    file: UploadFile | None = None,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    if file is None:
        return {"error": "No file uploaded"}
    content = await file.read()
    result = await upload_candidate(
        container=container,
        filename=file.filename or "cv.txt",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
        job_id=job_id,
        full_name=file.filename or "",
        correlation_id=get_correlation_id(),
    )
    return result


@router.get("/candidates")
async def list_candidates(
    job_id: UUID | None = None,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    candidates = await container.candidate_repository.list_candidates(job_id)
    return [
        {
            "id": str(c.id),
            "full_name": c.full_name,
            "email": c.email,
            "job_id": str(c.job_id) if c.job_id else None,
            "status": c.status.value,
            "overall_score": c.overall_score,
            "priority": c.priority,
            "years_of_experience": c.years_of_experience,
            "skills": c.skills,
        }
        for c in candidates
    ]


@router.delete("/candidates/{candidate_id}")
async def delete_candidate_endpoint(
    candidate_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    from copilot.domain.errors import NotFoundError

    success = await container.candidate_repository.delete_candidate(candidate_id)
    if not success:
        raise NotFoundError(f"Candidate {candidate_id} not found")
    await container.audit.log(
        action="delete_candidate",
        target_type="candidate",
        target_id=str(candidate_id),
        actor_id=user["id"],
        actor_role=user["role"],
        details={"deleted": True},
        correlation_id=get_correlation_id(),
    )
    return {"message": f"Candidate {candidate_id} deleted successfully"}


@router.get("/candidates/{candidate_id}/cv")
async def get_candidate_cv(
    candidate_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> dict:
    from sqlalchemy import select
    from copilot.domain.errors import NotFoundError
    from copilot.infrastructure.db.models import DocumentORM

    cand = await container.candidate_repository.get_candidate(candidate_id)
    if not cand:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    docs_res = await container.session.execute(select(DocumentORM))
    doc = None
    for d in docs_res.scalars().all():
        meta = d.metadata_ or {}
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(cand.full_name.replace(" ", "_")):
            doc = d
            break

    cv_text = (doc.raw_text if doc and doc.raw_text else cand.raw_text) or ""
    filename = doc.filename if doc else f"{cand.full_name.replace(' ', '_')}_CV.txt"

    return {
        "candidate_id": str(cand.id),
        "full_name": cand.full_name,
        "email": cand.email,
        "job_id": str(cand.job_id) if cand.job_id else None,
        "raw_text": cv_text,
        "filename": filename,
        "document_id": str(doc.id) if doc else None,
        "mime_type": doc.mime_type if doc else "text/plain",
        "skills": cand.skills,
        "priority": cand.priority,
        "years_of_experience": cand.years_of_experience,
    }


@router.get("/candidates/{candidate_id}/cv/download")
async def download_candidate_cv(
    candidate_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> Response:
    from sqlalchemy import select
    from copilot.domain.errors import NotFoundError
    from copilot.infrastructure.db.models import DocumentORM

    cand = await container.candidate_repository.get_candidate(candidate_id)
    if not cand:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    docs_res = await container.session.execute(select(DocumentORM))
    doc = None
    for d in docs_res.scalars().all():
        meta = d.metadata_ or {}
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(cand.full_name.replace(" ", "_")):
            doc = d
            break

    cv_text = (doc.raw_text if doc and doc.raw_text else cand.raw_text) or ""
    filename = doc.filename if doc else f"{cand.full_name.replace(' ', '_')}_CV.txt"

    return Response(
        content=cv_text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/candidates/document/by-name")
async def get_document_by_name(
    filename: str,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> dict:
    from sqlalchemy import select
    from copilot.infrastructure.db.models import DocumentORM

    stmt = select(DocumentORM).where(DocumentORM.filename.ilike(f"%{filename}%")).limit(1)
    result = await container.session.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc:
        return {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "raw_text": doc.raw_text,
            "mime_type": doc.mime_type,
            "metadata": doc.metadata_,
        }
    return {
        "document_id": None,
        "filename": filename,
        "raw_text": "",
        "metadata": {},
    }
