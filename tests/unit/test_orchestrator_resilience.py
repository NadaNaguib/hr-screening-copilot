"""Unit tests for orchestrator resiliency controls (FR-5) and token streaming (FR-6)."""

from __future__ import annotations

import asyncio

import pytest

import copilot.agents.orchestrator as orch
from copilot.domain.errors import OrchestratorError


async def test_guard_step_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orch, "STEP_TIMEOUT_SECONDS", 0.01)

    async def _slow(state: dict) -> dict:
        await asyncio.sleep(1.0)
        return {}

    guarded = orch._guard_step("slow", _slow)
    with pytest.raises(OrchestratorError, match="per-step timeout"):
        await guarded({"iteration_count": 0})


async def test_guard_step_enforces_max_iterations() -> None:
    async def _ok(state: dict) -> dict:
        return {}

    guarded = orch._guard_step("ok", _ok)
    with pytest.raises(OrchestratorError, match="Max iterations"):
        await guarded({"iteration_count": orch.MAX_ITERATIONS})


async def test_guard_step_increments_iteration_count() -> None:
    async def _ok(state: dict) -> dict:
        return {"answer": "hi"}

    guarded = orch._guard_step("ok", _ok)
    result = await guarded({"iteration_count": 2})
    assert result["iteration_count"] == 3
    assert result["answer"] == "hi"


async def test_max_iterations_constant_is_bounded() -> None:
    assert orch.MAX_ITERATIONS == 10
    assert orch.STEP_TIMEOUT_SECONDS == 30.0


async def test_stream_tokens_splits_word_by_word(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orch, "STREAM_TOKEN_DELAY_SECONDS", 0)
    tokens = [token async for token in orch._stream_tokens("Hello brave world.")]
    assert tokens == ["Hello ", "brave ", "world."]


async def test_stream_tokens_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orch, "STREAM_TOKEN_DELAY_SECONDS", 0)
    assert [token async for token in orch._stream_tokens("")] == []
