"""Token/cost accounting."""
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


class TokenCostLedger:
    """In-memory ledger for token/cost accounting."""

    def __init__(self) -> None:
        self.records: list[TokenCostRecord] = []

    def record(self, record: TokenCostRecord) -> None:
        self.records.append(record)

    def summary(self) -> dict[str, Any]:
        if not self.records:
            return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        return {
            "calls": len(self.records),
            "input_tokens": sum(r.input_tokens for r in self.records),
            "output_tokens": sum(r.output_tokens for r in self.records),
            "cost_usd": sum(r.cost_usd for r in self.records),
        }


_ledger = TokenCostLedger()


def get_ledger() -> TokenCostLedger:
    return _ledger
