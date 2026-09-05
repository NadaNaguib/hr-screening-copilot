"""Chat / SSE endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from copilot.application.use_cases.ask_copilot import ask_copilot
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.infrastructure.sse.helpers import sse_event_stream
from copilot.presentation.dependencies import get_container, get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    job_id: UUID | None = None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    container: Container = Depends(get_container),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    correlation_id = get_correlation_id()
    stream = ask_copilot(
        container=container,
        question=request.question,
        job_id=request.job_id,
        correlation_id=correlation_id,
    )
    return StreamingResponse(
        sse_event_stream(stream),
        media_type="text/event-stream",
        headers={"X-Correlation-ID": correlation_id},
    )
