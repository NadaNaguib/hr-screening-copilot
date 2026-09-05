"""Dependency injection container."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from copilot.application.ports.candidate_repository_port import CandidateRepositoryPort
from copilot.application.ports.document_repository_port import DocumentRepositoryPort
from copilot.application.ports.embedding_port import EmbeddingPort
from copilot.application.ports.llm_port import LLMPort
from copilot.application.ports.review_task_repository_port import ReviewTaskRepositoryPort
from copilot.application.ports.vector_store_port import VectorStorePort
from copilot.infrastructure.providers.embedding_adapter import GeminiEmbeddingAdapter
from copilot.infrastructure.providers.fallback_policy import build_llm_provider
from copilot.infrastructure.repositories.sqlalchemy_repositories import (
    AuditLogger,
    SqlAlchemyCandidateRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyReviewTaskRepository,
    SqlAlchemyVectorStore,
)
from copilot.infrastructure.retrieval.hybrid_search import HybridSearch


@dataclass
class Container:
    session: AsyncSession
    document_repository: DocumentRepositoryPort
    candidate_repository: CandidateRepositoryPort
    review_task_repository: ReviewTaskRepositoryPort
    vector_store: VectorStorePort
    embedding: EmbeddingPort
    llm: LLMPort
    hybrid_search: HybridSearch
    audit: AuditLogger

    @classmethod
    def from_session(cls, session: AsyncSession) -> Container:
        document_repository = SqlAlchemyDocumentRepository(session)
        candidate_repository = SqlAlchemyCandidateRepository(session)
        review_task_repository = SqlAlchemyReviewTaskRepository(session)
        vector_store = SqlAlchemyVectorStore(session)
        embedding = GeminiEmbeddingAdapter()
        llm = build_llm_provider()
        hybrid_search = HybridSearch(vector_store, embedding)
        audit = AuditLogger(session)
        return cls(
            session=session,
            document_repository=document_repository,
            candidate_repository=candidate_repository,
            review_task_repository=review_task_repository,
            vector_store=vector_store,
            embedding=embedding,
            llm=llm,
            hybrid_search=hybrid_search,
            audit=audit,
        )
