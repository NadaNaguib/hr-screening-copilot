"""Export shortlist as CSV or PDF."""
from __future__ import annotations

import csv
import io
from uuid import UUID

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from copilot.domain.errors import AuthorizationError, NotFoundError
from copilot.domain.shortlist import ShortlistFormat
from copilot.infrastructure.db.models import ShortlistORM
from copilot.infrastructure.di import Container


async def export_shortlist(
    container: Container,
    role: str,
    shortlist_id: UUID,
    format: str,
) -> tuple[bytes, str]:
    if role not in {"hiring_manager", "admin"}:
        raise AuthorizationError("Only hiring_manager or admin can export shortlists")

    shortlist = await container.session.get(ShortlistORM, shortlist_id)
    if shortlist is None:
        raise NotFoundError(f"Shortlist {shortlist_id} not found")

    entries = list(shortlist.entries)
    if format == ShortlistFormat.CSV.value:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["candidate_id", "full_name", "email", "overall_score", "status", "manager_comment"])
        for e in entries:
            writer.writerow([str(e.candidate_id), e.full_name, e.email, e.overall_score, e.status, e.manager_comment])
        return output.getvalue().encode("utf-8"), "text/csv"

    if format == ShortlistFormat.PDF.value:
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(72, 750, f"Shortlist: {shortlist.name}")
        y = 720
        for e in entries:
            line = f"{e.full_name} | {e.email} | Score: {e.overall_score} | {e.status}"
            c.drawString(72, y, line)
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        return output.getvalue(), "application/pdf"

    raise ValueError(f"Unsupported format: {format}")
