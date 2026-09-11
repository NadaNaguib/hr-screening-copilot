"""Multi-scope script tools for HR Screening Agentic RAG.

Provides discrete retrieval tools across 4 distinct scopes:
1. Candidate Scope: identity lookup, full CV reader, section extractor, isolated CV chunk search, screening evaluation.
2. Job Requisition Scope: job description details, rubric criteria & weights, active jobs list.
3. Talent Pool Scope: cross-candidate semantic search, side-by-side candidate comparison, ranked applicants by job.
4. Pipeline Scope: pipeline distribution stats, human review queue items.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from copilot.application.ports.embedding_port import EmbeddingPort
from copilot.infrastructure.db.models import (
    CandidateORM,
    DocumentORM,
    JobORM,
    ReviewTaskORM,
    RubricCriterionORM,
    RubricORM,
)

# ─────────────────────────────────────────────────────────────────────────────
# Scope 1: Candidate Scope
# ─────────────────────────────────────────────────────────────────────────────


async def lookup_candidate(
    session: AsyncSession,
    name_or_query: str,
) -> dict[str, Any]:
    """Resolve a candidate by name, email, or UUID.

    Returns candidate profile if found, or available candidates list if not found.
    """
    cleaned = name_or_query.strip()
    if not cleaned:
        return {"found": False, "message": "No candidate name provided", "available_candidates": []}

    # Try exact UUID
    try:
        cand_uuid = UUID(cleaned)
        stmt = select(CandidateORM).where(CandidateORM.id == cand_uuid)
        res = await session.execute(stmt)
        cand = res.scalar_one_or_none()
        if cand:
            return _format_candidate_card(cand, session)
    except (ValueError, AttributeError):
        pass

    # Try full name / email match
    stmt = (
        select(CandidateORM, JobORM.title.label("job_title"))
        .outerjoin(JobORM, CandidateORM.job_id == JobORM.id)
        .where(
            (CandidateORM.full_name.ilike(f"%{cleaned}%"))
            | (CandidateORM.email.ilike(f"%{cleaned}%"))
        )
    )
    res = await session.execute(stmt)
    matches = res.all()

    if matches:
        cand, job_title = matches[0]
        card = _format_candidate_dict(cand, job_title)
        card["found"] = True
        return card

    # Try matching first or last name
    parts = cleaned.split()
    if len(parts) > 1:
        stmt_part = (
            select(CandidateORM, JobORM.title.label("job_title"))
            .outerjoin(JobORM, CandidateORM.job_id == JobORM.id)
            .where(
                (CandidateORM.full_name.ilike(f"%{parts[0]}%"))
                | (CandidateORM.full_name.ilike(f"%{parts[-1]}%"))
            )
        )
        res_part = await session.execute(stmt_part)
        part_matches = res_part.all()
        if part_matches:
            cand, job_title = part_matches[0]
            card = _format_candidate_dict(cand, job_title)
            card["found"] = True
            return card

    # Not found: return list of available candidates
    all_cands = await session.execute(select(CandidateORM.full_name, CandidateORM.id))
    avail = [r[0] for r in all_cands.all() if r[0]]
    return {
        "found": False,
        "query": cleaned,
        "message": f"Candidate '{cleaned}' was not found in the talent pool records.",
        "available_candidates": sorted(set(avail)),
    }


def _format_candidate_dict(cand: CandidateORM, job_title: str | None) -> dict[str, Any]:
    return {
        "found": True,
        "candidate_id": str(cand.id),
        "full_name": cand.full_name,
        "email": cand.email,
        "phone": cand.phone,
        "job_title": job_title or "Unassigned",
        "job_id": str(cand.job_id) if cand.job_id else None,
        "status": cand.status,
        "overall_score": cand.overall_score,
        "years_of_experience": cand.years_of_experience,
        "skills": cand.skills or [],
        "priority": cand.priority,
        "has_cv_text": bool(cand.raw_text),
        "education": cand.education or [],
        "work_experience": cand.work_experience or [],
    }


def _format_candidate_card(cand: CandidateORM, session: AsyncSession) -> dict[str, Any]:
    return _format_candidate_dict(cand, None)


async def get_candidate_cv(
    session: AsyncSession,
    candidate_id: UUID,
    section: str | None = None,
) -> dict[str, Any]:
    """Retrieve full CV text or specific section for a candidate with document citations."""
    cand = await session.get(CandidateORM, candidate_id)
    if not cand:
        return {"error": f"Candidate {candidate_id} not found"}

    # Find attached document
    docs_res = await session.execute(select(DocumentORM))
    doc = None
    for d in docs_res.scalars().all():
        meta = d.metadata_ or {}
        if str(meta.get("candidate_id")) == str(candidate_id) or d.filename.startswith(
            cand.full_name.replace(" ", "_")
        ):
            doc = d
            break

    cv_text = (doc.raw_text if doc and doc.raw_text else cand.raw_text) or ""
    filename = doc.filename if doc else f"{cand.full_name.replace(' ', '_')}_CV.pdf"

    # Filter by section if requested
    filtered_text = cv_text
    section_name = "Full CV"
    if section:
        s_lower = section.lower()
        patterns = {
            "skills": r"(CORE TECHNICAL SKILLS|TECHNICAL SKILLS|SKILLS)[\s\S]*?(?=(PROFESSIONAL WORK EXPERIENCE|WORK EXPERIENCE|EXPERIENCE|EDUCATION|$))",
            "experience": r"(PROFESSIONAL WORK EXPERIENCE|WORK EXPERIENCE|EXPERIENCE)[\s\S]*?(?=(EDUCATION|PROJECTS|CERTIFICATIONS|$))",
            "education": r"(EDUCATION)[\s\S]*?(?=(PROJECTS|OPEN SOURCE|CERTIFICATIONS|$))",
            "projects": r"(PROJECTS|OPEN SOURCE)[\s\S]*?(?=(CERTIFICATIONS|$))",
            "certifications": r"(CERTIFICATIONS)[\s\S]*?$",
        }
        for key, pattern in patterns.items():
            if key in s_lower:
                match = re.search(pattern, cv_text, re.IGNORECASE)
                if match:
                    filtered_text = match.group(0).strip()
                    section_name = key.capitalize()
                    break

    citation = {
        "id": f"cv_{cand.id}",
        "quote": filtered_text[:350].replace("\n", " ").strip(),
        "source": filename,
        "page": 1,
        "candidate_id": str(cand.id),
        "candidate_name": cand.full_name,
        "full_context": filtered_text,
        "scope": "candidate_cv",
    }

    return {
        "candidate_id": str(cand.id),
        "full_name": cand.full_name,
        "filename": filename,
        "section": section_name,
        "text": filtered_text,
        "citations": [citation],
    }


async def search_candidate_cv(
    session: AsyncSession,
    embedding_port: EmbeddingPort,
    candidate_id: UUID,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search strictly inside a specific candidate's CV chunks (zero cross-talk)."""
    cand = await session.get(CandidateORM, candidate_id)
    if not cand:
        return []

    # Get chunks belonging strictly to this candidate
    cand_id_str = str(candidate_id)
    raw_query = """
        SELECT c.id, c.document_id, c.text, c.page_number, c.metadata,
               d.filename, d.raw_text
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (c.metadata->>'candidate_id' = :cid OR d.metadata->>'candidate_id' = :cid)
    """
    res = await session.execute(text(raw_query), {"cid": cand_id_str})
    rows = res.mappings().all()

    if not rows:
        # Fallback to in-memory candidate raw_text
        cv_text = cand.raw_text or ""
        if not cv_text:
            return []
        return [
            {
                "id": f"raw_{cand.id}",
                "chunk_id": f"raw_{cand.id}",
                "quote": cv_text[:350].replace("\n", " ").strip(),
                "source": f"{cand.full_name.replace(' ', '_')}_CV.pdf",
                "page": 1,
                "candidate_id": cand_id_str,
                "candidate_name": cand.full_name,
                "full_context": cv_text,
                "scope": "candidate_cv",
                "confidence": 1.0,
            }
        ]

    # Vector search on these candidate chunks
    emb = (await embedding_port.embed([query]))[0]
    vector_str = f"[{','.join(str(v) for v in emb)}]"

    sql = """
        SELECT c.id, c.document_id, c.text, c.page_number, c.metadata,
               d.filename, d.raw_text,
               c.embedding <=> CAST(:embedding AS vector) AS distance
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (c.metadata->>'candidate_id' = :cid OR d.metadata->>'candidate_id' = :cid)
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """
    vector_res = await session.execute(
        text(sql),
        {"embedding": vector_str, "cid": cand_id_str, "limit": top_k},
    )

    results = []
    for r in vector_res.mappings().all():
        dist = float(r["distance"]) if r.get("distance") is not None else 0.5
        results.append(
            {
                "id": str(r["id"]),
                "chunk_id": str(r["id"]),
                "quote": r["text"],
                "source": r.get("filename") or f"{cand.full_name.replace(' ', '_')}_CV.pdf",
                "page": int(r.get("page_number") or 1),
                "candidate_id": cand_id_str,
                "candidate_name": cand.full_name,
                "full_context": r.get("raw_text") or r["text"],
                "scope": "candidate_cv",
                "confidence": max(0.0, 1.0 - dist),
            }
        )
    return results


