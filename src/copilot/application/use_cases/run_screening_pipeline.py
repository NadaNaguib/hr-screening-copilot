"""Run the agentic screening pipeline for a candidate."""
from __future__ import annotations

from uuid import UUID

from copilot.agents.bias_guard import BiasGuard
from copilot.agents.evidence_extractor import extract_evidence
from copilot.agents.orchestrator import LangGraphOrchestrator
from copilot.agents.rubric_scorer import RubricScorer
from copilot.domain.errors import NotFoundError
from copilot.domain.rubric_score import RubricScore
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def run_screening_pipeline(
    container: Container,
    candidate_id: UUID,
    correlation_id: str = "",
) -> dict:
    correlation_id = correlation_id or get_correlation_id()
    candidate = await container.candidate_repository.get_candidate(candidate_id)
    if candidate is None:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    candidate.mark_processing()
    await container.candidate_repository.update_candidate(candidate)

    rubric = await container.document_repository.get_rubric_for_job(candidate.job_id) if candidate.job_id else None

    # Agentic flow
    bias_guard = BiasGuard()
    redacted_text, findings = bias_guard.redact(candidate)
    await container.audit.log(
        action="bias_guard",
        target_type="candidate",
        target_id=str(candidate.id),
        actor_id=None,
        actor_role=None,
        details={"findings_count": len(findings)},
        correlation_id=correlation_id,
    )

    evidence = extract_evidence(candidate, rubric)
    await container.candidate_repository.add_evidence(candidate.id, evidence)

    scores: list[RubricScore] = []
    if rubric:
        scorer = RubricScorer()
        scores = scorer.score(candidate, rubric, evidence)
        await container.candidate_repository.add_scores(candidate.id, scores)

    overall = sum(s.score for s in scores) / max(len(scores), 1) if scores else 0.0
    candidate.mark_screened(overall)
    await container.candidate_repository.update_candidate(candidate)

    # Orchestrator event stream (consume for side effects)
    orchestrator = LangGraphOrchestrator(container.llm)
    events = []
    async for event in orchestrator.run_screening(
        candidate_id=candidate.id,
        job_id=candidate.job_id,
        rubric_id=rubric.id if rubric else None,
        correlation_id=correlation_id,
    ):
        events.append(event)

    await container.audit.log(
        action="run_screening_pipeline",
        target_type="candidate",
        target_id=str(candidate.id),
        actor_id=None,
        actor_role=None,
        details={"overall_score": overall, "evidence_count": len(evidence), "score_count": len(scores)},
        correlation_id=correlation_id,
    )
    return {
        "candidate_id": str(candidate.id),
        "status": candidate.status.value,
        "overall_score": overall,
        "evidence_count": len(evidence),
        "score_count": len(scores),
        "bias_findings": len(findings),
        "events": events,
    }
