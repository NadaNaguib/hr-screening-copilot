"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from copilot.presentation.dependencies import get_session

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"}, status_code=status.HTTP_200_OK)
    except Exception as exc:
        return JSONResponse(
            {"status": "not_ready", "error": str(exc)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
