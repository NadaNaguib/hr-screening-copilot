"""Upload a candidate CV, deduplicate by SHA-256, and create a review task."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from copilot.domain.candidate import Candidate, CandidateStatus
from copilot.domain.review_task import ReviewTask
from copilot.domain.sla_rule import Priority, resolve_sla_duration
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.infrastructure.parsing.parser import parse_document, sha256_bytes


def _extract_years(text: str) -> float:
    """Extract total unique years of professional experience from CV text.

    Combines explicit statements (e.g. "8 years of experience") with the union
    of non-overlapping work-history date ranges (e.g. "2019 - Present") so that
    overlapping roles are never double-counted.
    """
    if not text:
        return 0.0
    explicit = _extract_explicit_years(text)
    experience_text = _experience_section(text) or text
    ranged = _years_from_ranges(experience_text)
    years = max(explicit, ranged)
    return round(min(years, 50.0), 1)


_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_PRESENT_TOKENS = {"present", "current", "now", "today", "ongoing"}

_EXPERIENCE_HEADING_RE = re.compile(
    r"(work|professional|employment|relevant|career)\s+experience", re.IGNORECASE
)
_NEXT_SECTION_RE = re.compile(
    r"^\s*(education|certificat|skills|technical|projects|awards|languages|interests|references)\b",
    re.IGNORECASE,
)
_EDUCATION_LINE_RE = re.compile(
    r"b\.?sc|bachelor|master|m\.?sc|ph\.?d|university|college|education|gpa|degree|diploma",
    re.IGNORECASE,
)
_DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d{2})"
    r"\s*(?:-|–|—|to|until|till|through)\s*"
    r"(?P<end>(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d{2}|present|current|now|today|ongoing)",
    re.IGNORECASE,
)
_STRICT_YEARS_RE = re.compile(
    r"(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)[^.\n]{0,60}?experience", re.IGNORECASE
)
_LOOSE_YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)


def _extract_explicit_years(text: str) -> float:
    """Find an explicit "N years of experience" style statement."""
    strict = _STRICT_YEARS_RE.findall(text)
    if strict:
        return max(float(value) for value in strict)
    loose = _LOOSE_YEARS_RE.findall(text)
    if loose:
        return max(float(value) for value in loose)
    return 0.0


def _experience_section(text: str) -> str:
    """Return only the work-experience section of a CV, if a heading exists."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if _EXPERIENCE_HEADING_RE.search(line):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if _NEXT_SECTION_RE.search(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def _token_to_months(token: str, *, is_end: bool) -> int | None:
    """Convert a date token ("2021", "Jan 2021", "Present") to an absolute month."""
    token = token.strip().lower().rstrip(".")
    if token in _PRESENT_TOKENS:
        now = datetime.utcnow()
        return now.year * 12 + now.month
    month: int | None = None
    year: int | None = None
    for part in token.replace(",", " ").split():
        if part.rstrip(".") in _MONTHS:
            month = _MONTHS[part.rstrip(".")]
        elif part[:4].isdigit() and len(part) >= 4:
            year = int(part[:4])
    if year is None:
        return None
    if month is None:
        month = 12 if is_end else 1
    return year * 12 + month


def _years_from_ranges(text: str) -> float:
    """Total unique years covered by the union of work-history date ranges."""
    intervals: list[tuple[int, int]] = []
    for match in _DATE_RANGE_RE.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line = text[line_start : match.end()]
        if _EDUCATION_LINE_RE.search(line):
            continue
        start = _token_to_months(match.group("start"), is_end=False)
        end = _token_to_months(match.group("end"), is_end=True)
        if start is None or end is None or end < start:
            continue
        intervals.append((start, end))
    if not intervals:
        return 0.0
    intervals.sort()
    merged: list[list[int]] = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    total_months = sum(end - start for start, end in merged)
    return total_months / 12.0


