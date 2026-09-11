"""Unit tests for CV document parsing, format validation, and experience extraction."""
from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument

from copilot.application.use_cases.ensure_job_rubric import build_default_rubric
from copilot.application.use_cases.upload_candidate import _extract_years
from copilot.domain.job import Job
from copilot.infrastructure.parsing.parser import (
    is_supported_document,
    parse_document,
)

_MIMIC_CV = """CURRICULUM VITAE

FULL NAME: Alex Rivera
TARGET ROLE: Senior Python Backend Engineer (Engineering)

PROFESSIONAL SUMMARY:
Accomplished and proactive professional with 5+ years of demonstrable hands-on
experience in Python. Proven expertise in FastAPI, PostgreSQL, and Docker.

WORK EXPERIENCE:

Senior Specialist | CloudTech Solutions (2022 - Present)
- Led end-to-end technical implementation of core features.
- Mentored junior engineers and conducted peer code reviews.

Software Engineer | Innovatech Labs (2019 - 2022)
- Built high-performance backend and integration services.

EDUCATION:
- B.Sc. in Computer Science & Engineering | Tech University (2015 - 2019)
"""


def _make_docx(text: str) -> bytes:
    document = DocxDocument()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Issue 4 — document format validation
# ---------------------------------------------------------------------------
def test_is_supported_document_accepts_pdf_and_docx() -> None:
    assert is_supported_document("resume.pdf", "application/pdf")
    assert is_supported_document(
        "resume.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert is_supported_document("resume.txt", "text/plain")


def test_is_supported_document_accepts_docx_with_generic_mime() -> None:
    # Browsers frequently omit/garble the MIME type for Office documents.
    assert is_supported_document("resume.docx", "application/octet-stream")
    assert is_supported_document("resume.DOCX", "")


def test_is_supported_document_rejects_unknown_types() -> None:
    assert not is_supported_document("resume.exe", "application/x-msdownload")
    assert not is_supported_document("photo.png", "image/png")


def test_parse_document_parses_docx_content() -> None:
    content = _make_docx("Hello DOCX world")
    text = parse_document("resume.docx", content, "application/octet-stream")
    assert "Hello DOCX world" in text


def test_parse_document_parses_plain_text() -> None:
    assert parse_document("resume.txt", b"plain text body", "text/plain") == "plain text body"


# ---------------------------------------------------------------------------
# Issue 3 — experience extraction
# ---------------------------------------------------------------------------
def test_extract_years_from_explicit_statement() -> None:
    text = "Engineer with 8 years of experience building backend services."
    assert _extract_years(text) >= 8.0


def test_extract_years_handles_words_between_years_and_experience() -> None:
    # Regression: the mimic-CV phrasing previously failed the strict regex.
    text = "Professional with 5+ years of demonstrable hands-on experience in Python."
    assert _extract_years(text) >= 5.0


def test_extract_years_from_overlapping_date_ranges_deduplicates() -> None:
    years = _extract_years(_MIMIC_CV)
    assert years > 0.0
    # Union of 2019-2022 and 2022-Present must not exceed the total span.
    assert years < 20.0


# ---------------------------------------------------------------------------
# Issue 2 — default rubric provisioning
# ---------------------------------------------------------------------------
def test_build_default_rubric_includes_job_skills_as_criteria() -> None:
    job = Job(title="Backend Engineer", skills=["Python", "Docker", "PostgreSQL"])
    rubric = build_default_rubric(job)
    names = [c.name for c in rubric.criteria]
    assert "Python proficiency" in names
    assert "Docker proficiency" in names
    assert any(c.name == "Relevant experience" for c in rubric.criteria)


def test_build_default_rubric_without_skills_still_has_criteria() -> None:
    job = Job(title="Generalist", skills=[])
    rubric = build_default_rubric(job)
    assert len(rubric.criteria) >= 2
