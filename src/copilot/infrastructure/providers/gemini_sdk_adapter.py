"""Gemini SDK-based LLM adapter."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from copilot.application.ports.llm_port import LLMPort, LLMResponse


class GeminiSdkAdapter(LLMPort):
    """Primary LLM adapter using google-generativeai."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self._client: Any | None = None

    def _ensure_config(self) -> None:
        from copilot.infrastructure.config.ai_config import AIConfigManager

        manager = AIConfigManager()
        if self.model is None:
            self.model = manager.config.gemini_model
        if self.api_key is None:
            self.api_key = manager.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    def name(self) -> str:
        return "gemini-sdk"

    def _client_ready(self) -> bool:
        self._ensure_config()
        if not self.api_key:
            return False
        try:
            import google.generativeai as genai

            if self._client is None:
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            return True
        except Exception:
            return False
        try:
            import google.generativeai as genai

            if self._client is None:
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            return True
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> LLMResponse:
        if not self._client_ready():
            return self._stub(prompt)
        try:
            import google.generativeai as genai

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            response = await self._client.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings={
                    "HARASSMENT": "BLOCK_NONE",
                    "HATE": "BLOCK_NONE",
                    "SEXUAL": "BLOCK_NONE",
                    "DANGEROUS": "BLOCK_NONE",
                },
            )
            text = response.text or ""
            usage = response.usage_metadata
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            cost = _estimate_cost(input_tokens, output_tokens)
            return LLMResponse(
                text=text,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                metadata={"correlation_id": correlation_id, "provider": self.name()},
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini SDK error: {exc}") from exc

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> AsyncIterator[LLMResponse]:
        if not self._client_ready():
            yield self._stub(prompt)
            return
        try:
            import google.generativeai as genai

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            response = await self._client.generate_content_async(
                prompt,
                generation_config=generation_config,
                stream=True,
                safety_settings={
                    "HARASSMENT": "BLOCK_NONE",
                    "HATE": "BLOCK_NONE",
                    "SEXUAL": "BLOCK_NONE",
                    "DANGEROUS": "BLOCK_NONE",
                },
            )
            async for chunk in response:
                text = chunk.text or ""
                if text:
                    yield LLMResponse(
                        text=text,
                        model=self.model,
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                        metadata={"correlation_id": correlation_id, "provider": self.name()},
                    )
        except Exception as exc:
            raise RuntimeError(f"Gemini SDK stream error: {exc}") from exc

    def _stub(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            text=f"[stub] Gemini SDK would answer: {prompt[:80]}...",
            model=self.model,
            input_tokens=len(prompt.split()),
            output_tokens=20,
            cost_usd=0.0,
            metadata={"provider": self.name(), "stub": True},
        )


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    # Approximate Gemini Flash pricing: $0.35 / 1M input, $1.05 / 1M output
    return input_tokens * 0.35e-6 + output_tokens * 1.05e-6