def _extract_skills_fallback(text: str) -> list[str]:
    """Regex fallback for skill extraction when LLM is unavailable."""
    common = [
        "python",
        "javascript",
        "typescript",
        "java",
        "c++",
        "c#",
        "go",
        "rust",
        "react",
        "node.js",
        "sql",
        "postgresql",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "machine learning",
        "data analysis",
        "project management",
        "agile",
        "scrum",
        "leadership",
        "communication",
        "teamwork",
        "fastapi",
        "flask",
        "django",
        "html",
        "css",
        "tailwind",
        "bootstrap",
        "git",
        "linux",
        "nginx",
        "redis",
        "mongodb",
        "mysql",
        "sqlite",
        "opencv",
        "tensorflow",
        "pytorch",
        "keras",
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "excel",
        "rest api",
        "graphql",
        "microservices",
        "ci/cd",
        "jenkins",
        "github actions",
    ]
    lower = text.lower()
    found = [skill for skill in common if skill in lower]
    return list(dict.fromkeys(found))


async def _extract_skills_with_llm(text: str, llm: Any, correlation_id: str = "") -> list[str]:
    """Use Gemini to extract professional skills/keywords from a CV; fallback to regex."""
    from copilot.infrastructure.config.ai_config import AIConfigManager
    from copilot.infrastructure.providers.tiered_router import TaskTier

    ai_config = AIConfigManager().config
    if not llm or not ai_config.ai_enabled:
        return _extract_skills_fallback(text)
    prompt = (
        "You are a resume parser. Extract the professional skills, technologies, programming languages, "
        "frameworks, databases, cloud platforms, tools, and methodologies mentioned in the CV below. "
        'Return ONLY a single JSON array of strings. Example: ["Python", "FastAPI", "React", "Docker", "AWS"]. '
        "No explanations, no code fences, no markdown, no additional text.\n\nCV TEXT:\n"
        + text[:8000]
    )
    try:
        tier_llm = llm.for_tier(TaskTier.FAST) if hasattr(llm, "for_tier") else llm
        response = await tier_llm.generate(
            prompt=prompt,
            system_instruction=None,
            temperature=0.0,
            max_tokens=512,
            correlation_id=correlation_id,
        )
        raw = response.text.strip()
        print(f"[upload_candidate] LLM raw response ({len(raw)} chars): {raw[:500]}")
        # Try to extract the first JSON array from the response
        parsed = _extract_json_array(raw)
        if parsed:
            print(f"[upload_candidate] LLM parsed skills: {parsed}")
            return [str(item).strip() for item in parsed if str(item).strip()]
        print("[upload_candidate] LLM response did not contain a usable JSON array; using fallback")
    except Exception as exc:
        # Log and fall back to deterministic extraction so the pipeline still works
        print(f"[upload_candidate] LLM skill extraction failed: {exc}")
    return _extract_skills_fallback(text)


def _extract_json_array(raw: str) -> list[str] | None:
    """Extract a JSON array of strings from LLM output, tolerating markdown fences and extra text."""
    # If wrapped in markdown fences, take the fenced content
    if "```" in raw:
        raw = raw.split("```")[1]
        raw = raw.replace("json", "", 1).strip()

    # Look for the first JSON array in the text
    match = re.search(r"\[[\s\S]*?\]", raw)
    if not match:
        return None
    raw_array = match.group(0)
    try:
        parsed = json.loads(raw_array)
    except json.JSONDecodeError:
        # Try normalizing trailing commas and single quotes to double quotes
        normalized = re.sub(r",\s*\]", "]", raw_array)
        normalized = re.sub(r"'([^']*)'", r'"\1"', normalized)
        parsed = json.loads(normalized)
    if isinstance(parsed, list) and parsed:
        return [str(item).strip() for item in parsed if str(item).strip()]
    return None


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[tuple[str, int]]:
    words = text.split()
    chunks: list[tuple[str, int]] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append((" ".join(chunk_words), start))
        start = max(end - overlap, start + 1)
    return chunks


