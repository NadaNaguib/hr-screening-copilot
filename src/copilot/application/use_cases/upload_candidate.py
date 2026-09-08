"""Upload a candidate CV, deduplicate by SHA-256, and create a review task."""
from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from copilot.domain.candidate import Candidate, CandidateStatus
from copilot.domain.review_task import ReviewTask
from copilot.domain.sla_rule import Priority, resolve_sla_duration
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id
from copilot.infrastructure.parsing.parser import parse_document, sha256_bytes


def _extract_years(text: str) -> float:
    matches = re.findall(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", text, re.IGNORECASE)
    if matches:
        return float(matches[0])
    return 0.0


def _extract_skills_fallback(text: str) -> list[str]:
    """Regex fallback for skill extraction when LLM is unavailable."""
    common = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "node.js", "sql", "postgresql", "docker", "kubernetes", "aws",
        "azure", "gcp", "machine learning", "data analysis", "project management",
        "agile", "scrum", "leadership", "communication", "teamwork", "fastapi",
        "flask", "django", "html", "css", "tailwind", "bootstrap", "git", "linux",
        "nginx", "redis", "mongodb", "mysql", "sqlite", "opencv", "tensorflow",
        "pytorch", "keras", "pandas", "numpy", "matplotlib", "seaborn", "excel",
        "rest api", "graphql", "microservices", "ci/cd", "jenkins", "github actions",
    ]
    lower = text.lower()
    found = [skill for skill in common if skill in lower]
    return list(dict.fromkeys(found))


async def _extract_skills_with_llm(text: str, llm: Any, correlation_id: str = "") -> list[str]:
    """Use Gemini to extract professional skills/keywords from a CV; fallback to regex."""
    from copilot.infrastructure.config.ai_config import AIConfigManager

    ai_config = AIConfigManager().config
    if not llm or not ai_config.ai_enabled:
        return _extract_skills_fallback(text)
    prompt = (
        "You are a resume parser. Extract the professional skills, technologies, programming languages, "
        "frameworks, databases, cloud platforms, tools, and methodologies mentioned in the CV below. "
        "Return ONLY a single JSON array of strings. Example: [\"Python\", \"FastAPI\", \"React\", \"Docker\", \"AWS\"]. "
        "No explanations, no code fences, no markdown, no additional text.\n\nCV TEXT:\n"
        + text[:8000]
    )
    try:
        response = await llm.generate(
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
        existing.skills = await _extract_skills_with_llm(raw_text, container.llm, correlation_id) or existing.skills
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
    chunk_data = [(text, None, {"type": "cv", "filename": filename, "index": i}) for i, (text, _) in enumerate(chunks)]
    embeddings = await container.embedding.embed([c[0] for c in chunk_data], correlation_id=correlation_id)
    from copilot.infrastructure.db.models import DocumentORM

    doc = DocumentORM(
        job_id=job_id,
        filename=filename,
        mime_type=mime_type,
        sha256=sha256,
        raw_text=raw_text,
        metadata_={"candidate_id": str(candidate.id)},
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
