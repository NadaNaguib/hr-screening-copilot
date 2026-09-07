"""Query review queue with role-aware filters."""
from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError
from copilot.domain.review_task import ReviewStatus
from copilot.infrastructure.di import Container


async def query_review_queue(
    container: Container,
    role: str,
    job_id: UUID | None = None,
    status: list[str] | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if role not in {"admin", "hiring_manager", "hr_recruiter"}:
        raise AuthorizationError("Not authorized")

    if role == "hiring_manager":
        # Manager sees only pending manager review + approved/rejected history
        status_filter = status or [
            ReviewStatus.PENDING_MANAGER_REVIEW.value,
            ReviewStatus.APPROVED.value,
            ReviewStatus.REJECTED_BY_MANAGER.value,
            ReviewStatus.EDITED_AND_APPROVED.value,
            ReviewStatus.ESCALATED_MANAGER.value,
        ]
    elif role == "hr_recruiter":
        # Recruiter sees all tasks (Advanced Queue)
        status_filter = status
    else:
        # Admin sees all unless overridden by status param
        status_filter = status

    tasks = await container.review_task_repository.query_tasks(
        job_id=job_id,
        status=status_filter,
        role=role,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": str(t.id),
            "candidate_id": str(t.candidate_id),
            "job_id": str(t.job_id) if t.job_id else None,
            "status": t.status.value,
            "priority": t.priority,
            "triage_deadline_at": t.triage_deadline_at.isoformat() if t.triage_deadline_at else None,
            "decision_deadline_at": t.decision_deadline_at.isoformat() if t.decision_deadline_at else None,
            "triage_reason": t.triage_reason,
            "manager_comment": t.manager_comment,
            "admin_override_reason": t.admin_override_reason,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in tasks
    ]
