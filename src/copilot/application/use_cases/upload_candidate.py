"""Upload a candidate CV, deduplicate by SHA-256, and create a review task."""
from __future__ import annotations

import re
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


def _extract_skills(text: str) -> list[str]:
    common = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "node.js", "sql", "postgresql", "docker", "kubernetes", "aws",
        "azure", "gcp", "machine learning", "data analysis", "project management",
        "agile", "scrum", "leadership", "communication", "teamwork",
    ]
    lower = text.lower()
    return [skill for skill in common if skill in lower]


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
        existing.skills = _extract_skills(raw_text) or existing.skills
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
            skills=_extract_skills(raw_text),
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
        triage_hours, _ = resolve_sla_duration(Priority(priority), job_rule)
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
    }
