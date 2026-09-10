"""Tiered LLM Router for Task-Fit Model Allocation.

Routes tasks to the most appropriate model tier:
- FAST: Lightweight, high-throughput tasks (e.g. CV skill extraction, keyword parsing, intent classification).
  Uses high-quota models like gemini-3.1-flash-lite (500 RPD, 15 RPM) or gemini-2.5-flash-lite.
- REASONING: Complex reasoning tasks (e.g. screening criteria evaluation, rubric scoring, agentic RAG chat).
  Uses reasoning models like gemini-3.8-flash, gemini-2.5-flash, gemini-3.7-flash.
"""
from __future__ import annotations

from enum import Enum


class TaskTier(str, Enum):
    FAST = "fast"
    REASONING = "reasoning"


def get_model_for_tier(tier: TaskTier = TaskTier.REASONING) -> str:
    """Return the configured model name for a specific task tier."""
    from copilot.infrastructure.config.ai_config import AIConfigManager

    config = AIConfigManager().config
    if not config.task_routing_enabled:
        return config.gemini_model

    if tier == TaskTier.FAST:
        return config.fast_model or "gemini-3.1-flash-lite"
    return config.gemini_model or "gemini-2.5-flash"
