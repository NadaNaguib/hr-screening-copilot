"""Admin break-glass override with mandatory reason and audit."""

from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError, NotFoundError, ValidationError
from copilot.domain.review_task import ReviewAction
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def admin_override(
    container: Container,
    actor_id: UUID,
    role: str,
    task_id: UUID,
    reason: str,
    correlation_id: str = "",
) -> dict:
    if role != "admin":
        raise AuthorizationError("Only admin can override")
    if not reason:
        raise ValidationError("Admin override requires a mandatory reason")
    correlation_id = correlation_id or get_correlation_id()
    task = await container.review_task_repository.get_task(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")

    task.apply_action("admin", ReviewAction.ADMIN_OVERRIDE, reason=reason, actor_id=actor_id)
    await container.review_task_repository.update_task(task)
    await container.audit.log(
        action="ADMIN_OVERRIDE",
        target_type="review_task",
        target_id=str(task.id),
        actor_id=actor_id,
        actor_role="admin",
        details={"reason": reason, "to_status": task.status.value},
        correlation_id=correlation_id,
    )
    return {
        "task_id": str(task.id),
        "status": task.status.value,
        "audit_log": task.audit_log,
    }
