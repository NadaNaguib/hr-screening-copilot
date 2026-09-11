"""APScheduler jobs for SLA breach monitoring and auto-escalation.

The scheduler is a thin infrastructure driver: it opens a session, builds a
container, and delegates to the ``auto_escalate_sla`` application use case.
"""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from copilot.infrastructure.db.session import async_session_factory
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import set_correlation_id

logger = logging.getLogger(__name__)

_SCHEDULER: AsyncIOScheduler | None = None


async def run_sla_escalation() -> dict:
    """Run one SLA timeout sweep against a fresh database session."""
    from copilot.application.use_cases.auto_escalate_sla import auto_escalate_sla

    set_correlation_id(f"sla-sweep-{datetime.utcnow().isoformat()}")
    async with async_session_factory() as session:
        container = Container.from_session(session)
        try:
            result = await auto_escalate_sla(container)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("SLA escalation sweep failed")
            raise
    if result.get("forwarded") or result.get("auto_approved"):
        logger.info("SLA sweep result: %s", result)
    return result


def start_scheduler(interval_minutes: int = 5) -> AsyncIOScheduler:
    """Start (or return the running) SLA escalation scheduler."""
    global _SCHEDULER
    if _SCHEDULER is not None and _SCHEDULER.running:
        return _SCHEDULER
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_sla_escalation,
        "interval",
        minutes=interval_minutes,
        id="sla_escalation_sweep",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    _SCHEDULER = scheduler
    return scheduler


def stop_scheduler() -> None:
    """Shut the scheduler down if it is running."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        _SCHEDULER.shutdown(wait=False)
        _SCHEDULER = None

