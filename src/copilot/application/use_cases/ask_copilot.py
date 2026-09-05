"""Ask the copilot a question using retrieval-augmented generation."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from copilot.agents.orchestrator import LangGraphOrchestrator
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def ask_copilot(
    container: Container,
    question: str,
    job_id: UUID | None = None,
    correlation_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    correlation_id = correlation_id or get_correlation_id()

    # Retrieve evidence
    evidence = await container.hybrid_search.search(question, job_id=job_id, top_k=5)
    context = "\n\n".join(
        f"[{i+1}] {e.quote} (source: {e.source_document}, page: {e.page_number})"
        for i, e in enumerate(evidence)
    )
    prompt = (
        "You are a helpful HR screening assistant. Use only the retrieved context below.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely and cite sources using [1], [2], etc."
    )

    orchestrator = LangGraphOrchestrator(container.llm)
    async for event in orchestrator.ask(prompt, job_id=job_id, correlation_id=correlation_id):
        if event["type"] == "chunk":
            yield {
                "type": "answer_chunk",
                "data": event["data"],
                "citations": [
                    {"quote": e.quote, "source": e.source_document, "page": e.page_number}
                    for e in evidence
                ],
            }
        elif event["type"] == "done":
            yield {"type": "done", "data": event["data"]}
