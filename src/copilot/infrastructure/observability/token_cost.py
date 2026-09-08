"""Token/cost accounting and failure tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenCostRecord:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureRecord:
    provider: str
    model: str
    error: str
    correlation_id: str = ""
    timestamp: str = ""


class TokenCostLedger:
    """In-memory ledger for token/cost accounting and failure tracking."""

    def __init__(self) -> None:
        self.records: list[TokenCostRecord] = []
        self.failures: list[FailureRecord] = []

    def record(self, record: TokenCostRecord) -> None:
        self.records.append(record)

    def record_failure(self, failure: FailureRecord) -> None:
        self.failures.append(failure)

    def summary(self) -> dict[str, Any]:
        if not self.records:
            return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "models": {}}
        models: dict[str, dict[str, Any]] = {}
        for r in self.records:
            key = f"{r.provider}:{r.model}"
            entry = models.setdefault(key, {"provider": r.provider, "model": r.model, "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            entry["calls"] += 1
            entry["input_tokens"] += r.input_tokens
            entry["output_tokens"] += r.output_tokens
            entry["cost_usd"] += r.cost_usd
        return {
            "calls": len(self.records),
            "input_tokens": sum(r.input_tokens for r in self.records),
            "output_tokens": sum(r.output_tokens for r in self.records),
            "cost_usd": sum(r.cost_usd for r in self.records),
            "models": models,
        }

    def failures_summary(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "provider": f.provider,
                "model": f.model,
                "error": f.error,
                "correlation_id": f.correlation_id,
                "timestamp": f.timestamp,
            }
            for f in self.failures[-limit:]
        ]


_ledger = TokenCostLedger()


def get_ledger() -> TokenCostLedger:
    return _ledger
