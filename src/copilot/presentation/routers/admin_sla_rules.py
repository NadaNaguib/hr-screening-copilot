"""Admin SLA rules endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from copilot.application.use_cases.manage_sla_rules import (
    create_or_update_sla_rule,
    delete_sla_rule,
    list_active_sla_priorities,
    list_sla_rules,
)
from copilot.infrastructure.di import Container
from copilot.presentation.dependencies import get_container, get_current_user, require_roles

router = APIRouter()


class SLARuleRequest(BaseModel):
    id: UUID | None = None  # present => update the existing rule; absent => create
    job_id: UUID | None = None
    priority: str = Field(min_length=1, max_length=20)
    triage_hours: int = Field(ge=1, le=8760)
    decision_hours: int = Field(ge=1, le=8760)
    active: bool = True

    @field_validator("id", "job_id", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        """Treat ``""``/whitespace as "not supplied" so null-ish ids don't 422/500."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def _clean_priority(cls, value: object) -> object:
        if value is None:
            return value
        return " ".join(str(value).split())


@router.get("/admin/sla-rules")
async def get_sla_rules(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await list_sla_rules(container, user["role"])


@router.get("/admin/sla-rules/priorities")
async def get_sla_rule_priorities(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> list[str]:
    """Distinct priority levels from active SLA rules (drives the queue filter)."""
    return await list_active_sla_priorities(container, user["role"])


@router.delete("/admin/sla-rules/{rule_id}")
async def delete_sla_rule_endpoint(
    rule_id: UUID,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin")),
) -> dict:
    return await delete_sla_rule(container=container, role=user["role"], rule_id=rule_id)


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
        rule_id=request.id,
    )
