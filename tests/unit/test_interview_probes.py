"""Unit tests for AI-generated interview probes."""

from __future__ import annotations

from uuid import uuid4

from copilot.agents.interview_probe_generator import (
    _coerce_probes,
    _extract_probe_array,
    _fallback_probes,
    generate_interview_probes,
)
from copilot.domain.candidate import Candidate
from copilot.domain.job import Job


def _candidate(**kwargs) -> Candidate:
    defaults: dict = {
        "id": uuid4(),
        "full_name": "Alex Rivera",
        "skills": ["Python", "FastAPI"],
        "years_of_experience": 6.0,
    }
    defaults.update(kwargs)
    return Candidate(**defaults)


class _StubLLM:
    """Minimal LLM stub returning a fixed text payload (no for_tier tiering)."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, *args, **kwargs):  # noqa: ANN002, ANN003
        class _Resp:
            text = ""

        resp = _Resp()
        resp.text = self._text
        return resp


def test_extract_probe_array_tolerates_markdown_fences() -> None:
    raw = 'Sure:\n```json\n[{"category": "technical", "question": "Explain the GIL"}]\n```'
    parsed = _extract_probe_array(raw)
    assert parsed is not None
    assert len(parsed) == 1


def test_coerce_probes_normalises_categories_and_dedupes() -> None:
    probes = _coerce_probes(
        [
            {"category": "Tech", "question": "Q1"},
            {"category": "red-flag", "question": "Q1"},
            {"type": "behavioral", "question": "Q2"},
            "Q3",
            {"category": "gap", "question": "   "},
        ]
    )
    assert [p["category"] for p in probes] == ["technical", "behavioral", "technical"]
    assert len(probes) == 3


def test_fallback_probes_shape_and_gap_skill() -> None:
    job = Job(id=uuid4(), title="Backend Engineer", skills=["Python", "Kubernetes"])
    probes = _fallback_probes(_candidate(skills=["Python"]), job)
    categories = [p["category"] for p in probes]
    assert categories.count("technical") == 2
    assert categories.count("gap") == 1
    assert "Kubernetes" in probes[-1]["question"]


async def test_generate_interview_probes_falls_back_without_llm() -> None:
    job = Job(id=uuid4(), title="Backend Engineer", skills=["Python", "Go"])
    probes = await generate_interview_probes(llm=None, candidate=_candidate(), job=job)
    assert 3 <= len(probes) <= 5


async def test_generate_interview_probes_uses_llm_json() -> None:
    payload = (
        '[{"category":"technical","question":"Describe a hard bug you fixed"},'
        '{"category":"behavioral","question":"Tell me about a team conflict"},'
        '{"category":"gap","question":"You lack Go. How would you ramp up?"}]'
    )
    probes = await generate_interview_probes(llm=_StubLLM(payload), candidate=_candidate())
    assert len(probes) == 3
    assert probes[0]["category"] == "technical"
    assert probes[-1]["category"] == "gap"
