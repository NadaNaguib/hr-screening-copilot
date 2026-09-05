"""LangGraph-based orchestrator behind OrchestratorPort."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from copilot.application.ports.llm_port import LLMPort
from copilot.application.ports.orchestrator_port import OrchestratorPort
from copilot.infrastructure.config.settings import get_settings
from copilot.infrastructure.observability.token_cost import TokenCostRecord, get_ledger


class _OrchestratorState(dict):
    """Typed graph state."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []
        self.degraded = False


def _build_graph():
    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"LangGraph not available: {exc}") from exc

    def extract_node(state: _OrchestratorState) -> _OrchestratorState:
        state.events.append({"agent": "evidence_extractor", "status": "done"})
        return state

    def bias_node(state: _OrchestratorState) -> _OrchestratorState:
        state.events.append({"agent": "bias_guard", "status": "done"})
        return state

    def score_node(state: _OrchestratorState) -> _OrchestratorState:
        state.events.append({"agent": "rubric_scorer", "status": "done"})
        return state

    def draft_node(state: _OrchestratorState) -> _OrchestratorState:
        state.events.append({"agent": "shortlist_drafter", "status": "done"})
        return state

    def degrade_node(state: _OrchestratorState) -> _OrchestratorState:
        state.degraded = True
        state.events.append({"agent": "orchestrator", "status": "degraded"})
        return state

    def route(state: _OrchestratorState) -> str:
        if state.degraded:
            return "degrade"
        return "extract"

    builder = StateGraph(_OrchestratorState)
    builder.add_node("extract", extract_node)
    builder.add_node("bias", bias_node)
    builder.add_node("score", score_node)
    builder.add_node("draft", draft_node)
    builder.add_node("degrade", degrade_node)
    builder.set_conditional_entry_point(route, {"extract": "extract", "degrade": "degrade"})
    builder.add_edge("extract", "bias")
    builder.add_edge("bias", "score")
    builder.add_edge("score", "draft")
    builder.add_edge("draft", END)
    builder.add_edge("degrade", END)
    return builder.compile()


class LangGraphOrchestrator(OrchestratorPort):
    """Agentic orchestrator using a LangGraph graph."""

    def __init__(self, llm: LLMPort) -> None:
        self.llm = llm
        self.graph = _build_graph()

    async def run_screening(
        self,
        candidate_id: UUID,
        job_id: UUID | None,
        rubric_id: UUID | None,
        correlation_id: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        settings = get_settings()
        degraded = settings.simulate_agent_failure
        state = _OrchestratorState()
        if degraded:
            state.degraded = True

        # Run graph (synchronous compile; nodes are sync)
        final_state = self.graph.invoke(state)

        for event in final_state.events:
            yield {"type": "agent_event", "data": event}

        # Generate a summary justification via LLM
        prompt = f"Summarize why candidate {candidate_id} fits job {job_id}."
        response = await self.llm.generate(prompt, correlation_id=correlation_id)
        get_ledger().record(
            TokenCostRecord(
                provider=response.metadata.get("provider", "unknown"),
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                correlation_id=correlation_id,
                metadata=response.metadata,
            )
        )
        yield {
            "type": "result",
            "data": {
                "candidate_id": str(candidate_id),
                "job_id": str(job_id) if job_id else None,
                "degraded": final_state.degraded,
                "justification": response.text,
            },
        }

    async def ask(
        self,
        question: str,
        job_id: UUID | None = None,
        correlation_id: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        response = await self.llm.generate(question, correlation_id=correlation_id)
        get_ledger().record(
            TokenCostRecord(
                provider=response.metadata.get("provider", "unknown"),
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                correlation_id=correlation_id,
                metadata=response.metadata,
            )
        )
        yield {"type": "chunk", "data": response.text}
        yield {
            "type": "done",
            "data": {
                "citations": [],
                "degraded": False,
            },
        }
