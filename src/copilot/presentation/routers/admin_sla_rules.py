"""Admin SLA rules endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from copilot.application.use_cases.manage_sla_rules import create_or_update_sla_rule, list_sla_rules
from copilot.infrastructure.di import Container
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


class SLARuleRequest(BaseModel):
    job_id: UUID | None = None
    priority: str
    triage_hours: int
    decision_hours: int
    active: bool = True


@router.get("/admin/sla-rules")
async def get_sla_rules(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await list_sla_rules(container, user["role"])


@router.post("/admin/sla-rules")
async def post_sla_rule(
    request: SLARuleRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin")),
) -> dict:
    return await create_or_update_sla_rule(
        container=container,
        role=user["role"],
        job_id=request.job_id,
        priority=request.priority,
        triage_hours=request.triage_hours,
        decision_hours=request.decision_hours,
        active=request.active,
        created_by=user["id"],
    )