async def get_candidate_evaluation(
    session: AsyncSession,
    candidate_id: UUID,
) -> dict[str, Any]:
    """Retrieve candidate screening score breakdown, rubric scores, and review status."""
    cand = await session.get(CandidateORM, candidate_id)
    if not cand:
        return {"error": f"Candidate {candidate_id} not found"}

    rt_res = await session.execute(
        select(ReviewTaskORM).where(ReviewTaskORM.candidate_id == candidate_id)
    )
    task = rt_res.scalar_one_or_none()

    job_title = "Unassigned"
    if cand.job_id:
        job = await session.get(JobORM, cand.job_id)
        if job:
            job_title = job.title

    return {
        "candidate_id": str(cand.id),
        "full_name": cand.full_name,
        "job_title": job_title,
        "overall_score": cand.overall_score,
        "status": cand.status,
        "priority": cand.priority,
        "review_status": task.status if task else "NOT_IN_QUEUE",
        "review_priority": task.priority if task else "N/A",
        "skills": cand.skills or [],
        "years_of_experience": cand.years_of_experience,
        "summary": f"{cand.full_name} has an overall score of {cand.overall_score or 'N/A'}/100 and is in '{cand.status}' status for {job_title}.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scope 2: Job Requisition Scope
# ─────────────────────────────────────────────────────────────────────────────


async def get_job_details(
    session: AsyncSession,
    job_id_or_title: str,
) -> dict[str, Any]:
    """Retrieve full job requisition description, department, and required skills."""
    cleaned = job_id_or_title.strip()
    job = None
    try:
        j_uuid = UUID(cleaned)
        job = await session.get(JobORM, j_uuid)
    except (ValueError, AttributeError):
        pass

    if not job:
        stmt = select(JobORM).where(JobORM.title.ilike(f"%{cleaned}%"))
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()

    if not job:
        all_jobs = (await session.execute(select(JobORM.title))).scalars().all()
        return {
            "found": False,
            "message": f"Job requisition '{cleaned}' was not found.",
            "available_jobs": all_jobs,
        }

    skills = job.skills or []
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)

    citation = {
        "id": f"job_{job.id}",
        "quote": f"Job: {job.title} | Dept: {job.department} | Skills: {skills_str}",
        "source": f"Job Requisition: {job.title}",
        "page": 1,
        "candidate_id": "",
        "full_context": f"Title: {job.title}\nDepartment: {job.department}\nLocation: {job.location}\nRequired Skills: {skills_str}\nDescription: {job.description}",
        "scope": "job_requirements",
    }

    return {
        "found": True,
        "job_id": str(job.id),
        "title": job.title,
        "department": job.department,
        "description": job.description,
        "location": job.location,
        "priority": job.priority,
        "skills": skills,
        "citations": [citation],
    }


