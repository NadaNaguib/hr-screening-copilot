"""Review queue and decision endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from copilot.application.use_cases.admin_override import admin_override
from copilot.application.use_cases.bulk_review_action import bulk_review_action
from copilot.application.use_cases.decide_candidate import decide_candidate
from copilot.application.use_cases.query_review_queue import query_review_queue
from copilot.application.use_cases.triage_candidate import triage_candidate
from copilot.application.use_cases.update_task_priority import update_task_priority
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


class TriageRequest(BaseModel):
    task_id: UUID
    action: str  # forward_to_manager | reject_at_triage
    reason: str | None = None


class DecideRequest(BaseModel):
    task_id: UUID
    action: str  # approve | reject | edit_and_approve
    reason: str | None = None


class AdminOverrideRequest(BaseModel):
    task_id: UUID
    reason: str


class UpdatePriorityRequest(BaseModel):
    task_id: UUID
    priority: str  # HIGH | MEDIUM | LOW


class BulkActionRequest(BaseModel):
    task_ids: list[UUID] = Field(min_length=1, max_length=200)
    action: str  # forward_to_manager | reject_at_triage | approve | reject | edit_and_approve
    reason: str | None = None


@router.get("/review-queue")
async def get_review_queue(
    job_id: UUID | None = None,
    status: list[str] | None = None,
    search: str | None = None,
    priority: str | None = None,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await query_review_queue(
        container=container,
        role=user["role"],
        job_id=job_id,
        status=status,
        search=search,
        priority=priority,
    )


@router.post("/review-queue/triage")
async def post_triage(
    request: TriageRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("hr_recruiter", "admin")),
) -> dict:
    return await triage_candidate(
        container=container,
        actor_id=user["id"],
        role=user["role"],
        task_id=request.task_id,
        action=request.action,
        reason=request.reason,
        correlation_id=get_correlation_id(),
    )


@router.post("/review-queue/decide")
async def post_decide(
    request: DecideRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("hiring_manager", "admin")),
) -> dict:
    return await decide_candidate(
        container=container,
        actor_id=user["id"],
        role=user["role"],
        task_id=request.task_id,
        action=request.action,
        reason=request.reason,
        correlation_id=get_correlation_id(),
    )


@router.post("/review-queue/admin-override")
async def post_admin_override(
    request: AdminOverrideRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin")),
) -> dict:
    return await admin_override(
        container=container,
        actor_id=user["id"],
        role=user["role"],
        task_id=request.task_id,
        reason=request.reason,
        correlation_id=get_correlation_id(),
    )


@router.post("/review-queue/update-priority")
async def post_update_priority(
    request: UpdatePriorityRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    return await update_task_priority(
        container=container,
        actor_id=user["id"],
        role=user["role"],
        task_id=request.task_id,
        priority=request.priority,
        correlation_id=get_correlation_id(),
    )


@router.post("/review-queue/bulk")
async def post_bulk_action(
    request: BulkActionRequest,
    container: Container = Depends(get_container),
    # Admin is intentionally excluded: bulk mutations are read-only-disabled for admin.
    user: dict = Depends(require_roles("hr_recruiter", "hiring_manager")),
) -> dict:
    return await bulk_review_action(
        container=container,
        actor_id=user["id"],
        role=user["role"],
        task_ids=request.task_ids,
        action=request.action,
        reason=request.reason,
        correlation_id=get_correlation_id(),
    )


@router.get("/shortlist/{shortlist_id}/export")
async def export_shortlist_endpoint(
    shortlist_id: UUID,
    format: str = "csv",
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("hiring_manager", "admin")),
):
    """Export a finalized shortlist as CSV or PDF."""
    from fastapi.responses import Response

    from copilot.application.use_cases.export_shortlist import export_shortlist

    data, content_type = await export_shortlist(
        container=container,
        role=user["role"],
        shortlist_id=shortlist_id,
        format=format,
    )
    filename = f"shortlist-{shortlist_id}.{format}"
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
