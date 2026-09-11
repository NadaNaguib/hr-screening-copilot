"""Typed domain exceptions."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""

    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateCandidateError(DomainError):
    """A candidate with the same document hash already exists."""

    code = "duplicate_candidate"


class InvalidTransitionError(DomainError):
    """A review-task state transition is not allowed."""

    code = "invalid_transition"


class SLABreachError(DomainError):
    """An SLA deadline has been breached."""

    code = "sla_breach"


class UnparseableDocumentError(DomainError):
    """A document could not be parsed."""

    code = "unparseable_document"


class NotFoundError(DomainError):
    """A requested entity was not found."""

    code = "not_found"


class ConflictError(DomainError):
    """Entity already exists or conflicts with state."""

    code = "conflict"


class ValidationError(DomainError):
    """Invalid input or state transition."""

    code = "validation_error"


class AuthorizationError(DomainError):
    """The actor is not authorized for an action."""

    code = "authorization_error"


class LLMProviderError(DomainError):
    """All LLM adapters failed."""

    code = "llm_provider_error"


class PipelineError(DomainError):
    """Screening pipeline failure."""

    code = "pipeline_error"