async def get_job_rubric(
    session: AsyncSession,
    job_id: UUID | None = None,
    job_title: str | None = None,
) -> dict[str, Any]:
    """Retrieve rubric scoring criteria, weights, required status, and keywords."""
    if not job_id and job_title:
        j_res = await session.execute(select(JobORM).where(JobORM.title.ilike(f"%{job_title}%")))
        j = j_res.scalar_one_or_none()
        if j:
            job_id = j.id

    stmt = (
        select(
            RubricCriterionORM, RubricORM.name.label("rubric_name"), JobORM.title.label("job_title")
        )
        .join(RubricORM, RubricCriterionORM.rubric_id == RubricORM.id)
        .join(JobORM, RubricORM.job_id == JobORM.id)
    )
    if job_id:
        stmt = stmt.where(JobORM.id == job_id)

    res = await session.execute(stmt)
    rows = res.all()

    criteria = []
    citations = []
    for rc, rubric_name, j_title in rows:
        kw = rc.keywords or []
        kw_str = ", ".join(kw) if isinstance(kw, list) else str(kw)
        c_dict = {
            "name": rc.name,
            "description": rc.description,
            "weight": rc.weight,
            "required": rc.required,
            "keywords": kw,
            "min_score": rc.min_score,
            "max_score": rc.max_score,
            "job_title": j_title,
        }
        criteria.append(c_dict)
        citations.append(
            {
                "id": f"crit_{rc.id}",
                "quote": f"Criterion: {rc.name} (Weight: {rc.weight}, Required: {rc.required}) — Keywords: {kw_str}",
                "source": f"Rubric: {rubric_name} ({j_title})",
                "page": 1,
                "candidate_id": "",
                "full_context": f"Criterion: {rc.name}\nDescription: {rc.description}\nWeight: {rc.weight}\nRequired: {rc.required}\nScore Range: {rc.min_score}-{rc.max_score}\nKeywords: {kw_str}",
                "scope": "rubric",
            }
        )

    return {
        "job_id": str(job_id) if job_id else None,
        "criteria_count": len(criteria),
        "criteria": criteria,
        "citations": citations,
    }


