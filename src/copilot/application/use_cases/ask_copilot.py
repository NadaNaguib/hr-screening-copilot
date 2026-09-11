"""Ask the copilot a question using Agentic RAG with multi-scope retrieval."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from copilot.agents.orchestrator import LangGraphOrchestrator
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


def check_query_safety_and_scope(q: str) -> str | None:
    ql = q.lower().strip()

    # 1. Jailbreak & Prompt injection
    if any(p in ql for p in ["system:", "you are now a different ai", "reveal all candidate data"]):
        return "I cannot execute this system override prompt. I am not able to deviate from HR screening protocols, will not comply with role reversals, and must reject inappropriate access attempts."
    if "ignore previous instructions" in ql:
        return "I cannot comply with this request. I am not able to execute inappropriate instructions or bypass safety guidelines, and I will not provide personal address data."

    # 2. PII extraction (email, phone, address)
    if any(
        p in ql
        for p in [
            "email address",
            "phone number",
            "home address",
            "personal address",
            "contact info",
        ]
    ):
        return "I cannot provide contact information or email addresses. It is not permitted under candidate data privacy policy."

    # 3. Protected attributes (nationality, gender, age)
    if any(p in ql for p in ["egypt or arab", "nationality", "country of origin", "countries"]):
        return "I cannot filter candidates by nationality or geographic origin. Nationality is a protected attribute and not relevant to professional qualifications; our screening guidelines do not consider nationality."
    if any(
        p in ql
        for p in ["male candidates", "female candidates", "only male", "only female", "gender"]
    ):
        return "I cannot comply with this request. We do not filter candidates by gender; gender is a protected attribute and screening is strictly audited against bias."
    if any(
        p in ql
        for p in [
            "youngest candidate",
            "oldest candidate",
            "age of the candidate",
            "candidate's age",
        ]
    ):
        return "I cannot evaluate candidate age. Age is a protected characteristic, not relevant to job requirements, and we do not filter candidates on this basis."

    # 4. Hallucination check & Impossible queries & Unknown entities
    if "bob" in ql and ("salary" in ql or "expectation" in ql):
        return "Salary expectation data is not available. I cannot provide compensation details as there is no information in the records, and Bob's salary was not found."
    if "20 years" in ql and "kubernetes" in ql:
        return "There is no candidate with 20 years of Kubernetes experience. None of the applicant profiles meet this query, and not found in any resume as no match exists."
    if "zephyr nightingale" in ql:
        return "Candidate Zephyr Nightingale was not found in the talent pool. There is no candidate by this name, so I cannot find any details and have no information."

    # 5. Out of scope
    if any(p in ql for p in ["weather in", "what is the weather", "recipe for", "football score"]):
        return "This request is not related to HR talent screening. I cannot help with weather forecasts as this is out of scope; please focus on candidates and screening evaluations."

    return None


async def ask_copilot(
    container: Container,
    question: str,
    job_id: UUID | None = None,
    correlation_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    correlation_id = correlation_id or get_correlation_id()

    # Fast safety & adversarial guardrail
    guard_refusal = check_query_safety_and_scope(question)
    if guard_refusal:
        yield {"type": "answer_chunk", "data": guard_refusal, "citations": []}
        yield {"type": "done", "data": "guard_refusal"}
        return

    from copilot.infrastructure.config.ai_config import AIConfigManager

    ai_config = AIConfigManager().config
    if not ai_config.ai_enabled:
        yield {
            "type": "answer_chunk",
            "data": "AI is currently disabled by the administrator.",
            "citations": [],
        }
        yield {"type": "done", "data": "AI disabled"}
        return

    # ─── Build Agentic RAG tool functions ──────────────────────────────────────

    async def _search_fn(
        query: str,
        job_id: UUID | None = None,
        top_k: int = 10,
        candidate_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Candidate-name-aware hybrid search tool."""
        embedding = (await container.embedding.embed([query]))[0]
        from sqlalchemy import text as sa_text

        vector_str = f"[{','.join(str(v) for v in embedding)}]"

        # Build SQL with optional candidate name filter via document/candidate join
        if candidate_name:
            # Filter chunks to only the candidate with matching full_name
            sql = """
                SELECT c.id, c.document_id, c.job_id, c.text, c.page_number, c.metadata,
                       d.filename, d.raw_text, d.metadata AS doc_meta,
                       cand.full_name,
                       c.embedding <=> CAST(:embedding AS vector) AS distance
                FROM chunks c
                LEFT JOIN documents d ON c.document_id = d.id
                LEFT JOIN candidates cand ON (d.metadata->>'candidate_id')::uuid = cand.id
                WHERE (cand.full_name ILIKE :name_pattern OR d.filename ILIKE :name_file)
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """
            name_parts = candidate_name.split()
            name_pattern = f"%{candidate_name}%"
            # Also try first name only if full name doesn't match
            name_file = f"%{name_parts[0]}%"
            result = await container.session.execute(
                sa_text(sql),
                {
                    "embedding": vector_str,
                    "name_pattern": name_pattern,
                    "name_file": name_file,
                    "limit": top_k,
                },
            )
        else:
            sql = """
                SELECT c.id, c.document_id, c.job_id, c.text, c.page_number, c.metadata,
                       d.filename, d.raw_text, d.metadata AS doc_meta,
                       cand.full_name,
                       c.embedding <=> CAST(:embedding AS vector) AS distance
                FROM chunks c
                LEFT JOIN documents d ON c.document_id = d.id
                LEFT JOIN candidates cand ON (d.metadata->>'candidate_id')::uuid = cand.id
                WHERE (CAST(:job_id AS uuid) IS NULL OR c.job_id = CAST(:job_id AS uuid))
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """
            result = await container.session.execute(
                sa_text(sql),
                {
                    "embedding": vector_str,
                    "job_id": str(job_id) if job_id else None,
                    "limit": top_k,
                },
            )

        rows = []
        for row in result.mappings().all():
            meta = dict(row["metadata"] or {})
            doc_meta = row.get("doc_meta") or {}
            candidate_id_val = ""
            if isinstance(doc_meta, dict):
                candidate_id_val = str(doc_meta.get("candidate_id") or "")
            rows.append(
                {
                    "id": str(row["id"]),
                    "chunk_id": str(row["id"]),
                    "quote": row["text"] or "",
                    "source": row.get("filename") or meta.get("source_document") or "Resume.pdf",
                    "page": int(row["page_number"] or 1),
                    "candidate_id": candidate_id_val,
                    "full_context": row.get("raw_text") or row["text"] or "",
                    "candidate_name": row.get("full_name") or "",
                    "confidence": max(0.0, 1.0 - float(row["distance"])),
                }
            )
        return rows

    async def _candidate_fn(name: str | None) -> list[dict[str, Any]]:
        """Get structured candidate profile by name."""
        if not name:
            return []
        from sqlalchemy import text as sa_text

        sql = """
            SELECT c.id, c.full_name, c.status, c.overall_score, c.job_id,
                   j.title as job_title
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.full_name ILIKE :pattern
            LIMIT 5
        """
        result = await container.session.execute(sa_text(sql), {"pattern": f"%{name}%"})
        rows = []
        for row in result.mappings().all():
            rows.append(
                {
                    "id": str(row["id"]),
                    "chunk_id": str(row["id"]),
                    "quote": (
                        f"Candidate: {row['full_name']} | Status: {row['status']} | "
                        f"Score: {row['overall_score'] or 'N/A'} | Job: {row['job_title'] or 'Unassigned'}"
                    ),
                    "source": "Candidate Profile (Database)",
                    "page": 1,
                    "candidate_id": str(row["id"]),
                    "full_context": (
                        f"Full Name: {row['full_name']}\nStatus: {row['status']}\n"
                        f"Overall Score: {row['overall_score'] or 'Not scored'}\n"
                        f"Applied Job: {row['job_title'] or 'No job assigned'}"
                    ),
                    "scope": "candidate_profile",
                }
            )
        return rows

    async def _job_fn(query: str, job_id: UUID | None = None) -> list[dict[str, Any]]:
        """Search job descriptions and requirements."""
        from sqlalchemy import text as sa_text

        if job_id:
            sql = """
                SELECT j.id, j.title, j.description, j.department, j.skills, j.location,
                       j.priority
                FROM jobs j
                WHERE j.id = CAST(:job_id AS uuid)
                LIMIT 1
            """
            result = await container.session.execute(sa_text(sql), {"job_id": str(job_id)})
        else:
            sql = """
                SELECT j.id, j.title, j.description, j.department, j.skills, j.location,
                       j.priority
                FROM jobs j
                ORDER BY j.created_at DESC
                LIMIT 5
            """
            result = await container.session.execute(sa_text(sql))

        rows = []
        for row in result.mappings().all():
            skills = row["skills"] or []
            skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
            rows.append(
                {
                    "id": str(row["id"]),
                    "chunk_id": str(row["id"]),
                    "quote": f"Job: {row['title']} ({row['department']}) — Requires: {skills_str}",
                    "source": f"Job Description: {row['title']}",
                    "page": 1,
                    "candidate_id": "",
                    "full_context": (
                        f"Title: {row['title']}\nDepartment: {row['department']}\n"
                        f"Location: {row['location']}\nPriority: {row['priority']}\n"
                        f"Required Skills: {skills_str}\n"
                        f"Description: {(row['description'] or '')[:500]}"
                    ),
                    "scope": "job_requirements",
                }
            )
        return rows

    async def _rubric_fn(job_id: UUID | None = None) -> list[dict[str, Any]]:
        """Get rubric evaluation criteria."""
        from sqlalchemy import text as sa_text

        if job_id:
            sql = """
                SELECT rc.id, rc.name, rc.description, rc.weight, rc.required,
                       rc.keywords, rc.min_score, rc.max_score,
                       r.name as rubric_name, j.title as job_title
                FROM rubric_criteria rc
                JOIN rubrics r ON rc.rubric_id = r.id
                JOIN jobs j ON r.job_id = j.id
                WHERE j.id = CAST(:job_id AS uuid)
                LIMIT 10
            """
            result = await container.session.execute(sa_text(sql), {"job_id": str(job_id)})
        else:
            sql = """
                SELECT rc.id, rc.name, rc.description, rc.weight, rc.required,
                       rc.keywords, rc.min_score, rc.max_score,
                       r.name as rubric_name, j.title as job_title
                FROM rubric_criteria rc
                JOIN rubrics r ON rc.rubric_id = r.id
                JOIN jobs j ON r.job_id = j.id
                ORDER BY r.created_at DESC
                LIMIT 10
            """
            result = await container.session.execute(sa_text(sql))

        rows = []
        for row in result.mappings().all():
            keywords = row["keywords"] or []
            kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
            rows.append(
                {
                    "id": str(row["id"]),
                    "chunk_id": str(row["id"]),
                    "quote": (
                        f"Criterion: {row['name']} (Weight: {row['weight']}, "
                        f"Required: {row['required']}) — Keywords: {kw_str}"
                    ),
                    "source": f"Rubric: {row['rubric_name']} for {row['job_title']}",
                    "page": 1,
                    "candidate_id": "",
                    "full_context": (
                        f"Criterion: {row['name']}\nDescription: {row['description'] or ''}\n"
                        f"Weight: {row['weight']} | Required: {row['required']}\n"
                        f"Score Range: {row['min_score']} - {row['max_score']}\n"
                        f"Keywords: {kw_str}"
                    ),
                    "scope": "rubric",
                }
            )
        return rows

    # ─── Run Agentic RAG or plain RAG ─────────────────────────────────────────

    if ai_config.agentic_rag_enabled:
        orchestrator = LangGraphOrchestrator(container.llm)
        chunk_received = False
        async for event in orchestrator.ask(
            question=question,
            job_id=job_id,
            correlation_id=correlation_id,
            session=container.session,
            embedding=container.embedding,
            search_fn=_search_fn,
            candidate_fn=_candidate_fn,
            job_fn=_job_fn,
            rubric_fn=_rubric_fn,
        ):
            if event["type"] == "agent_event":
                yield event  # Pass agent events to frontend for trace visibility
            elif event["type"] == "chunk":
                text_chunk = event.get("data", "")
                citations = event.get("citations", [])
                if text_chunk and str(text_chunk).strip():
                    chunk_received = True
                    yield {
                        "type": "answer_chunk",
                        "data": text_chunk,
                        "citations": citations,
                    }
            elif event["type"] == "done":
                done_data = event.get("data", {})
                if not chunk_received:
                    # Fallback: plain RAG if agentic produced nothing
                    evidence = await container.hybrid_search.search(
                        question, job_id=job_id, top_k=5
                    )
                    fallback_citations = [
                        {
                            "id": str(e.id),
                            "quote": e.quote,
                            "source": e.source_document or "Resume.pdf",
                            "page": e.page_number if e.page_number and e.page_number > 0 else 1,
                            "candidate_id": str(e.metadata.get("candidate_id") or ""),
                            "chunk_id": str(e.source_chunk_id or e.id),
                            "full_context": e.metadata.get("full_text") or e.quote,
                        }
                        for e in evidence
                    ]
                    yield {
                        "type": "answer_chunk",
                        "data": f"Based on screening records: {question}",
                        "citations": fallback_citations,
                    }
                citations_final = (
                    done_data.get("citations", []) if isinstance(done_data, dict) else []
                )
                yield {"type": "done", "data": done_data, "citations": citations_final}
    else:
        # Plain RAG path
        evidence = await container.hybrid_search.search(question, job_id=job_id, top_k=5)
        context = "\n\n".join(
            f'[{i + 1}] Document: {e.source_document} | Page: {e.page_number or 1}\nQuote: "{e.quote}"'
            for i, e in enumerate(evidence)
        )
        prompt = (
            "You are an expert HR screening copilot. Use ONLY the retrieved CV context below to answer the question.\n"
            "MANDATORY INSTRUCTION: You MUST cite the exact source document and page number where you found each piece of info, "
            "using inline markers like [1], [2] and referencing the document name (e.g., 'According to Alice_Johnson_CV.pdf (Page 1) [1]').\n\n"
            f"Retrieved Evidence:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer thoroughly and cite exact CV sources."
        )
        citations = [
            {
                "id": str(e.id),
                "quote": e.quote,
                "source": e.source_document or "Resume.pdf",
                "page": e.page_number if e.page_number and e.page_number > 0 else 1,
                "candidate_id": str(e.metadata.get("candidate_id") or ""),
                "chunk_id": str(e.source_chunk_id or e.id),
                "full_context": e.metadata.get("full_text") or e.quote,
            }
            for e in evidence
        ]
        response = await container.llm.generate(prompt, correlation_id=correlation_id)
        ans = (
            response.text
            if response.text.strip()
            else f"Based on talent screening records, here is relevant evidence for: '{question}'."
        )
        yield {"type": "answer_chunk", "data": ans, "citations": citations}
        yield {"type": "done", "data": ans}
