"""Document parsing utilities."""
from __future__ import annotations

import hashlib
from io import BytesIO

from docx import Document as DocxDocument
from PyPDF2 import PdfReader

from copilot.domain.errors import UnparseableDocumentError

# Canonical MIME types for every format we advertise as supported in the UI.
PDF_MIME_TYPES = frozenset({"application/pdf"})

DOCX_MIME_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
        "application/vnd.ms-word.document.macroenabled.12",
        "application/vnd.ms-word.template.macroenabled.12",
        "application/msword",
        "application/vnd.ms-word",
    }
)

TEXT_MIME_PREFIXES = ("text/",)

# Lower-case extensions (including the leading dot) accepted by the platform.
PDF_EXTENSIONS = (".pdf",)
DOCX_EXTENSIONS = (".docx", ".doc")
TEXT_EXTENSIONS = (".txt", ".md", ".rtf")
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS + DOCX_EXTENSIONS + TEXT_EXTENSIONS
SUPPORTED_MIME_TYPES = PDF_MIME_TYPES | DOCX_MIME_TYPES


def normalize_mime_type(mime_type: str | None) -> str:
    """Lower-case a MIME type and strip any ``; charset=...`` parameters."""
    return (mime_type or "").split(";")[0].strip().lower()


def _extension(filename: str) -> str:
    """Return the lower-case file extension including the leading dot."""
    lowered = (filename or "").lower().strip()
    dot = lowered.rfind(".")
    return lowered[dot:] if dot != -1 else ""


def is_supported_document(filename: str, mime_type: str = "") -> bool:
    """Return True when the extension or MIME type is a format we can parse.

    Browsers frequently report generic types (``application/octet-stream``) or
    omit the MIME type entirely, so the extension is treated as authoritative
    with the MIME type as a fallback.
    """
    ext = _extension(filename)
    mime = normalize_mime_type(mime_type)
    if ext in SUPPORTED_EXTENSIONS:
        return True
    if mime in SUPPORTED_MIME_TYPES:
        return True
    return any(mime.startswith(prefix) for prefix in TEXT_MIME_PREFIXES)


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
    """Parse a document into plain text based on its extension and MIME type.

    The extension is authoritative because browsers frequently report generic
    or missing MIME types (e.g. ``application/octet-stream``); the MIME type is
    used as a fallback. Both ``.docx``/``.doc`` and ``.pdf`` are accepted.
    """
    ext = _extension(filename)
    mime = normalize_mime_type(mime_type)

    if ext in PDF_EXTENSIONS or mime in PDF_MIME_TYPES:
        return parse_pdf(content)
    if ext in DOCX_EXTENSIONS or mime in DOCX_MIME_TYPES:
        return parse_docx(content)
    if ext in TEXT_EXTENSIONS or any(mime.startswith(prefix) for prefix in TEXT_MIME_PREFIXES):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnparseableDocumentError(f"Failed to decode text: {exc}") from exc
    if mime and mime != "application/octet-stream":
        raise UnparseableDocumentError(f"Unsupported file type: {filename} ({mime})")
    raise UnparseableDocumentError(f"Unsupported file type: {filename}")
