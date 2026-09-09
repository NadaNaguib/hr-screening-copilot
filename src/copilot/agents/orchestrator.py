"""LangGraph-based orchestrator behind OrchestratorPort."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, TypedDict
from uuid import UUID

from copilot.application.ports.llm_port import LLMPort
from copilot.application.ports.orchestrator_port import OrchestratorPort
from copilot.infrastructure.config.settings import get_settings
from copilot.infrastructure.observability.token_cost import TokenCostRecord, get_ledger


class OrchestratorGraphState(TypedDict, total=False):
    events: list[dict[str, Any]]
    degraded: bool


_OrchestratorState = OrchestratorGraphState


def _build_graph():
    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"LangGraph not available: {exc}") from exc

    def extract_node(state: OrchestratorGraphState) -> dict[str, Any]:
        events = list(state.get("events") or [])
        events.append({"agent": "evidence_extractor", "status": "done"})
        return {"events": events}

    def bias_node(state: OrchestratorGraphState) -> dict[str, Any]:
        events = list(state.get("events") or [])
        events.append({"agent": "bias_guard", "status": "done"})
        return {"events": events}

    def score_node(state: OrchestratorGraphState) -> dict[str, Any]:
        events = list(state.get("events") or [])
        events.append({"agent": "rubric_scorer", "status": "done"})
        return {"events": events}

    def draft_node(state: OrchestratorGraphState) -> dict[str, Any]:
        events = list(state.get("events") or [])
        events.append({"agent": "shortlist_drafter", "status": "done"})
        return {"events": events}

    def degrade_node(state: OrchestratorGraphState) -> dict[str, Any]:
        events = list(state.get("events") or [])
        events.append({"agent": "orchestrator", "status": "degraded"})
        return {"degraded": True, "events": events}

    def route(state: OrchestratorGraphState) -> str:
        if state.get("degraded", False):
            return "degrade"
        return "extract"

    builder = StateGraph(OrchestratorGraphState)
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
        state: OrchestratorGraphState = {"events": [], "degraded": degraded}

        # Run graph (synchronous compile; nodes are sync)
        final_state = self.graph.invoke(state)

        events: list[dict[str, Any]] = final_state.get("events", []) if isinstance(final_state, dict) else getattr(final_state, "events", [])
        is_degraded: bool = final_state.get("degraded", False) if isinstance(final_state, dict) else getattr(final_state, "degraded", False)

        for event in events:
            yield {"type": "agent_event", "data": event}

        # Generate a summary justification via LLM
        prompt = f"Summarize why candidate {candidate_id} fits job {job_id}."
        response = await self.llm.generate(prompt, correlation_id=correlation_id)
        meta = response.metadata or {}
        get_ledger().record(
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
        yield {
            "type": "result",
            "data": {
                "candidate_id": str(candidate_id),
                "job_id": str(job_id) if job_id else None,
                "degraded": is_degraded,
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
        meta = response.metadata or {}
        get_ledger().record(
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
        yield {"type": "chunk", "data": response.text}
        yield {
            "type": "done",
            "data": {
                "citations": [],
                "degraded": False,
            },
        }
