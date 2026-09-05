"""Hiring manager final decision actions."""
from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError, NotFoundError
from copilot.domain.review_task import ReviewAction
from copilot.infrastructure.db.models import ShortlistEntryORM, ShortlistORM
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def decide_candidate(
    container: Container,
    actor_id: UUID,
    role: str,
    task_id: UUID,
    action: str,
    reason: str | None = None,
    correlation_id: str = "",
) -> dict:
    if role not in {"hiring_manager", "admin"}:
        raise AuthorizationError("Only hiring_manager or admin can decide")
    correlation_id = correlation_id or get_correlation_id()
    task = await container.review_task_repository.get_task(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")

    review_action = ReviewAction(action)
    task.apply_action(role, review_action, reason=reason, actor_id=actor_id)
    task = await container.review_task_repository.update_task(task)

    # Gated finalize shortlist after manager approval/edit
    if review_action in (ReviewAction.APPROVE, ReviewAction.EDIT_AND_APPROVE):
        candidate = await container.candidate_repository.get_candidate(task.candidate_id)
        if candidate:
            shortlist = ShortlistORM(
                job_id=candidate.job_id,
                name=f"Shortlist entry for {candidate.full_name}",
                created_by=actor_id,
            )
            container.session.add(shortlist)
            await container.session.flush()
            await container.session.refresh(shortlist)
            entry = ShortlistEntryORM(
                shortlist_id=shortlist.id,
                candidate_id=candidate.id,
                full_name=candidate.full_name,
                email=candidate.email,
                overall_score=candidate.overall_score or 0.0,
                status=task.status.value,
                manager_comment=reason,
            )
            container.session.add(entry)
            await container.session.flush()

    await container.audit.log(
        action=f"decide_{action}",
        target_type="review_task",
        target_id=str(task.id),
        actor_id=actor_id,
        actor_role=role,
        details={"reason": reason, "to_status": task.status.value},
        correlation_id=correlation_id,
    )
    return {
        "task_id": str(task.id),
        "status": task.status.value,
        "audit_log": task.audit_log,
    }
