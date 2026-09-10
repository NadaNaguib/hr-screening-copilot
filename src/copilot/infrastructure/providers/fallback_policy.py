"""LLM fallback policy with intelligent priority queue cascade and task-tier routing."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from copilot.application.ports.llm_port import LLMPort, LLMResponse
from copilot.infrastructure.providers.tiered_router import TaskTier

logger = logging.getLogger(__name__)


class FallbackLLMProvider(LLMPort):
    """Wraps dynamic multi-model cascade and retry/backoff policy."""

    def __init__(
        self,
        adapters: list[LLMPort] | None = None,
        max_retries: int = 1,
        base_delay: float = 0.5,
        tier: TaskTier = TaskTier.REASONING,
    ) -> None:
        self.adapters = adapters or []
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.tier = tier

    def name(self) -> str:
        return f"fallback-chain-{self.tier.value}"

    def for_tier(self, tier: TaskTier) -> FallbackLLMProvider:
        """Return a provider instance targeted at a specific task tier."""
        return FallbackLLMProvider(
            adapters=self.adapters,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            tier=tier,
        )

    def add_adapter(self, adapter: LLMPort) -> None:
        self.adapters.append(adapter)

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> LLMResponse:
        from copilot.infrastructure.config.ai_config import AIConfigManager
        from copilot.infrastructure.observability.token_cost import FailureRecord, TokenCostRecord, get_ledger
        from copilot.infrastructure.providers.gemini_rest_adapter import GeminiRestAdapter

        ai_config = AIConfigManager().config
        if not ai_config.ai_enabled:
            return LLMResponse(
                text="",
                model="ai-disabled",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                metadata={"correlation_id": correlation_id, "disabled": True},
            )

        # 1. Determine preferred model based on task tier
        if self.tier == TaskTier.FAST and ai_config.task_routing_enabled:
            preferred_model = ai_config.fast_model or "gemini-3.1-flash-lite"
        else:
            preferred_model = ai_config.gemini_model or "gemini-2.5-flash"

        # 2. Build ordered cascade queue
        cascade_models: list[str] = [preferred_model]
        if ai_config.enable_priority_fallback and ai_config.model_priority_queue:
            for m in ai_config.model_priority_queue:
                if m and m not in cascade_models:
                    cascade_models.append(m)

        last_error: Exception | None = None

        # 3. If explicit adapters were passed in (e.g. in test fixtures), prioritize them
        if self.adapters:
            for adapter in self.adapters:
                for attempt in range(self.max_retries + 1):
                    try:
                        response = await adapter.generate(
                            prompt,
                            system_instruction=system_instruction,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            correlation_id=correlation_id,
                        )
                        ledger = get_ledger()
                        meta = response.metadata or {}
                        ledger.record(
                            TokenCostRecord(
                                provider=meta.get("provider", adapter.name()),
                                model=response.model,
                                input_tokens=response.input_tokens,
                                output_tokens=response.output_tokens,
                                cost_usd=response.cost_usd,
                                correlation_id=correlation_id,
                                metadata=meta,
                            )
                        )
                        return response
                    except Exception as exc:
                        last_error = exc
                        err_str = str(exc).lower()
                        if "429" in err_str or "resourceexhausted" in err_str or "quota" in err_str:
                            break
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.base_delay * (2**attempt))

        # 4. Cascade through priority queue of models
        for model_idx, model_name in enumerate(cascade_models):
            for attempt in range(self.max_retries + 1):
                try:
                    adapter = GeminiRestAdapter(model=model_name, api_key=ai_config.gemini_api_key)
                    response = await adapter.generate(
                        prompt,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        correlation_id=correlation_id,
                    )
                    # Successful generation
                    meta = response.metadata or {}
                    if model_name != preferred_model:
                        meta["cascaded"] = True
                        meta["cascaded_from"] = preferred_model
                        meta["cascade_depth"] = model_idx
                        logger.info(
                            "[PriorityQueueCascade] Successfully answered via fallback model '%s' (cascaded from '%s')",
                            model_name,
                            preferred_model,
                        )

                    ledger = get_ledger()
                    ledger.record(
                        TokenCostRecord(
                            provider=meta.get("provider", "gemini-rest"),
                            model=response.model,
                            input_tokens=response.input_tokens,
                            output_tokens=response.output_tokens,
                            cost_usd=response.cost_usd,
                            correlation_id=correlation_id,
                            metadata=meta,
                        )
                    )
                    return response

                except Exception as exc:
                    last_error = exc
                    err_str = str(exc).lower()
                    # If quota, rate limit (429), not found (404), or overloaded (503): immediately cascade
                    is_rate_limit = (
                        "429" in err_str
                        or "resourceexhausted" in err_str
                        or "quota" in err_str
                        or "rate_limit" in err_str
                    )
                    is_unavailable = "404" in err_str or "not found" in err_str or "503" in err_str

                    if is_rate_limit or is_unavailable:
                        next_model = (
                            cascade_models[model_idx + 1] if model_idx + 1 < len(cascade_models) else None
                        )
                        logger.warning(
                            "[PriorityQueueCascade] Model '%s' encountered limit/error (%s). "
                            "Cascading to next priority model: %s",
                            model_name,
                            exc,
                            next_model or "None (exhausted cascade)",
                        )
                        break  # Break retry loop and move immediately to next model in cascade

                    if attempt < self.max_retries:
                        await asyncio.sleep(self.base_delay * (2**attempt))

        # 5. Graceful degrade if all cascade models fail
        get_ledger().record_failure(
            FailureRecord(
                provider="priority-cascade",
                model=preferred_model,
                error=str(last_error) if last_error else "unknown",
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return LLMResponse(
            text="",
            model="degraded",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            metadata={
                "correlation_id": correlation_id,
                "degraded": True,
                "last_error": str(last_error) if last_error else None,
                "tried_models": cascade_models,
            },
        )

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> AsyncIterator[LLMResponse]:
        response = await self.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            correlation_id=correlation_id,
        )
        yield response


def build_llm_provider(tier: TaskTier = TaskTier.REASONING) -> FallbackLLMProvider:
    """Factory that creates the configured fallback chain with priority cascade."""
    return FallbackLLMProvider(
        adapters=None,
        max_retries=1,
        base_delay=0.5,
        tier=tier,
    )
