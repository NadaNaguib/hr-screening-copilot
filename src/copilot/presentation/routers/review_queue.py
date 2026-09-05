"""Review queue and decision endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from copilot.application.use_cases.admin_override import admin_override
from copilot.application.use_cases.decide_candidate import decide_candidate
from copilot.application.use_cases.query_review_queue import query_review_queue
from copilot.application.use_cases.triage_candidate import triage_candidate
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


@router.get("/review-queue")
async def get_review_queue(
    job_id: UUID | None = None,
    status: list[str] | None = None,
    search: str | None = None,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await query_review_queue(
        container=container,
        role=user["role"],
        job_id=job_id,
        status=status,
        search=search,
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
