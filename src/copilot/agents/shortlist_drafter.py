"""Shortlist drafter with gated finalize tool."""
from __future__ import annotations

from typing import Any

from copilot.domain.candidate import Candidate
from copilot.domain.rubric_score import RubricScore
from copilot.domain.shortlist import Shortlist, ShortlistEntry


class ShortlistDrafter:
    """Draft a shortlist entry; finalize is gated externally."""

    def draft(
        self,
        candidate: Candidate,
        scores: list[RubricScore],
        manager_comment: str | None = None,
    ) -> Shortlist:
        overall = sum(s.score for s in scores) / max(len(scores), 1)
        entry = ShortlistEntry(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            overall_score=overall,
            status="draft",
            manager_comment=manager_comment,
        )
        return Shortlist(
            job_id=candidate.job_id,
            name=f"Shortlist for {candidate.full_name}",
            entries=[entry],
        )

    def finalize(
        self,
        candidate: Candidate,
        scores: list[RubricScore],
        manager_comment: str | None = None,
    ) -> dict[str, Any]:
        """Gated finalize tool: only call after manager approval."""
        overall = sum(s.score for s in scores) / max(len(scores), 1)
        return {
            "candidate_id": str(candidate.id),
            "overall_score": overall,
            "status": "finalized",
            "manager_comment": manager_comment,
        }
