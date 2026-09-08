"""Update review task priority."""
from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import NotFoundError
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id

VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


async def update_task_priority(
    container: Container,
    actor_id: UUID,
    role: str,
    task_id: UUID,
    priority: str,
    correlation_id: str = "",
) -> dict:
    correlation_id = correlation_id or get_correlation_id()
    task = await container.review_task_repository.get_task(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")

    priority_upper = priority.upper()
    if priority_upper not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")

    task.priority = priority_upper
    task = await container.review_task_repository.update_task(task)

    await container.audit.log(
        action="update_task_priority",
        target_type="review_task",
        target_id=str(task.id),
        actor_id=actor_id,
        actor_role=role,
        details={"priority": priority_upper},
        correlation_id=correlation_id,
    )

    return {
        "id": str(task.id),
        "priority": task.priority,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
