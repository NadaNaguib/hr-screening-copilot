"""Rubric scorer: deterministic numeric aggregation + LLM justification."""

from __future__ import annotations

from copilot.domain.candidate import Candidate
from copilot.domain.evidence import Evidence
from copilot.domain.rubric import Rubric
from copilot.domain.rubric_score import RubricScore


class RubricScorer:
    """Score a candidate against a rubric."""

    def score(
        self,
        candidate: Candidate,
        rubric: Rubric,
        evidence: list[Evidence],
    ) -> list[RubricScore]:
        """Return rubric scores with deterministic aggregation."""
        scores: list[RubricScore] = []
        evidence_by_criterion: dict = {}
        for e in evidence:
            if e.criterion_id:
                evidence_by_criterion.setdefault(e.criterion_id, []).append(e)

        for criterion in rubric.criteria:
            matched = evidence_by_criterion.get(criterion.id, [])
            # Simple deterministic score based on evidence count and years
            base = min(len(matched), 3) / 3.0  # 0..1
            years_bonus = min(candidate.years_of_experience / 10.0, 0.3)
            raw = (base + years_bonus) * 100
            score = min(100.0, max(0.0, raw))
            scores.append(
                RubricScore(
                    candidate_id=candidate.id,
                    criterion_id=criterion.id,
                    score=score,
                    reasoning=(
                        f"Matched {len(matched)} evidence items for '{criterion.name}'. "
                        f"Years of experience: {candidate.years_of_experience}."
                    ),
                    evidence_ids=[e.id for e in matched[:5]],
                )
            )
        return scores
