"""Gemini REST-based LLM adapter."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from copilot.application.ports.llm_port import LLMPort, LLMResponse


class GeminiRestAdapter(LLMPort):
    """Fallback LLM adapter using direct Gemini REST API."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key

    def _ensure_config(self) -> None:
        from copilot.infrastructure.config.ai_config import AIConfigManager

        manager = AIConfigManager()
        if self.model is None:
            self.model = manager.config.gemini_model
        if self.api_key is None:
            self.api_key = manager.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    def name(self) -> str:
        return "gemini-rest"

    def _url(self) -> str:
        self._ensure_config()
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _payload(
        self, prompt: str, system_instruction: str | None, temperature: float, max_tokens: int
    ) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [{"text": prompt}]
        system_part = {"parts": [{"text": system_instruction or ""}]}
        return {
            "contents": [{"role": "user", "parts": parts}],
            "systemInstruction": system_part,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> LLMResponse:
        self._ensure_config()
        if not self.api_key:
            return self._stub(prompt)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._url(),
                headers=self._headers(),
                params={"key": self.api_key},
                json=self._payload(prompt, system_instruction, temperature, max_tokens),
            )
            response.raise_for_status()
            data = response.json()
            text = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = " ".join(p.get("text", "") for p in parts)
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            return LLMResponse(
                text=text,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=_estimate_cost(input_tokens, output_tokens),
                metadata={"correlation_id": correlation_id, "provider": self.name()},
            )

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> AsyncIterator[LLMResponse]:
        # REST fallback does not stream easily; yield single chunk.
        response = await self.generate(
            prompt, system_instruction, temperature, max_tokens, correlation_id
        )
        yield response

    def _stub(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            text=f"[stub] Gemini REST would answer: {prompt[:80]}...",
            model=self.model,
            input_tokens=len(prompt.split()),
            output_tokens=20,
            cost_usd=0.0,
            metadata={"provider": self.name(), "stub": True},
        )


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens * 0.35e-6 + output_tokens * 1.05e-6
