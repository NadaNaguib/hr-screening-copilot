"""APScheduler jobs for SLA breach monitoring."""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from copilot.infrastructure.db.session import async_session_factory
from copilot.infrastructure.observability.correlation import get_correlation_id, set_correlation_id


async def _check_sla_breaches(stage: str) -> None:
    set_correlation_id(f"sla-{stage}-{datetime.utcnow().isoformat()}")
    async with async_session_factory() as session:
        from copilot.infrastructure.db.models import ReviewTaskORM

        now = datetime.utcnow()
        if stage == "triage":
            result = await session.execute(
                select(ReviewTaskORM).where(
                    ReviewTaskORM.status == "pending_triage",
                    ReviewTaskORM.triage_deadline_at < now,
                )
            )
        else:
            result = await session.execute(
                select(ReviewTaskORM).where(
                    ReviewTaskORM.status == "pending_manager_review",
                    ReviewTaskORM.decision_deadline_at < now,
                )
            )
        for task in result.scalars().all():
            if stage == "triage":
                task.status = "escalated_triage"
                task.triage_escalated_at = now
            else:
                task.status = "escalated_manager"
                task.decision_escalated_at = now
            task.audit_log.append(
                {
                    "action": f"escalate_{stage}",
                    "to_status": task.status,
                    "timestamp": now.isoformat(),
                    "correlation_id": get_correlation_id(),
                }
            )
        await session.commit()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: _check_sla_breaches("triage"),
        "interval",
        minutes=5,
        id="sla_triage_check",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        lambda: _check_sla_breaches("decision"),
        "interval",
        minutes=5,
        id="sla_decision_check",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    return scheduler
