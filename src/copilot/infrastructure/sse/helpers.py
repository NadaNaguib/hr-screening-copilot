"""Server-Sent Event helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any


async def sse_event_stream(
    iterator: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[str]:
    """Yield SSE formatted lines from an async iterator of event dicts."""
    async for event in iterator:
        yield f"data: {json.dumps(event)}\n\n"
    yield f"data: {json.dumps({'event': 'done'})}\n\n"
