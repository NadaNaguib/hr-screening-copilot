"""Document parsing utilities."""
from __future__ import annotations

import hashlib
from io import BytesIO

from docx import Document as DocxDocument
from PyPDF2 import PdfReader

from copilot.domain.errors import UnparseableDocumentError


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception as exc:
        raise UnparseableDocumentError(f"Failed to parse PDF: {exc}") from exc


def parse_docx(content: bytes) -> str:
    try:
        doc = DocxDocument(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception as exc:
        raise UnparseableDocumentError(f"Failed to parse DOCX: {exc}") from exc


def parse_document(filename: str, content: bytes, mime_type: str = "") -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf") or mime_type == "application/pdf":
        return parse_pdf(content)
    if lowered.endswith(".docx") or mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return parse_docx(content)
    if lowered.endswith(".txt") or mime_type.startswith("text/"):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnparseableDocumentError(f"Failed to decode text: {exc}") from exc
    raise UnparseableDocumentError(f"Unsupported file type: {filename}")
