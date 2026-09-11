"""Screening pipeline endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from copilot.application.use_cases.run_screening_pipeline import run_screening_pipeline
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.presentation.dependencies import get_container, require_roles

router = APIRouter()


class RunPipelineRequest(BaseModel):
    candidate_id: UUID


@router.post("/pipeline/run")
async def run_pipeline(
    request: RunPipelineRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(require_roles("admin", "hr_recruiter")),
) -> dict:
    return await run_screening_pipeline(
        container=container,
        candidate_id=request.candidate_id,
        correlation_id=get_correlation_id(),
    )
