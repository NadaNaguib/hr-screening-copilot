"""Extract structured evidence from candidate text."""

from __future__ import annotations

import re

from copilot.domain.candidate import Candidate
from copilot.domain.evidence import Evidence, EvidenceType
from copilot.domain.rubric import Rubric

# Total number of evidence rows persisted per candidate (bounds DB growth).
_MAX_EVIDENCE = 50
# Criterion keyword hits kept per criterion. ``RubricScorer`` only needs to see up
# to 3 matches to award full credit, so a small cap keeps the rubric evidence
# balanced and stops one keyword from monopolising the list.
_MAX_PER_CRITERION = 5
# Bulk skill snippets kept *after* the scoring-relevant evidence is captured.
_MAX_SKILL_EVIDENCE = 20


def _snippet(text: str, start: int, end: int) -> str:
    return text[max(0, start - 80) : min(len(text), end + 80)]


def extract_evidence(candidate: Candidate, rubric: Rubric | None = None) -> list[Evidence]:
    """Extract evidence snippets from candidate raw text.

    Evidence is ordered by scoring relevance: rubric/criterion evidence (the only
    kind ``RubricScorer`` consumes, because it carries ``criterion_id``) is
    collected *first*, then experience, then bulk skill snippets.

    The previous implementation appended every skill snippet (which carries no
    ``criterion_id``) before the criterion evidence and then truncated the list
    with ``[:50]``. Any skill-heavy CV — e.g. a generated mimic resume that lists
    the whole job skill set — filled the cap with skill snippets and had every
    scored match discarded, so it received 0 credit on every criterion. Criterion
    evidence can no longer be displaced by the total cap.
    """
    criterion_evidence: list[Evidence] = []
    experience_evidence: list[Evidence] = []
    skill_evidence: list[Evidence] = []

    text = candidate.raw_text
    if not text:
        return []

    # 1) Rubric-specific evidence -> the only evidence that drives scoring.
    if rubric:
        for criterion in rubric.criteria:
            matched = 0
            for keyword in criterion.keywords:
                if matched >= _MAX_PER_CRITERION:
                    break
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    if matched >= _MAX_PER_CRITERION:
                        break
                    criterion_evidence.append(
                        Evidence(
                            candidate_id=candidate.id,
                            criterion_id=criterion.id,
                            evidence_type=EvidenceType.OTHER,
                            quote=_snippet(text, match.start(), match.end()),
                            confidence=0.7,
                            metadata={"criterion": criterion.name, "keyword": keyword},
                        )
                    )
                    matched += 1

    # 2) Experience evidence.
    years = candidate.years_of_experience
    if years > 0:
        experience_evidence.append(
            Evidence(
                candidate_id=candidate.id,
                evidence_type=EvidenceType.EXPERIENCE,
                quote=f"{years} years of experience",
                confidence=0.9,
                metadata={"years": years},
            )
        )

    # 3) Skill evidence (bulk; carries no criterion_id) — collected last so it can
    #    never crowd out the criterion evidence above.
    for skill in candidate.skills:
        if len(skill_evidence) >= _MAX_SKILL_EVIDENCE:
            break
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            if len(skill_evidence) >= _MAX_SKILL_EVIDENCE:
                break
            skill_evidence.append(
                Evidence(
                    candidate_id=candidate.id,
                    evidence_type=EvidenceType.SKILL,
                    quote=_snippet(text, match.start(), match.end()),
                    confidence=0.8,
                    metadata={"skill": skill},
                )
            )

    return (criterion_evidence + experience_evidence + skill_evidence)[:_MAX_EVIDENCE]
