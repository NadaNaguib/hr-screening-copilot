"""Correlation ID helpers."""
from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    cid = _correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        set_correlation_id(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)
