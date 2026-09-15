"""Regression tests for evidence extraction and rubric scoring.

These guard the fix where criterion-mapped evidence (the only evidence
``RubricScorer`` reads, because it carries ``criterion_id``) was appended after
bulk skill snippets and then discarded by the ``[:50]`` cap. Skill-heavy CVs
such as generated mimic resumes therefore scored 0 on every criterion.
"""

from __future__ import annotations

from copilot.agents.evidence_extractor import extract_evidence
from copilot.agents.rubric_scorer import RubricScorer
from copilot.application.use_cases.ensure_job_rubric import build_default_rubric
from copilot.domain.candidate import Candidate
from copilot.domain.job import Job

_SKILLS = [
    "Java 17",
    "Spring Boot",
    "Spring Data JPA",
    "Hibernate",
    "RESTful APIs",
    "PostgreSQL",
]


def _skill_heavy_candidate() -> Candidate:
    """A mimic-style CV that names every required skill many times."""
    cv = (
        "CURRICULUM VITAE\nFULL NAME: Zaid Mansour\n"
        "Accomplished professional with 5+ years of experience in Java Backend Developer.\n"
        "Core Technologies: Java 17, Spring Boot, Spring Data JPA, Hibernate, "
        "RESTful APIs, PostgreSQL.\n"
        "Senior Specialist | CloudTech (2022 - Present)\n"
        "Led implementation leveraging Java 17, Spring Boot, Spring Data JPA, Hibernate, "
        "RESTful APIs, PostgreSQL.\n"
    )
    cv = cv * 7  # force well past the old 50-item evidence cap
    return Candidate(
        full_name="Zaid Mansour",
        raw_text=cv,
        skills=list(_SKILLS),
        years_of_experience=7.7,
    )


def test_criterion_evidence_survives_bulk_skill_snippets() -> None:
    candidate = _skill_heavy_candidate()
    rubric = build_default_rubric(Job(title="Java Backend Developer", skills=_SKILLS))

    evidence = extract_evidence(candidate, rubric)

    assert len(evidence) == 50
    # The scored evidence must never be crowded out by the bulk skill snippets.
    assert any(e.criterion_id is not None for e in evidence)


def test_mimic_style_candidate_scores_high() -> None:
    candidate = _skill_heavy_candidate()
    rubric = build_default_rubric(Job(title="Java Backend Developer", skills=_SKILLS))

    evidence = extract_evidence(candidate, rubric)
    scores = RubricScorer().score(candidate, rubric, evidence)
    overall = sum(s.score for s in scores) / len(scores)

    # Every required skill is present in the CV, so the match score must be high.
    assert overall >= 80.0
