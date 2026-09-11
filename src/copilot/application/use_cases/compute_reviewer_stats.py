"""Compute reviewer statistics."""

from __future__ import annotations

from copilot.domain.errors import AuthorizationError
from copilot.domain.review_task import ReviewStatus
from copilot.infrastructure.di import Container


async def compute_reviewer_stats(container: Container, role: str) -> dict:
    if role not in {"admin", "hiring_manager", "hr_recruiter"}:
        raise AuthorizationError("Not authorized")

    tasks = await container.review_task_repository.query_tasks(role=role, limit=10000)
    total = len(tasks)
    triage_done = [
        t
        for t in tasks
        if t.status in (ReviewStatus.PENDING_MANAGER_REVIEW, ReviewStatus.REJECTED_AT_TRIAGE)
    ]
    manager_done = [
        t
        for t in tasks
        if t.status
        in (
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED_BY_MANAGER,
            ReviewStatus.EDITED_AND_APPROVED,
        )
    ]
    escalated = [
        t
        for t in tasks
        if t.status in (ReviewStatus.ESCALATED_TRIAGE, ReviewStatus.ESCALATED_MANAGER)
    ]

    return {
        "total_tasks": total,
        "triage_completed": len(triage_done),
        "triage_forwarded": len(
            [t for t in triage_done if t.status == ReviewStatus.PENDING_MANAGER_REVIEW]
        ),
        "triage_rejected": len(
            [t for t in triage_done if t.status == ReviewStatus.REJECTED_AT_TRIAGE]
        ),
        "manager_decisions": len(manager_done),
        "manager_approved": len([t for t in manager_done if t.status == ReviewStatus.APPROVED]),
        "manager_rejected": len(
            [t for t in manager_done if t.status == ReviewStatus.REJECTED_BY_MANAGER]
        ),
        "manager_edited_approved": len(
            [t for t in manager_done if t.status == ReviewStatus.EDITED_AND_APPROVED]
        ),
        "escalated": len(escalated),
    }
