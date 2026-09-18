"""Interview question generator with gated tool exposure.

Role:
    Generates tailored, evidence-grounded interview questions and probes based on
    candidate skill gaps and rubric evaluations.

The generated probes are written directly onto the candidate's Review Task so
reviewers can view/edit/regenerate them inline (see Design Decision 5.5) without
modals or a separate shortlist entity. Approval/export remain gated externally via
the review-task state machine.
"""

from __future__ import annotations

from typing import Any

from copilot.domain.candidate import Candidate
from copilot.domain.job import Job
from copilot.domain.rubric_score import RubricScore


class InterviewQuestionGenerator:
    """Tailor interview questions and probes for a candidate; finalize is gated externally."""

    def __init__(self, llm: Any = None, correlation_id: str = "") -> None:
        self._llm = llm
        self._correlation_id = correlation_id

    async def generate(
        self,
        candidate: Candidate,
        job: Job | None = None,
        scores: list[RubricScore] | None = None,
    ) -> list[dict[str, Any]]:
        """Return 3-5 tailored, evidence-grounded interview probes for ``candidate``.

        Probes are grounded in the candidate's parsed CV/skills and rubric evaluations;
        gap probes surface job-required skills the candidate has not evidenced. When the
        LLM is disabled or returns malformed output, a deterministic template fallback
        keeps the workflow functional.
        """
        from copilot.agents.interview_probe_generator import generate_interview_probes

        return await generate_interview_probes(
            llm=self._llm,
            candidate=candidate,
            job=job,
            correlation_id=self._correlation_id,
        )

    def finalize(
        self,
        candidate: Candidate,
        scores: list[RubricScore] | None = None,
        manager_comment: str | None = None,
    ) -> dict[str, Any]:
        """Gated finalize tool: only call after the review task is APPROVED.

        Records the approved candidate as ready for shortlist/export. If the task is not
        APPROVED this call must not be exposed to the model — approval is enforced by the
        review-task state machine in ``decide_candidate``.
        """
        overall = (
            sum(s.score for s in scores) / max(len(scores), 1) if scores else 0.0
        )
        return {
            "candidate_id": str(candidate.id),
            "overall_score": overall,
            "status": "finalized",
            "manager_comment": manager_comment,
        }
