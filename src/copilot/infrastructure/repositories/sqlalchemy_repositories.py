"""SQLAlchemy implementations of application repository ports."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from copilot.application.ports.candidate_repository_port import CandidateRepositoryPort
from copilot.application.ports.document_repository_port import DocumentRepositoryPort
from copilot.application.ports.review_task_repository_port import ReviewTaskRepositoryPort
from copilot.application.ports.vector_store_port import VectorStorePort
from copilot.domain.candidate import Candidate, CandidateStatus
from copilot.domain.evidence import Evidence
from copilot.domain.job import Job
from copilot.domain.review_task import ReviewStatus, ReviewTask
from copilot.domain.rubric import CriterionWeight, Rubric, RubricCriterion
from copilot.domain.rubric_score import RubricScore
from copilot.domain.sla_rule import Priority, SLARule
from copilot.infrastructure.db.models import (
    AuditEventORM,
    CandidateORM,
    ChunkORM,
    EvidenceORM,
    JobORM,
    ReviewTaskORM,
    RubricCriterionORM,
    RubricORM,
    RubricScoreORM,
    SLARuleORM,
)


def _job_to_domain(orm: JobORM) -> Job:
    return Job(
        id=orm.id,
        title=orm.title,
        department=orm.department,
        description=orm.description,
        location=orm.location,
        priority=orm.priority,
        skills=orm.skills or [],
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _job_from_domain(domain: Job) -> JobORM:
    return JobORM(
        id=domain.id,
        title=domain.title,
        department=domain.department,
        description=domain.description,
        location=domain.location,
        priority=domain.priority,
        skills=domain.skills,
        created_by=None,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def _rubric_to_domain(orm: RubricORM) -> Rubric:
    criteria = [
        RubricCriterion(
            id=c.id,
            rubric_id=c.rubric_id,
            name=c.name,
            description=c.description,
            weight=CriterionWeight(c.weight),
            required=c.required,
            keywords=c.keywords,
            min_score=c.min_score,
            max_score=c.max_score,
            created_at=c.created_at,
        )
        for c in orm.criteria
    ]
    return Rubric(
        id=orm.id,
        job_id=orm.job_id,
        name=orm.name,
        description=orm.description,
        criteria=criteria,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _rubric_from_domain(domain: Rubric) -> RubricORM:
    orm = RubricORM(
        id=domain.id,
        job_id=domain.job_id,
        name=domain.name,
        description=domain.description,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
    orm.criteria = [
        RubricCriterionORM(
            id=c.id,
            rubric_id=orm.id,
            name=c.name,
            description=c.description,
            weight=c.weight.value,
            required=c.required,
            keywords=c.keywords,
            min_score=c.min_score,
            max_score=c.max_score,
            created_at=c.created_at,
        )
        for c in domain.criteria
    ]
    return orm


def _candidate_to_domain(orm: CandidateORM) -> Candidate:
    return Candidate(
        id=orm.id,
        job_id=orm.job_id,
        full_name=orm.full_name,
        email=orm.email,
        phone=orm.phone,
        years_of_experience=orm.years_of_experience,
        skills=orm.skills,
        education=orm.education,
        work_experience=orm.work_experience,
        raw_text=orm.raw_text,
        cv_sha256=orm.cv_sha256,
        status=CandidateStatus(orm.status),
        overall_score=orm.overall_score,
        priority=orm.priority,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _candidate_from_domain(domain: Candidate) -> CandidateORM:
    return CandidateORM(
        id=domain.id,
        job_id=domain.job_id,
        full_name=domain.full_name,
        email=domain.email,
        phone=domain.phone,
        years_of_experience=domain.years_of_experience,
        skills=domain.skills,
        education=domain.education,
        work_experience=domain.work_experience,
        raw_text=domain.raw_text,
        cv_sha256=domain.cv_sha256,
        status=domain.status.value,
        overall_score=domain.overall_score,
        priority=domain.priority,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def _evidence_from_domain(domain: Evidence) -> EvidenceORM:
    return EvidenceORM(
        id=domain.id,
        candidate_id=domain.candidate_id,
        criterion_id=domain.criterion_id,
        evidence_type=domain.evidence_type.value,
        quote=domain.quote,
        source_chunk_id=domain.source_chunk_id,
        confidence=domain.confidence,
        metadata_=domain.metadata,
        created_at=domain.created_at,
    )


def _score_from_domain(domain: RubricScore) -> RubricScoreORM:
    return RubricScoreORM(
        id=domain.id,
        candidate_id=domain.candidate_id,
        criterion_id=domain.criterion_id,
        score=domain.score,
        reasoning=domain.reasoning,
        evidence_ids=[str(e) for e in domain.evidence_ids],
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def _review_task_to_domain(orm: ReviewTaskORM) -> ReviewTask:
    return ReviewTask(
        id=orm.id,
        candidate_id=orm.candidate_id,
        job_id=orm.job_id,
        status=ReviewStatus(orm.status.value),
        priority=orm.priority,
        triage_deadline_at=orm.triage_deadline_at,
        decision_deadline_at=orm.decision_deadline_at,
        triage_escalated_at=orm.triage_escalated_at,
        decision_escalated_at=orm.decision_escalated_at,
        triage_reason=orm.triage_reason,
        manager_comment=orm.manager_comment,
        admin_override_reason=orm.admin_override_reason,
        audit_log=orm.audit_log,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _review_task_from_domain(domain: ReviewTask) -> ReviewTaskORM:
    return ReviewTaskORM(
        id=domain.id,
        candidate_id=domain.candidate_id,
        job_id=domain.job_id,
        status=domain.status,
        priority=domain.priority,
        triage_deadline_at=domain.triage_deadline_at,
        decision_deadline_at=domain.decision_deadline_at,
        triage_escalated_at=domain.triage_escalated_at,
        decision_escalated_at=domain.decision_escalated_at,
        triage_reason=domain.triage_reason,
        manager_comment=domain.manager_comment,
        admin_override_reason=domain.admin_override_reason,
        audit_log=domain.audit_log,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def _sla_rule_to_domain(orm: SLARuleORM) -> SLARule:
    return SLARule(
        id=orm.id,
        job_id=orm.job_id,
        priority=Priority(orm.priority),
        triage_hours=orm.triage_hours,
        decision_hours=orm.decision_hours,
        active=orm.active,
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _sla_rule_from_domain(domain: SLARule) -> SLARuleORM:
    return SLARuleORM(
        id=domain.id,
        job_id=domain.job_id,
        priority=domain.priority.value,
        triage_hours=domain.triage_hours,
        decision_hours=domain.decision_hours,
        active=domain.active,
        created_by=domain.created_by,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


class SqlAlchemyDocumentRepository(DocumentRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, job: Job) -> Job:
        orm = _job_from_domain(job)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _job_to_domain(orm)

    async def get_job(self, job_id: UUID) -> Job | None:
        orm = await self._session.get(JobORM, job_id)
        return _job_to_domain(orm) if orm else None

    async def list_jobs(self) -> list[Job]:
        result = await self._session.execute(select(JobORM))
        return [_job_to_domain(orm) for orm in result.scalars().all()]

    async def create_rubric(self, rubric: Rubric) -> Rubric:
        orm = _rubric_from_domain(rubric)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _rubric_to_domain(orm)

    async def get_rubric_for_job(self, job_id: UUID) -> Rubric | None:
        result = await self._session.execute(
            select(RubricORM).where(RubricORM.job_id == job_id)
        )
        orm = result.scalar_one_or_none()
        return _rubric_to_domain(orm) if orm else None

    async def save_sla_rule(self, rule: SLARule) -> SLARule:
        orm = _sla_rule_from_domain(rule)
        await self._session.merge(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _sla_rule_to_domain(orm)

    async def get_sla_rule_for_job(self, job_id: UUID | None) -> SLARule | None:
        result = await self._session.execute(
            select(SLARuleORM).where(SLARuleORM.job_id == job_id, SLARuleORM.active)
        )
        orm = result.scalar_one_or_none()
        return _sla_rule_to_domain(orm) if orm else None


class SqlAlchemyCandidateRepository(CandidateRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, job_id: UUID | None, sha256: str) -> Candidate | None:
        result = await self._session.execute(
            select(CandidateORM).where(
                CandidateORM.job_id == job_id, CandidateORM.cv_sha256 == sha256
            )
        )
        orm = result.scalar_one_or_none()
        return _candidate_to_domain(orm) if orm else None

    async def create_candidate(self, candidate: Candidate) -> Candidate:
        orm = _candidate_from_domain(candidate)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _candidate_to_domain(orm)

    async def update_candidate(self, candidate: Candidate) -> Candidate:
        orm = _candidate_from_domain(candidate)
        orm = await self._session.merge(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _candidate_to_domain(orm)

    async def get_candidate(self, candidate_id: UUID) -> Candidate | None:
        orm = await self._session.get(CandidateORM, candidate_id)
        return _candidate_to_domain(orm) if orm else None

    async def list_candidates(self, job_id: UUID | None = None) -> list[Candidate]:
        stmt = select(CandidateORM)
        if job_id is not None:
            stmt = stmt.where(CandidateORM.job_id == job_id)
        result = await self._session.execute(stmt)
        return [_candidate_to_domain(orm) for orm in result.scalars().all()]

    async def add_evidence(self, candidate_id: UUID, evidence: list[Evidence]) -> None:
        for e in evidence:
            orm = _evidence_from_domain(e)
            orm.candidate_id = candidate_id
            self._session.add(orm)
        await self._session.flush()

    async def add_scores(self, candidate_id: UUID, scores: list[RubricScore]) -> None:
        for s in scores:
            orm = _score_from_domain(s)
            orm.candidate_id = candidate_id
            self._session.add(orm)
        await self._session.flush()


class SqlAlchemyReviewTaskRepository(ReviewTaskRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(self, task: ReviewTask) -> ReviewTask:
        orm = _review_task_from_domain(task)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _review_task_to_domain(orm)

    async def get_task(self, task_id: UUID) -> ReviewTask | None:
        orm = await self._session.get(ReviewTaskORM, task_id)
        return _review_task_to_domain(orm) if orm else None

    async def get_task_by_candidate(self, candidate_id: UUID) -> ReviewTask | None:
        result = await self._session.execute(
            select(ReviewTaskORM).where(ReviewTaskORM.candidate_id == candidate_id)
        )
        orm = result.scalar_one_or_none()
        return _review_task_to_domain(orm) if orm else None

    async def update_task(self, task: ReviewTask) -> ReviewTask:
        orm = _review_task_from_domain(task)
        orm = await self._session.merge(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _review_task_to_domain(orm)

    async def query_tasks(
        self,
        job_id: UUID | None = None,
        status: list[str] | None = None,
        role: str | None = None,
        assignee_id: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReviewTask]:
        stmt = select(ReviewTaskORM)
        if job_id is not None:
            stmt = stmt.where(ReviewTaskORM.job_id == job_id)
        if status:
            stmt = stmt.where(ReviewTaskORM.status.in_(status))
        stmt = stmt.order_by(ReviewTaskORM.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_review_task_to_domain(orm) for orm in result.scalars().all()]

    async def get_sla_rule_for_job(self, job_id: UUID | None) -> SLARule | None:
        result = await self._session.execute(
            select(SLARuleORM).where(SLARuleORM.job_id == job_id, SLARuleORM.active)
        )
        orm = result.scalar_one_or_none()
        return _sla_rule_to_domain(orm) if orm else None


class SqlAlchemyVectorStore(VectorStorePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ingest_chunks(
        self,
        job_id: UUID | None,
        document_id: UUID,
        chunks: list[tuple[str, int | None, dict]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        for i, (chunk_text, page, meta) in enumerate(chunks):
            orm = ChunkORM(
                document_id=document_id,
                job_id=job_id,
                text=chunk_text,
                embedding=embeddings[i] if embeddings else None,
                page_number=page,
                metadata_=meta,
            )
            self._session.add(orm)
        await self._session.flush()

    async def search(
        self,
        query_embedding: list[float],
        query_text: str,
        job_id: UUID | None = None,
        top_k: int = 10,
    ) -> list[Evidence]:
        # Vector similarity search using pgvector
        vector_str = f"[{','.join(str(v) for v in query_embedding)}]"
        sql = """
            SELECT id, document_id, job_id, text, page_number, metadata,
                   embedding <=> :embedding AS distance
            FROM chunks
            WHERE (:job_id::uuid IS NULL OR job_id = :job_id::uuid)
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """
        result = await self._session.execute(
            text(sql),
            {
                "embedding": vector_str,
                "job_id": str(job_id) if job_id else None,
                "limit": top_k,
            },
        )
        evidence_list: list[Evidence] = []
        for row in result.mappings().all():
            meta = row["metadata"] or {}
            evidence_list.append(
                Evidence(
                    id=row["id"],
                    source_chunk_id=str(row["id"]),
                    quote=row["text"],
                    source_document=meta.get("filename", ""),
                    page_number=row["page_number"],
                    confidence=max(0.0, 1.0 - float(row["distance"])),
                    metadata=meta,
                )
            )
        return evidence_list


class AuditLogger:
    """Helper to write audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        action: str,
        target_type: str,
        target_id: str,
        actor_id: UUID | None,
        actor_role: str | None,
        details: dict,
        correlation_id: str = "",
    ) -> None:
        orm = AuditEventORM(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            correlation_id=correlation_id,
        )
        self._session.add(orm)
        await self._session.flush()
