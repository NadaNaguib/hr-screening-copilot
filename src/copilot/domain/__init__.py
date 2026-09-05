"""Domain layer."""
from __future__ import annotations

from copilot.domain.candidate import Candidate, CandidateStatus
from copilot.domain.errors import (
    AuthorizationError,
    ConflictError,
    DomainError,
    LLMProviderError,
    NotFoundError,
    PipelineError,
    ValidationError,
)
from copilot.domain.evidence import Evidence, EvidenceType
from copilot.domain.review_task import ReviewAction, ReviewStatus, ReviewTask
from copilot.domain.rubric import CriterionWeight, Rubric, RubricCriterion
from copilot.domain.rubric_score import RubricScore
from copilot.domain.shortlist import Shortlist, ShortlistEntry, ShortlistFormat
from copilot.domain.sla_rule import Priority, SLARule, default_sla_rule, resolve_sla_duration
from copilot.domain.bias_rules import BiasFinding, BiasRules

__all__ = [
    "Candidate",
    "CandidateStatus",
    "AuthorizationError",
    "ConflictError",
    "DomainError",
    "LLMProviderError",
    "NotFoundError",
    "PipelineError",
    "ValidationError",
    "Evidence",
    "EvidenceType",
    "ReviewAction",
    "ReviewStatus",
    "ReviewTask",
    "CriterionWeight",
    "Rubric",
    "RubricCriterion",
    "RubricScore",
    "Shortlist",
    "ShortlistEntry",
    "ShortlistFormat",
    "Priority",
    "SLARule",
    "default_sla_rule",
    "resolve_sla_duration",
    "BiasFinding",
    "BiasRules",
]

