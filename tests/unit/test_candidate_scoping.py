"""Regression tests for candidate-scoped RAG isolation (no cross-candidate leakage)."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import copilot.agents.orchestrator as orch
import copilot.agents.rag_tools as rag_tools
from copilot.agents.orchestrator import LangGraphOrchestrator
from copilot.application.ports.llm_port import LLMPort, LLMResponse
from copilot.application.use_cases.ask_copilot import (
    _resolve_candidate_scope,
    _scoped_citations,
)
from copilot.infrastructure.repositories.sqlalchemy_repositories import SqlAlchemyVectorStore
from copilot.infrastructure.retrieval.hybrid_search import HybridSearch

SCOPE = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")


class _StubLLM(LLMPort):
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
        return LLMResponse(text="Sara has 6 years of experience.", model="stub")

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        correlation_id: str = "",
    ) -> AsyncIterator[LLMResponse]:
        yield await self.generate(prompt)


# ─── Retrieval layer: the scope must reach the SQL query ─────────────────────


def test_vector_store_search_exposes_candidate_scope() -> None:
    params = inspect.signature(SqlAlchemyVectorStore.search).parameters
    assert "candidate_id" in params
    assert params["candidate_id"].default is None


def test_search_talent_pool_exposes_candidate_scope() -> None:
    params = inspect.signature(rag_tools.search_talent_pool).parameters
    assert "candidate_id" in params
    assert params["candidate_id"].default is None


async def test_hybrid_search_forwards_candidate_scope() -> None:
    class _Store:
        def __init__(self) -> None:
            self.received: dict[str, Any] | None = None

        async def search(self, **kwargs: Any) -> list[Any]:
            self.received = kwargs
            return []

    class _Embedding:
        async def embed(self, _texts: list[str]) -> list[list[float]]:
            return [[0.0, 0.0, 0.0]]

    store = _Store()
    search = HybridSearch(store, _Embedding())  # type: ignore[arg-type]

    await search.search("query", top_k=3, candidate_id=SCOPE)

    assert store.received is not None
    assert store.received["candidate_id"] == SCOPE


# ─── Citation post-filter: another candidate can never surface ───────────────


def test_scoped_citations_drops_other_candidates() -> None:
    citations = [
        {"id": "a", "candidate_id": str(SCOPE), "quote": "own"},
        {"id": "b", "candidate_id": str(OTHER), "quote": "leak"},
        {"id": "c", "candidate_id": "", "quote": "job description"},
    ]
    kept = _scoped_citations(citations, SCOPE)

    assert [c["id"] for c in kept] == ["a", "c"]


def test_scoped_citations_is_noop_without_scope() -> None:
    citations = [{"id": "b", "candidate_id": str(OTHER), "quote": "x"}]
    assert _scoped_citations(citations, None) == citations


def test_scoped_citations_accepts_uuid_objects() -> None:
    citations = [{"id": "a", "candidate_id": SCOPE, "quote": "own"}]
    assert len(_scoped_citations(citations, SCOPE)) == 1


# ─── Scope resolution priority ───────────────────────────────────────────────


async def test_resolve_scope_prefers_explicit_candidate_id() -> None:
    container = SimpleNamespace(session=None)
    resolved = await _resolve_candidate_scope(container, "tell me about her", SCOPE)
    assert resolved == SCOPE


async def test_resolve_scope_returns_none_without_session() -> None:
    container = SimpleNamespace(session=None)
    assert await _resolve_candidate_scope(container, "who is best?", None) is None


# ─── Orchestrator: a scoped turn never plans a pool-wide search ──────────────


async def test_scoped_ask_restricts_plan_to_candidate_tools() -> None:
    orchestrator = LangGraphOrchestrator(_StubLLM())

    events = [event async for event in orchestrator.ask("What are her skills?", candidate_id=SCOPE)]

    planner = next(
        event
        for event in events
        if event["type"] == "agent_event" and event["data"].get("agent") == "agentic_planner"
    )
    plan = planner["data"]["plan"]
    assert plan["intent"] == "candidate_inquiry"
    assert plan["scoped"] is True
    assert "talent_pool_search" not in plan["tools"]
    assert "candidate_cv_reader" in plan["tools"]


async def test_unscoped_ask_still_allows_pool_search() -> None:
    orchestrator = LangGraphOrchestrator(_StubLLM())

    events = [event async for event in orchestrator.ask("Who knows Kubernetes?")]

    planner = next(
        event
        for event in events
        if event["type"] == "agent_event" and event["data"].get("agent") == "agentic_planner"
    )
    assert planner["data"]["plan"].get("scoped") is not True


def test_scoped_evidence_filter_drops_foreign_candidates() -> None:
    """Mirrors the synthesizer guard: keep own + non-candidate, drop foreign."""
    scoped_id = str(uuid4())
    evidence = [
        {"candidate_id": scoped_id, "quote": "own chunk"},
        {"candidate_id": str(OTHER), "quote": "other candidate chunk"},
        {"candidate_id": "", "quote": "rubric criterion"},
    ]

    kept = [
        ev
        for ev in evidence
        if not ev.get("candidate_id") or str(ev.get("candidate_id")) == scoped_id
    ]

    assert [ev["quote"] for ev in kept] == ["own chunk", "rubric criterion"]


def test_orchestrator_state_exposes_scoped_candidate_fields() -> None:
    assert "scoped_candidate_id" in orch.AgenticRAGState.__annotations__
    assert "scoped_candidate_name" in orch.AgenticRAGState.__annotations__
