"""Tests that SIMULATE_AGENT_FAILURE forces degradation across Chat and Screening."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

import copilot.agents.orchestrator as orch
import copilot.application.use_cases.ask_copilot as ask_mod
from copilot.agents.orchestrator import LangGraphOrchestrator
from copilot.application.ports.llm_port import LLMPort, LLMResponse
from copilot.infrastructure.config.settings import get_settings

_ANSWER = "Alice Johnson knows Python, FastAPI, PostgreSQL and Docker very well."


class _StubLLM(LLMPort):
    """Deterministic LLM stub (no network)."""

    def __init__(self, text: str = _ANSWER) -> None:
        self.text = text

    def name(self) -> str:
        return "stub"

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> LLMResponse:
        return LLMResponse(text=self.text, model="stub", metadata={"provider": "stub"})

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> AsyncIterator[LLMResponse]:
        yield await self.generate(prompt, correlation_id=correlation_id)


@dataclass
class _Evidence:
    id: Any = field(default_factory=uuid4)
    quote: str = "Alice Johnson built FastAPI microservices."
    source_document: str = "Alice_Johnson_CV.pdf"
    page_number: int = 1
    source_chunk_id: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class _FakeHybridSearch:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: str, job_id: Any = None, top_k: int = 5) -> list[_Evidence]:
        self.calls += 1
        return [_Evidence()]


def _container() -> SimpleNamespace:
    return SimpleNamespace(
        session=None,
        embedding=None,
        llm=_StubLLM(),
        hybrid_search=_FakeHybridSearch(),
    )


QUESTION = "What Python frameworks does Alice Johnson know?"


@pytest.fixture(autouse=True)
def _no_stream_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ask_mod, "STREAM_TOKEN_DELAY_SECONDS", 0)
    monkeypatch.setattr(orch, "STREAM_TOKEN_DELAY_SECONDS", 0)


# ─── Chat AI (ask_copilot) ───────────────────────────────────────────────────


async def test_chat_degrades_when_simulate_agent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "simulate_agent_failure", True)
    container = _container()

    events = [event async for event in ask_mod.ask_copilot(container, QUESTION)]

    # An explicit degradation status event leads the stream …
    assert events[0]["type"] == "agent_event"
    assert events[0]["data"]["status"] == "degraded"
    assert events[0]["data"]["reason"] == "simulate_agent_failure"

    # … and the answer is streamed token-by-token (FR-6).
    chunks = [event for event in events if event["type"] == "answer_chunk"]
    assert len(chunks) > 1
    assert "".join(event["data"] for event in chunks) == _ANSWER

    # Plain RAG retrieval WAS used, and the run is flagged as degraded.
    assert container.hybrid_search.calls == 1
    done = events[-1]
    assert done["type"] == "done"
    assert done["data"]["degraded"] is True
    assert done["data"]["mode"] == "plain_rag"

    # No agentic agents ran — only the orchestrator degrade marker.
    agent_names = [event["data"]["agent"] for event in events if event["type"] == "agent_event"]
    assert agent_names == ["orchestrator"]


async def test_chat_runs_agentic_when_not_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "simulate_agent_failure", False)
    container = _container()

    events = [event async for event in ask_mod.ask_copilot(container, QUESTION)]

    done = events[-1]
    assert done["data"]["degraded"] is False
    assert done["data"]["mode"] == "agentic"

    # Live agent progress events are emitted by the graph nodes.
    agent_names = [event["data"]["agent"] for event in events if event["type"] == "agent_event"]
    assert "agentic_planner" in agent_names

    chunks = [event for event in events if event["type"] == "answer_chunk"]
    assert len(chunks) > 1
    assert "".join(event["data"] for event in chunks) == _ANSWER


# ─── Screening pipeline (run_screening) ──────────────────────────────────────


async def test_screening_degrades_when_simulate_agent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "simulate_agent_failure", True)
    orchestrator = LangGraphOrchestrator(_StubLLM())

    events = [
        event
        async for event in orchestrator.run_screening(
            candidate_id=uuid4(), job_id=None, rubric_id=None
        )
    ]

    agent_events = [event for event in events if event["type"] == "agent_event"]
    assert len(agent_events) == 1
    assert agent_events[0]["data"] == {"agent": "orchestrator", "status": "degraded"}

    result = next(event for event in events if event["type"] == "result")
    assert result["data"]["degraded"] is True
    assert result["data"]["mode"] == "plain_rag"


async def test_screening_runs_agents_when_not_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "simulate_agent_failure", False)
    orchestrator = LangGraphOrchestrator(_StubLLM())

    events = [
        event
        async for event in orchestrator.run_screening(
            candidate_id=uuid4(), job_id=None, rubric_id=None
        )
    ]

    agent_names = [event["data"]["agent"] for event in events if event["type"] == "agent_event"]
    assert agent_names == [
        "evidence_extractor",
        "bias_guard",
        "rubric_scorer",
        "shortlist_drafter",
    ]
    result = next(event for event in events if event["type"] == "result")
    assert result["data"]["degraded"] is False
    assert result["data"]["mode"] == "agentic"
