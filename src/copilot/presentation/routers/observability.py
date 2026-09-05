"""Observability endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from copilot.infrastructure.config.settings import get_settings
from copilot.infrastructure.observability.token_cost import get_ledger
from copilot.presentation.dependencies import require_roles

router = APIRouter()


@router.get("/observability/token-cost")
async def token_cost(admin_user: dict = Depends(require_roles("admin"))) -> dict:
    return get_ledger().summary()


@router.get("/observability/settings")
async def observability_settings(admin_user: dict = Depends(require_roles("admin"))) -> dict:
    settings = get_settings()
    return {
        "simulate_agent_failure": settings.simulate_agent_failure,
        "gemini_model": settings.gemini_model,
        "log_level": settings.log_level,
    }


@router.post("/observability/simulate-agent-failure")
async def toggle_simulate_failure(
    value: bool,
    admin_user: dict = Depends(require_roles("admin")),
) -> dict:
    # Note: this only affects the current process; for production use a DB-backed flag.
    settings = get_settings()
    settings.simulate_agent_failure = value
    return {"simulate_agent_failure": settings.simulate_agent_failure}