async def list_all_jobs(session: AsyncSession) -> list[dict[str, Any]]:
    """List all open job requisitions with title, department, priority, and required skills."""
    res = await session.execute(select(JobORM).order_by(JobORM.created_at.desc()))
    jobs = []
    for j in res.scalars().all():
        jobs.append(
            {
                "job_id": str(j.id),
                "title": j.title,
                "department": j.department,
                "priority": j.priority,
                "skills": j.skills or [],
                "location": j.location,
            }
        )
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Scope 3: Talent Pool & Comparison Scope
# ─────────────────────────────────────────────────────────────────────────────


async def search_talent_pool(
    session: AsyncSession,
    embedding_port: EmbeddingPort,
    query: str,
    job_id: UUID | None = None,
    skill: str | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """Cross-candidate ranked semantic and keyword search across all resumes."""
    emb = (await embedding_port.embed([query]))[0]
    vector_str = f"[{','.join(str(v) for v in emb)}]"

    sql = """
        SELECT c.id, c.document_id, c.job_id, c.text, c.page_number, c.metadata,
               d.filename, d.raw_text, d.metadata AS doc_meta,
               cand.id AS cand_id, cand.full_name, cand.overall_score,
               c.embedding <=> CAST(:embedding AS vector) AS distance
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN candidates cand ON CAST(d.metadata->>'candidate_id' AS uuid) = cand.id
        WHERE (CAST(:job_id AS uuid) IS NULL OR c.job_id = CAST(:job_id AS uuid))
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """
    res = await session.execute(
        text(sql),
        {"embedding": vector_str, "job_id": str(job_id) if job_id else None, "limit": top_k},
    )

    results = []
    for row in res.mappings().all():
        name = row.get("full_name") or "Talent Pool Candidate"
        cand_id_str = str(row.get("cand_id") or "")
        dist = float(row["distance"]) if row.get("distance") is not None else 0.5
        results.append(
            {
                "id": str(row["id"]),
                "chunk_id": str(row["id"]),
                "quote": row["text"],
                "source": row.get("filename") or f"{name.replace(' ', '_')}_CV.pdf",
                "page": int(row.get("page_number") or 1),
                "candidate_id": cand_id_str,
                "candidate_name": name,
                "overall_score": row.get("overall_score"),
                "full_context": row.get("raw_text") or row["text"],
                "scope": "talent_pool",
                "confidence": max(0.0, 1.0 - dist),
            }
        )
    return results


async def compare_candidates(
    session: AsyncSession,
    candidate_ids: list[UUID],
) -> dict[str, Any]:
    """Side-by-side comparative analysis of multiple candidates."""
    stmt = (
        select(CandidateORM, JobORM.title.label("job_title"))
        .outerjoin(JobORM, CandidateORM.job_id == JobORM.id)
        .where(CandidateORM.id.in_(candidate_ids))
    )
    res = await session.execute(stmt)
    rows = res.all()

    candidates_summary = []
    citations = []
    for cand, job_title in rows:
        skills = cand.skills or []
        summary = {
            "candidate_id": str(cand.id),
            "full_name": cand.full_name,
            "job_title": job_title or "Unassigned",
            "overall_score": cand.overall_score,
            "years_of_experience": cand.years_of_experience,
            "skills": skills,
            "status": cand.status,
            "education": [e.get("degree") for e in (cand.education or []) if isinstance(e, dict)],
        }
        candidates_summary.append(summary)
        citations.append(
            {
                "id": f"comp_{cand.id}",
                "quote": f"{cand.full_name}: {cand.years_of_experience} yrs exp | Score: {cand.overall_score}/100 | Skills: {', '.join(skills[:6])}",
                "source": f"{cand.full_name.replace(' ', '_')}_CV.pdf",
                "page": 1,
                "candidate_id": str(cand.id),
                "candidate_name": cand.full_name,
                "full_context": cand.raw_text[:500]
                if cand.raw_text
                else f"{cand.full_name} profile",
                "scope": "candidate_comparison",
            }
        )

    return {
        "candidate_count": len(candidates_summary),
        "candidates": candidates_summary,
        "citations": citations,
    }


async def list_candidates_for_job(
    session: AsyncSession,
    job_id: UUID,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List candidates applied to a specific job requisition, ranked by overall score."""
    stmt = select(CandidateORM).where(CandidateORM.job_id == job_id)
    if status:
        stmt = stmt.where(CandidateORM.status == status)
    stmt = stmt.order_by(CandidateORM.overall_score.desc().nullslast())

    res = await session.execute(stmt)
    return [
        {
            "candidate_id": str(c.id),
            "full_name": c.full_name,
            "overall_score": c.overall_score,
            "years_of_experience": c.years_of_experience,
            "skills": c.skills or [],
            "status": c.status,
            "priority": c.priority,
        }
        for c in res.scalars().all()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Scope 4: Pipeline & Review Queue Scope
# ─────────────────────────────────────────────────────────────────────────────


async def get_pipeline_stats(session: AsyncSession) -> dict[str, Any]:
    """Get screening pipeline distribution metrics and candidate counts by status."""
    stmt = select(CandidateORM.status, func.count(CandidateORM.id)).group_by(CandidateORM.status)
    res = await session.execute(stmt)
    status_counts = {str(r[0]): int(r[1]) for r in res.all()}

    total = sum(status_counts.values())
    return {
        "total_candidates": total,
        "status_distribution": status_counts,
        "screened": status_counts.get("screened", 0),
        "uploaded": status_counts.get("uploaded", 0),
        "shortlisted": status_counts.get("shortlisted", 0),
        "rejected": status_counts.get("rejected", 0),
        "human_review": status_counts.get("human_review", 0),
    }


async def get_review_queue_status(
    session: AsyncSession,
    priority: str | None = None,
) -> list[dict[str, Any]]:
    """Get pending human review tasks with candidate details."""
    stmt = (
        select(ReviewTaskORM, CandidateORM.full_name, JobORM.title.label("job_title"))
        .join(CandidateORM, ReviewTaskORM.candidate_id == CandidateORM.id)
        .outerjoin(JobORM, ReviewTaskORM.job_id == JobORM.id)
        .where(ReviewTaskORM.status.in_(["PENDING_TRIAGE", "PENDING_DECISION", "IN_REVIEW"]))
    )
    if priority:
        stmt = stmt.where(ReviewTaskORM.priority.ilike(f"%{priority}%"))
    stmt = stmt.order_by(ReviewTaskORM.created_at.desc()).limit(15)

    res = await session.execute(stmt)
    tasks = []
    for rt, name, j_title in res.all():
        tasks.append(
            {
                "task_id": str(rt.id),
                "candidate_id": str(rt.candidate_id),
                "candidate_name": name,
                "job_title": j_title or "Unassigned",
                "status": rt.status,
                "priority": rt.priority,
                "created_at": rt.created_at.isoformat() if rt.created_at else None,
            }
        )
    return tasks
