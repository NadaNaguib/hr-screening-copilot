"""Query review queue with role-aware filters."""

from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError
from copilot.domain.review_task import ReviewStatus, utc_iso
from copilot.infrastructure.di import Container


async def query_review_queue(
    container: Container,
    role: str,
    job_id: UUID | None = None,
    status: list[str] | None = None,
    search: str | None = None,
    priority: str | None = None,
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
        priority=priority,
        limit=limit,
        offset=offset,
    )

    candidate_map: dict[UUID, str] = {}
    job_map: dict[UUID, str] = {}
    probes_map: dict[UUID, tuple[bool, list]] = {}
    score_map: dict[UUID, float | None] = {}
    if tasks:
        all_candidates = await container.candidate_repository.list_candidates()
        candidate_map = {c.id: c.full_name for c in all_candidates}
        probes_map = {c.id: (c.probes_generated, c.interview_probes) for c in all_candidates}
        score_map = {c.id: c.overall_score for c in all_candidates}
        all_jobs = await container.document_repository.list_jobs()
        job_map = {j.id: j.title for j in all_jobs}

    return [
        {
            "id": str(t.id),
            "candidate_id": str(t.candidate_id),
            "candidate_name": candidate_map.get(t.candidate_id, "Applicant")
            if t.candidate_id
            else "Applicant",
            "job_id": str(t.job_id) if t.job_id else None,
            "job_title": job_map.get(t.job_id, "General Pool") if t.job_id else "General Pool",
            "status": t.status.value,
            "priority": t.priority,
            "overall_score": score_map.get(t.candidate_id) if t.candidate_id else None,
            "sla_phase": t.sla_phase(),
            "sla_active": t.active_sla_deadline() is not None and t.sla_frozen_at is None,
            "sla_deadline_at": utc_iso(t.active_sla_deadline()),
            "sla_resolved_at": utc_iso(t.sla_frozen_at),
            "sla_outcome": t.sla_outcome,
            "triage_deadline_at": utc_iso(t.triage_deadline_at),
            "decision_deadline_at": utc_iso(t.decision_deadline_at),
            "triage_reason": t.triage_reason,
            "manager_comment": t.manager_comment,
            "admin_override_reason": t.admin_override_reason,
            "probes_generated": (
                probes_map.get(t.candidate_id, (False, []))[0] if t.candidate_id else False
            ),
            "interview_probes": (
                probes_map.get(t.candidate_id, (False, []))[1] if t.candidate_id else []
            ),
            "created_at": utc_iso(t.created_at),
            "updated_at": utc_iso(t.updated_at),
        }
        for t in tasks
    ]
