"""Reviewer stats endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from copilot.application.use_cases.compute_reviewer_stats import compute_reviewer_stats
from copilot.infrastructure.di import Container
from copilot.presentation.dependencies import get_container, get_current_user

router = APIRouter()


@router.get("/reviewer-stats")
async def reviewer_stats(
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> dict:
    return await compute_reviewer_stats(container, user["role"])