async def upload_candidate(
    container: Container,
    filename: str,
    content: bytes,
    mime_type: str,
    job_id: UUID | None = None,
    full_name: str = "",
    email: str = "",
    priority: str = "MEDIUM",
    correlation_id: str = "",
) -> dict:
    raw_text = parse_document(filename, content, mime_type)
    sha256 = sha256_bytes(content)

    existing = await container.candidate_repository.get_by_hash(job_id, sha256)
    if existing:
        # Update existing candidate path
        existing.full_name = full_name or existing.full_name
        existing.email = email or existing.email
        existing.raw_text = raw_text or existing.raw_text
        existing.years_of_experience = _extract_years(raw_text) or existing.years_of_experience
        existing.skills = (
            await _extract_skills_with_llm(raw_text, container.llm, correlation_id)
            or existing.skills
        )
        existing.priority = priority or existing.priority
        await container.candidate_repository.update_candidate(existing)
        candidate = existing
        is_new = False
    else:
        candidate = Candidate(
            job_id=job_id,
            full_name=full_name or filename,
            email=email,
            raw_text=raw_text,
            cv_sha256=sha256,
            years_of_experience=_extract_years(raw_text),
            skills=await _extract_skills_with_llm(raw_text, container.llm, correlation_id),
            priority=priority,
            status=CandidateStatus.UPLOADED,
        )
        candidate = await container.candidate_repository.create_candidate(candidate)
        is_new = True

    # Store CV chunks in vector store for retrieval
    chunks = _chunk_text(raw_text)
    chunk_data = [
        (text, None, {"type": "cv", "filename": filename, "index": i})
        for i, (text, _) in enumerate(chunks)
    ]
    embeddings = await container.embedding.embed(
        [c[0] for c in chunk_data], correlation_id=correlation_id
    )
    import base64
    import os

    from copilot.infrastructure.db.models import DocumentORM

    doc_metadata = {"candidate_id": str(candidate.id)}
    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        doc_metadata["pdf_bytes_b64"] = base64.b64encode(content).decode("ascii")
        try:
            os.makedirs("/tmp/cv_storage", exist_ok=True)
            with open(f"/tmp/cv_storage/{candidate.id}_{filename}", "wb") as f:  # noqa: ASYNC230, ASYNC240
                f.write(content)
        except Exception:
            pass

    doc = DocumentORM(
        job_id=job_id,
        filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        raw_text=raw_text,
        metadata_=doc_metadata,
    )
    container.session.add(doc)
    await container.session.flush()
    await container.session.refresh(doc)
    await container.vector_store.ingest_chunks(
        job_id=job_id,
        document_id=doc.id,
        chunks=chunk_data,
        embeddings=embeddings,
    )

    # Create review task if not exists
    task = await container.review_task_repository.get_task_by_candidate(candidate.id)
    if task is None:
        task = ReviewTask(candidate_id=candidate.id, job_id=job_id, priority=priority)
        # Resolve SLA deadline
        job_rule = await container.review_task_repository.get_sla_rule_for_job(job_id)
        triage_hours, _ = resolve_sla_duration(Priority(priority.lower()), job_rule)
        from datetime import datetime, timedelta

        task.triage_deadline_at = datetime.utcnow() + timedelta(hours=triage_hours)
        task = await container.review_task_repository.create_task(task)

    await container.audit.log(
        action="upload_candidate",
        target_type="candidate",
        target_id=str(candidate.id),
        actor_id=None,
        actor_role=None,
        details={"filename": filename, "is_new": is_new, "job_id": str(job_id)},
        correlation_id=correlation_id or get_correlation_id(),
    )
    return {
        "candidate_id": str(candidate.id),
        "review_task_id": str(task.id),
        "is_new": is_new,
        "status": candidate.status.value,
        "extracted_skills": candidate.skills,
        "years_of_experience": candidate.years_of_experience,
    }
