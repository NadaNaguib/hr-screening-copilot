"""Persist interview-probe edits and track manager modifications.

Editing probes happens through the candidate (probes live on the candidate), but
*who* edited them and *whether the content actually changed* matters for the
review workflow: a hiring manager who tweaks the probes before approving should
have the task recorded as ``edited_and_approved`` rather than a plain
``approved``. This use case keeps that rule in the application layer so both the
HTTP handler and any future caller share one implementation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from copilot.domain.errors import NotFoundError
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


def normalize_probes(probes: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Drop empty questions and normalise each probe to ``{category, question}``."""
    cleaned: list[dict[str, str]] = []
    for item in probes or []:
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        category = str(item.get("category", "technical")).strip() or "technical"
        cleaned.append({"category": category, "question": question})
    return cleaned


async def update_candidate_probes(
    container: Container,
    candidate_id: UUID,
    role: str,
    probes: list[dict[str, Any]],
    actor_id: UUID | None = None,
    correlation_id: str = "",
) -> dict:
    """Save probe edits and flag the review task when a manager changed them."""
    correlation_id = correlation_id or get_correlation_id()

    candidate = await container.candidate_repository.get_candidate(candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    cleaned = normalize_probes(probes)
    modified = cleaned != normalize_probes(candidate.interview_probes)

    candidate.set_interview_probes(cleaned)
    await container.candidate_repository.update_candidate(candidate)

    # A manager editing the probes marks the task so the next approval is
    # recorded as ``edited_and_approved``. Resolved tasks keep their decision.
    manager_modified = False
    if role == "hiring_manager" and modified:
        task = await container.review_task_repository.get_task_by_candidate(candidate_id)
        if task is not None and not task.is_resolved():
            task.probes_edited = True
            await container.review_task_repository.update_task(task)
            manager_modified = True

    await container.audit.log(
        action="update_interview_probes",
        target_type="candidate",
        target_id=str(candidate_id),
        actor_id=actor_id,
        actor_role=role,
        details={"probe_count": len(cleaned), "manager_modified": manager_modified},
        correlation_id=correlation_id,
    )

    return {
        "candidate_id": str(candidate_id),
        "probes_generated": candidate.probes_generated,
        "interview_probes": cleaned,
        "manager_modified": manager_modified,
    }
