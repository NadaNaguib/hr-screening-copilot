"""Interview probe generator: tailored interview questions from a candidate profile.

Produces 3-5 questions grounded in the candidate's parsed CV and rubric score:

* 2 **technical** probes that validate claimed skills/tools.
* 1-2 **behavioral** probes exploring collaboration, ownership and delivery.
* 1 **gap** probe that surfaces missing skills or experience gaps relative to the
  job's required skills.

The LLM is asked for a strict JSON array. When the LLM is disabled, degraded, or
returns malformed output the module falls back to a deterministic, template-based
set so the feature never breaks the surrounding workflow.
"""

from __future__ import annotations

import json
import re
from typing import Any

from copilot.domain.candidate import Candidate
from copilot.domain.job import Job

MAX_PROBES = 5
MIN_PROBES = 3

_CATEGORY_ALIASES: dict[str, str] = {
    "technical": "technical",
    "tech": "technical",
    "skill": "technical",
    "skills": "technical",
    "tooling": "technical",
    "behavioral": "behavioral",
    "behavioural": "behavioral",
    "behavior": "behavioral",
    "behaviour": "behavioral",
    "situational": "behavioral",
    "culture": "behavioral",
    "teamwork": "behavioral",
    "gap": "gap",
    "red_flag": "gap",
    "red-flag": "gap",
    "redflag": "gap",
    "risk": "gap",
    "concern": "gap",
    "experience": "gap",
}

_SYSTEM_INSTRUCTION = (
    "You are a senior technical interviewer. You craft precise, non-discriminatory "
    "interview questions that probe a candidate's real capabilities and surface gaps. "
    "Never reference protected attributes such as age, gender, nationality, religion, "
    "marital status or disability."
)


def _normalise_category(raw: Any) -> str:
    """Map a free-form category label onto technical/behavioral/gap."""
    key = str(raw or "").strip().lower().replace(" ", "_")
    return _CATEGORY_ALIASES.get(key, "technical")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result


def _missing_skills(candidate: Candidate, job: Job | None) -> list[str]:
    """Return job-required skills the candidate has not evidenced."""
    if job is None:
        return []
    have = {s.strip().lower() for s in (candidate.skills or []) if s and s.strip()}
    return [s for s in (job.skills or []) if s and s.strip() and s.strip().lower() not in have]


def _build_prompt(candidate: Candidate, job: Job | None) -> str:
    skills = ", ".join(candidate.skills[:15]) if candidate.skills else "not specified"
    required = ", ".join((job.skills or [])[:15]) if job and job.skills else "not specified"
    missing = ", ".join(_missing_skills(candidate, job)) or "none identified"
    score = (
        f"{candidate.overall_score:.1f}%"
        if candidate.overall_score is not None
        else "not yet scored"
    )
    role = job.title if job else "the role"
    return (
        "Design 3 to 5 tailored interview questions for the candidate below.\n"
        "Return ONLY a single JSON array. Each element MUST be an object with exactly "
        'two string keys: "category" and "question".\n'
        'Allowed categories: "technical", "behavioral", "gap".\n'
        "Distribution: exactly 2 technical probes testing the candidate's claimed "
        "skills/tools, 1 to 2 behavioral/situational probes, and exactly 1 gap probe "
        "addressing a missing skill or experience gap versus the job requirements.\n"
        "No explanations, no markdown, no code fences, no additional text.\n\n"
        f"JOB TITLE: {role}\n"
        f"JOB REQUIRED SKILLS: {required}\n"
        f"CANDIDATE CLAIMED SKILLS: {skills}\n"
        f"CANDIDATE SKILLS MISSING VS JOB: {missing}\n"
        f"CANDIDATE YEARS OF EXPERIENCE: {candidate.years_of_experience}\n"
        f"CANDIDATE MATCH SCORE: {score}\n"
    )


def _extract_probe_array(raw: str) -> list[Any] | None:
    """Pull the first JSON array out of an LLM response, tolerating fences/text."""
    if not raw:
        return None
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            fenced = parts[1]
            text = fenced.replace("json", "", 1).strip() if fenced[:4].lower() == "json" else fenced
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate_json = text[start : end + 1]
    try:
        parsed = json.loads(candidate_json)
    except json.JSONDecodeError:
        try:
            normalised = re.sub(r",\s*([\]}])", r"\1", candidate_json)
            parsed = json.loads(normalised)
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, list) else None


def _coerce_probes(parsed: list[Any] | None) -> list[dict[str, Any]]:
    """Normalise raw LLM items into ``{category, question}`` dicts."""
    if not parsed:
        return []
    probes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in parsed:
        if isinstance(item, str):
            question, category = item, "technical"
        elif isinstance(item, dict):
            question = item.get("question") or item.get("probe") or item.get("text") or ""
            category = item.get("category") or item.get("type") or "technical"
        else:
            continue
        question = str(question).strip()
        if not question:
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        probes.append({"category": _normalise_category(category), "question": question})
        if len(probes) >= MAX_PROBES:
            break
    return probes


def _fallback_probes(candidate: Candidate, job: Job | None) -> list[dict[str, Any]]:
    """Deterministic 4-probe set used when the LLM is unavailable or unusable."""
    skills = _dedupe([s for s in (candidate.skills or []) if s and s.strip()])[:4]
    missing = _dedupe(_missing_skills(candidate, job))
    role = job.title if job and job.title else "this role"

    primary = skills[0] if skills else "your primary technology"
    secondary = skills[1] if len(skills) > 1 else "a core tool you rely on"

    probes: list[dict[str, Any]] = [
        {
            "category": "technical",
            "question": (
                f"Walk me through a production system where you used {primary}. "
                "What design decisions did you own and what trade-offs did you make?"
            ),
        },
        {
            "category": "technical",
            "question": (
                f"Describe the most complex problem you solved with {secondary}. "
                "How did you diagnose it, and how did you validate the fix?"
            ),
        },
        {
            "category": "behavioral",
            "question": (
                f"Tell me about a time you disagreed with a teammate while delivering for {role}. "
                "How did you resolve it and what was the outcome?"
            ),
        },
    ]

    gap = missing[0] if missing else None
    if gap:
        gap_question = (
            f"This role requires hands-on {gap}, which is not evident from your CV. "
            "Describe any exposure you have had to it and how you would ramp up quickly."
        )
    else:
        gap_question = (
            "Which responsibility in this role would you find most challenging, and how "
            "would you close that gap in your first 90 days?"
        )
    probes.append({"category": "gap", "question": gap_question})
    return probes


async def generate_interview_probes(
    llm: Any,
    candidate: Candidate,
    job: Job | None = None,
    correlation_id: str = "",
) -> list[dict[str, Any]]:
    """Return 3-5 tailored interview probes for ``candidate``.

    Falls back to a deterministic probe set whenever the LLM is disabled, errors,
    or returns output that cannot be parsed.
    """
    from copilot.infrastructure.providers.tiered_router import TaskTier

    prompt = _build_prompt(candidate, job)
    if llm is not None:
        try:
            tier_llm = llm.for_tier(TaskTier.FAST) if hasattr(llm, "for_tier") else llm
            response = await tier_llm.generate(
                prompt=prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_tokens=768,
                correlation_id=correlation_id,
            )
            probes = _coerce_probes(_extract_probe_array(getattr(response, "text", "") or ""))
            if len(probes) >= MIN_PROBES:
                return probes[:MAX_PROBES]
        except Exception:  # noqa: BLE001 - never break the calling workflow
            pass

    return _fallback_probes(candidate, job)
