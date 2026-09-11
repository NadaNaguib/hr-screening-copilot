"""FastAPI application factory."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from copilot.infrastructure.db.session import async_session_factory, close_engine
from copilot.infrastructure.observability.correlation import get_correlation_id, set_correlation_id
from copilot.infrastructure.observability.logging import configure_logging
from copilot.presentation.routers import (
    admin_ai_config,
    admin_sla_rules,
    admin_users,
    auth,
    candidates,
    chat,
    health,
    jobs,
    observability,
    pipeline,
    review_queue,
    reviewer_stats,
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # settings = get_settings()
    # Verify DB connectivity with retries
    for _ in range(10):
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            break
        except Exception:
            import asyncio

            await asyncio.sleep(1.0)
    yield
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Domain Copilot — HR Screening",
        description="Agentic RAG platform for HR talent screening",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        cid = get_correlation_id()
        if isinstance(exc, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "error_code": "validation_error",
                    "message": str(exc),
                    "correlation_id": cid,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "internal_error",
                "message": "Internal server error",
                "correlation_id": cid,
            },
        )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(candidates.router, prefix="/api/v1", tags=["candidates"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["pipeline"])
    app.include_router(review_queue.router, prefix="/api/v1", tags=["review-queue"])
    app.include_router(reviewer_stats.router, prefix="/api/v1", tags=["stats"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(admin_users.router, prefix="/api/v1", tags=["admin"])
    app.include_router(admin_sla_rules.router, prefix="/api/v1", tags=["admin"])
    app.include_router(admin_ai_config.router, prefix="/api/v1", tags=["admin"])
    app.include_router(observability.router, prefix="/api/v1", tags=["observability"])

    return app


app = create_app()
