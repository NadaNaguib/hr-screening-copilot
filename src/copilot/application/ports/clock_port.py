"""Clock port for testable time."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class ClockPort(ABC):
    """Abstract clock for testable datetime logic."""

    @abstractmethod
    def now(self) -> datetime:
        """Return current UTC datetime."""
