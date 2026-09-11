"""Generate professional, styled PDF resumes using ReportLab."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_cv_pdf(
    full_name: str,
    cv_text: str,
    email: str = "",
    skills: list[str] | None = None,
    years_of_experience: float = 0.0,
    job_title: str = "",
) -> bytes:
    """Generate a clean, professional PDF resume from candidate data and text."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Colors
    primary_color = HexColor("#4F46E5")  # Brand indigo
    dark_color = HexColor("#1E293B")
    muted_color = HexColor("#64748B")
    border_color = HexColor("#E2E8F0")

    # Custom Styles
    name_style = ParagraphStyle(
        "CandidateName",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=dark_color,
        spaceAfter=4,
    )
    title_style = ParagraphStyle(
        "CandidateTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=primary_color,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "CandidateMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=muted_color,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=dark_color,
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=dark_color,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2,
    )
    skill_badge_style = ParagraphStyle(
        "SkillBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=primary_color,
    )

    story: list[Any] = []

    # 1. Header: Name & Role
    story.append(Paragraph(full_name, name_style))
    if job_title:
        story.append(Paragraph(job_title.upper(), title_style))
    else:
        # Try to infer title from first line of cv_text
        first_line = cv_text.strip().split("\n")[0] if cv_text else ""
        if len(first_line) < 60 and not first_line.startswith("#"):
            story.append(Paragraph(first_line, title_style))

    # Meta contacts
    meta_parts = []
    if email:
        meta_parts.append(f"Email: {email}")
    if years_of_experience > 0:
        meta_parts.append(f"Experience: {years_of_experience:.1f}+ years")
    meta_parts.append("Status: Active Verified Candidate")
    story.append(Paragraph(" &nbsp;•&nbsp; ".join(meta_parts), meta_style))
    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=2, spaceAfter=8)
    )

    # 2. Extracted Skills Grid
    candidate_skills = skills or []
    if candidate_skills:
        story.append(Paragraph("CORE COMPETENCIES & TECHNICAL SKILLS", section_heading))
        story.append(
            HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=1, spaceAfter=6)
        )
        # Format skills in a compact table (up to 4 columns)
        skill_rows = []
        cols = 4
        for i in range(0, len(candidate_skills), cols):
            chunk = candidate_skills[i : i + cols]
            row_cells = [Paragraph(f"• {sk}", skill_badge_style) for sk in chunk]
            while len(row_cells) < cols:
                row_cells.append(Paragraph("", skill_badge_style))
            skill_rows.append(row_cells)

        if skill_rows:
            col_width = (doc.width) / cols
            skill_table = Table(skill_rows, colWidths=[col_width] * cols)
            skill_table.setStyle(
                TableStyle(
                    [
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(skill_table)
            story.append(Spacer(1, 6))

    # 3. Work Experience & Full Resume Content
    story.append(Paragraph("DETAILED PROFESSIONAL EXPERIENCE & PROFILE", section_heading))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=1, spaceAfter=6)
    )

    # Parse sections from raw text
    paragraphs = cv_text.split("\n")
    for raw_p in paragraphs:
        p = raw_p.strip()
        if not p:
            continue
        # Check if header
        if re.match(r"^[A-Z\s]{4,30}:?$", p) or p.startswith("### ") or p.startswith("## "):
            clean_head = p.replace("#", "").strip()
            story.append(Spacer(1, 4))
            story.append(Paragraph(clean_head, section_heading))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=border_color, spaceBefore=1, spaceAfter=4
                )
            )
        elif p.startswith("- ") or p.startswith("• ") or p.startswith("* "):
            bullet_text = p[2:].strip()
            # Escape HTML brackets
            bullet_text = (
                bullet_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            story.append(Paragraph(f"• {bullet_text}", bullet_style))
        else:
            p_clean = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(p_clean, body_style))
            story.append(Spacer(1, 3))

    # Footer notice
    story.append(Spacer(1, 10))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=4, spaceAfter=4)
    )
    story.append(
        Paragraph(
            "HR Screening Copilot • Automated Document Intelligence & Agentic RAG • Confidential Candidate Record",
            meta_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
