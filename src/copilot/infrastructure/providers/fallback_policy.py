"""LLM fallback policy: primary -> secondary -> graceful degrade."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from copilot.application.ports.llm_port import LLMPort, LLMResponse


class FallbackLLMProvider(LLMPort):
    """Wraps a chain of LLM adapters with retry/backoff."""

    def __init__(
        self,
        adapters: list[LLMPort] | None = None,
        max_retries: int = 2,
        base_delay: float = 1.0,
    ) -> None:
        self.adapters = adapters or []
        self.max_retries = max_retries
        self.base_delay = base_delay

    def name(self) -> str:
        return "fallback-chain"

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
        last_error: Exception | None = None
        for adapter in self.adapters:
            for attempt in range(self.max_retries + 1):
                try:
                    return await adapter.generate(
                        prompt,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        correlation_id=correlation_id,
                    )
                except Exception as exc:
                    last_error = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.base_delay * (2**attempt))
        # Graceful degrade: return a stub response instead of raising.
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


def build_llm_provider() -> LLMPort:
    """Factory that creates the configured fallback chain."""
    from copilot.infrastructure.providers.gemini_rest_adapter import GeminiRestAdapter
    from copilot.infrastructure.providers.gemini_sdk_adapter import GeminiSdkAdapter

    return FallbackLLMProvider(
        adapters=[GeminiSdkAdapter(), GeminiRestAdapter()],
        max_retries=2,
        base_delay=1.0,
    )
