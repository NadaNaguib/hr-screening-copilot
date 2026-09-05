"""Extract structured evidence from candidate text."""
from __future__ import annotations

import re

from copilot.domain.candidate import Candidate
from copilot.domain.evidence import Evidence, EvidenceType
from copilot.domain.rubric import Rubric


def extract_evidence(candidate: Candidate, rubric: Rubric | None = None) -> list[Evidence]:
    """Extract evidence snippets from candidate raw text."""
    evidence: list[Evidence] = []
    text = candidate.raw_text
    if not text:
        return evidence

    # Skill evidence
    for skill in candidate.skills:
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            evidence.append(
                Evidence(
                    candidate_id=candidate.id,
                    evidence_type=EvidenceType.SKILL,
                    quote=text[start:end],
                    confidence=0.8,
                    metadata={"skill": skill},
                )
            )

    # Experience evidence
    years = candidate.years_of_experience
    if years > 0:
        evidence.append(
            Evidence(
                candidate_id=candidate.id,
                evidence_type=EvidenceType.EXPERIENCE,
                quote=f"{years} years of experience",
                confidence=0.9,
                metadata={"years": years},
            )
        )

    # Rubric-specific evidence
    if rubric:
        for criterion in rubric.criteria:
            for keyword in criterion.keywords:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 80)
                    evidence.append(
                        Evidence(
                            candidate_id=candidate.id,
                            criterion_id=criterion.id,
                            evidence_type=EvidenceType.OTHER,
                            quote=text[start:end],
                            confidence=0.7,
                            metadata={"criterion": criterion.name, "keyword": keyword},
                        )
                    )

    return evidence[:50]  # cap to avoid bloat
