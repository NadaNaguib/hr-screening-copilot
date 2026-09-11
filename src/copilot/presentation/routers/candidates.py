"""Candidate endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from copilot.agents.interview_probe_generator import generate_interview_probes
from copilot.application.use_cases.upload_candidate import upload_candidate
from copilot.domain.errors import NotFoundError
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.infrastructure.parsing.parser import is_supported_document
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()

_SUPPORTED_FORMATS_HINT = "PDF, DOCX, or TXT"
# Multipart field names we accept for the resume file (the React client sends "file").
_ACCEPTED_FILE_FIELDS = ("file", "cv", "resume", "upload", "document")
_MAX_PART_SIZE_BYTES = 10 * 1024 * 1024


class CandidateUploadResponse(BaseModel):
    candidate_id: UUID
    review_task_id: UUID
    is_new: bool
    status: str
    extracted_skills: list[str] = []
    years_of_experience: float = 0.0


@router.post("/candidates")
async def upload_candidate_endpoint(
    request: Request,
    job_id: UUID | None = None,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    # Parse the multipart form directly. This keeps the handler independent of
    # FastAPI's form/file parameter inference and tolerant to field naming, so
    # the uploaded payload can never be silently dropped.
    try:
        form = await request.form(max_part_size=_MAX_PART_SIZE_BYTES)
    except TypeError:  # older Starlette without max_part_size
        form = await request.form()

    upload = None
    for field_name in _ACCEPTED_FILE_FIELDS:
        value = form.get(field_name)
        if value is not None and hasattr(value, "read"):
            upload = value
            break

    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "missing_file",
                "message": (
                    "No file uploaded. Attach a resume as a multipart field named "
                    f"'file' (accepted formats: {_SUPPORTED_FORMATS_HINT})."
                ),
            },
        )

    filename = (getattr(upload, "filename", None) or "cv.txt").strip() or "cv.txt"
    mime_type = getattr(upload, "content_type", None) or "application/octet-stream"
    content = await upload.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "empty_file", "message": "The uploaded file is empty"},
        )

    if not is_supported_document(filename, mime_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "unsupported_file_type",
                "message": (
                    f"Unsupported file type '{filename}'. "
                    f"Supported formats: {_SUPPORTED_FORMATS_HINT}."
                ),
            },
        )

    form_job_id = form.get("job_id")
    if hasattr(form_job_id, "read"):
        form_job_id = None
    raw_job_id = form_job_id or (str(job_id) if job_id else None)
    if not raw_job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "missing_job_id",
                "message": "A job_id is required so the candidate is linked to a vacancy.",
            },
        )
    try:
        resolved_job_id = UUID(str(raw_job_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "invalid_job_id",
                "message": f"Invalid job_id '{raw_job_id}'.",
            },
        ) from None

    return await upload_candidate(
        container=container,
        filename=filename,
        content=content,
        mime_type=mime_type,
        job_id=resolved_job_id,
        full_name=filename,
        correlation_id=get_correlation_id(),
    )


@router.post("/candidates/{candidate_id}/generate-probes", status_code=status.HTTP_201_CREATED)
async def generate_candidate_probes(
    candidate_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hiring_manager", "hr_recruiter")),
) -> dict:
    """Generate and persist tailored interview probes for a screened candidate.

    Probes are produced on demand so that LLM tokens are only spent when a
    recruiter explicitly asks for them (the mimic flow generates them eagerly
    as part of its single end-to-end run).
    """
    candidate = await container.candidate_repository.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    job = (
        await container.document_repository.get_job(candidate.job_id)
        if candidate.job_id
        else None
    )
    probes = await generate_interview_probes(
        llm=container.llm,
        candidate=candidate,
        job=job,
        correlation_id=get_correlation_id(),
    )

    candidate.set_interview_probes(probes)
    await container.candidate_repository.update_candidate(candidate)

    await container.audit.log(
        action="generate_interview_probes",
        target_type="candidate",
        target_id=str(candidate_id),
        actor_id=user["id"],
        actor_role=user["role"],
        details={"probe_count": len(probes)},
        correlation_id=get_correlation_id(),
    )
    return {
        "candidate_id": str(candidate_id),
        "probes_generated": True,
        "interview_probes": probes,
    }


class InterviewProbesUpdate(BaseModel):
    interview_probes: list[dict] = []


@router.put("/candidates/{candidate_id}/probes")
async def update_candidate_probes(
    candidate_id: UUID,
    payload: InterviewProbesUpdate,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hiring_manager", "hr_recruiter")),
) -> dict:
    """Persist recruiter/manager edits to a candidate's interview probes.

    Editing probes never requires a decision comment — only *rejecting* a
    candidate does. Empty questions are dropped so a saved set is always clean.
    """
    candidate = await container.candidate_repository.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    cleaned: list[dict] = []
    for item in payload.interview_probes:
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        category = str(item.get("category", "technical")).strip() or "technical"
        cleaned.append({"category": category, "question": question})

    candidate.set_interview_probes(cleaned)
    await container.candidate_repository.update_candidate(candidate)

    await container.audit.log(
        action="update_interview_probes",
        target_type="candidate",
        target_id=str(candidate_id),
        actor_id=user["id"],
        actor_role=user["role"],
        details={"probe_count": len(cleaned)},
        correlation_id=get_correlation_id(),
    )
    return {
        "candidate_id": str(candidate_id),
        "probes_generated": candidate.probes_generated,
        "interview_probes": cleaned,
    }


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
            "probes_generated": c.probes_generated,
            "interview_probes": c.interview_probes,
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
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(
            cand.full_name.replace(" ", "_")
        ):
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
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(
            cand.full_name.replace(" ", "_")
        ):
            doc = d
            break

    cv_text = (doc.raw_text if doc and doc.raw_text else cand.raw_text) or ""
    filename = doc.filename if doc else f"{cand.full_name.replace(' ', '_')}_CV.txt"

    return Response(
        content=cv_text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/candidates/{candidate_id}/cv/pdf")
async def get_candidate_cv_pdf(
    candidate_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> Response:
    import base64
    import os

    from sqlalchemy import select

    from copilot.domain.errors import NotFoundError
    from copilot.infrastructure.db.models import DocumentORM
    from copilot.infrastructure.parsing.pdf_generator import generate_cv_pdf

    cand = await container.candidate_repository.get_candidate(candidate_id)
    if not cand:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    docs_res = await container.session.execute(select(DocumentORM))
    doc = None
    for d in docs_res.scalars().all():
        meta = d.metadata_ or {}
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(
            cand.full_name.replace(" ", "_")
        ):
            doc = d
            break

    # 1. If uploaded as a real PDF and stored in metadata
    meta = (doc.metadata_ if doc else {}) or {}
    if "pdf_bytes_b64" in meta:
        pdf_bytes = base64.b64decode(meta["pdf_bytes_b64"])
        filename = (
            doc.filename
            if doc and doc.filename.endswith(".pdf")
            else f"{cand.full_name.replace(' ', '_')}_CV.pdf"
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # 2. Check if cached on disk
    disk_path = f"/tmp/cv_storage/{cand.id}_{cand.full_name.replace(' ', '_')}_CV.pdf"
    if os.path.exists(disk_path):  # noqa: ASYNC230, ASYNC240
        with open(disk_path, "rb") as f:  # noqa: ASYNC230, ASYNC240
            return Response(
                content=f.read(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{cand.full_name.replace(" ", "_")}_CV.pdf"'
                },
            )

    # 3. Generate authentic PDF resume using reportlab
    cv_text = (doc.raw_text if doc and doc.raw_text else cand.raw_text) or ""
    pdf_bytes = generate_cv_pdf(
        full_name=cand.full_name,
        cv_text=cv_text,
        email=cand.email or "",
        skills=cand.skills or [],
        years_of_experience=cand.years_of_experience or 0.0,
    )
    filename = f"{cand.full_name.replace(' ', '_')}_CV.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
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
