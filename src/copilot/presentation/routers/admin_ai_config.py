"""Admin AI/RAG settings and usage endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from copilot.infrastructure.config.ai_config import AIConfigManager
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.infrastructure.observability.token_cost import (
    FailureRecord,
    TokenCostRecord,
    get_ledger,
)
from copilot.presentation.dependencies import require_roles

router = APIRouter()

AVAILABLE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemma-4-31b-it",
    "gemma-4-26b-it",
    "gemini-flash-latest",
    "gemini-pro-latest",
]


class AIConfigUpdate(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    fast_model: str | None = None
    model_priority_queue: list[str] | None = None
    enable_priority_fallback: bool | None = None
    task_routing_enabled: bool | None = None
    ai_enabled: bool | None = None
    plain_rag_enabled: bool | None = None
    agentic_rag_enabled: bool | None = None


class LLMTestRequest(BaseModel):
    prompt: str = Field(default="Explain how AI works in a few words")


@router.get("/admin/ai-config")
async def get_ai_config(admin_user: dict = Depends(require_roles("admin"))) -> dict[str, Any]:
    manager = AIConfigManager()
    return {
        **manager.to_dict(include_key=False),
        "available_models": AVAILABLE_MODELS,
    }


@router.post("/admin/ai-config")
async def update_ai_config(
    request: AIConfigUpdate,
    admin_user: dict = Depends(require_roles("admin")),
) -> dict[str, Any]:
    manager = AIConfigManager()
    updates = {
        k: v for k, v in request.model_dump().items() if v is not None or isinstance(v, bool)
    }
    if "gemini_api_key" in updates and not updates["gemini_api_key"]:
        # Empty string means keep current key; never overwrite with empty to avoid accidental wipe
        del updates["gemini_api_key"]
    if "gemini_model" in updates:
        val = str(updates["gemini_model"]).strip()
        if not val:
            raise HTTPException(status_code=400, detail="Model name cannot be empty")
        updates["gemini_model"] = val
    if "fast_model" in updates:
        val = str(updates["fast_model"]).strip()
        if not val:
            raise HTTPException(status_code=400, detail="Fast model name cannot be empty")
        updates["fast_model"] = val
    manager.update(**updates)
    return {
        **manager.to_dict(include_key=False),
        "available_models": AVAILABLE_MODELS,
    }


@router.get("/admin/ai-usage")
async def get_ai_usage(admin_user: dict = Depends(require_roles("admin"))) -> dict[str, Any]:
    ledger = get_ledger()
    return {
        "usage": ledger.summary(),
        "failures": ledger.failures_summary(limit=50),
        "recent_records": [
            {
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.cost_usd,
                "correlation_id": r.correlation_id,
            }
            for r in ledger.records[-50:]
        ],
    }


@router.post("/admin/ai-test")
async def test_ai(
    request: LLMTestRequest,
    admin_user: dict = Depends(require_roles("admin")),
) -> dict[str, Any]:
    from copilot.infrastructure.db.session import async_session_factory
    from copilot.infrastructure.di import Container

    manager = AIConfigManager()
    if not manager.config.ai_enabled:
        return {"ok": False, "error": "AI is disabled", "model": manager.config.gemini_model}

    async with async_session_factory() as session:
        container = Container.from_session(session)
        correlation_id = get_correlation_id()
        try:
            response = await container.llm.generate(
                prompt=request.prompt,
                system_instruction=None,
                temperature=0.0,
                max_tokens=256,
                correlation_id=correlation_id,
            )
            meta = response.metadata or {}
            if response.model == "degraded" or meta.get("degraded"):
                last_err = (
                    meta.get("last_error") or "LLM generation failed and degraded to offline mode"
                )
                return {
                    "ok": False,
                    "model": manager.config.gemini_model,
                    "provider": "offline-fallback",
                    "error": f"Model '{manager.config.gemini_model}' failed: {last_err}",
                    "cost_usd": 0.0,
                }
            ledger = get_ledger()
            ledger.record(
                TokenCostRecord(
                    provider=meta.get("provider", "unknown"),
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_usd=response.cost_usd,
                    correlation_id=correlation_id,
                    metadata=meta,
                )
            )
            return {
                "ok": True,
                "model": response.model,
                "requested_model": manager.config.gemini_model,
                "provider": meta.get("provider", "unknown"),
                "cascaded": meta.get("cascaded", False),
                "cascaded_from": meta.get("cascaded_from"),
                "text": response.text[:500],
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
        except Exception as exc:
            ledger = get_ledger()
            ledger.record_failure(
                FailureRecord(
                    provider="fallback-chain",
                    model=manager.config.gemini_model,
                    error=str(exc),
                    correlation_id=correlation_id,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
            return {"ok": False, "error": str(exc), "model": manager.config.gemini_model}
