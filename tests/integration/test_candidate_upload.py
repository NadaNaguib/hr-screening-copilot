"""Integration tests for candidate CV upload: multipart parsing & format validation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from copilot.infrastructure.auth.service import create_access_token
from copilot.presentation.dependencies import get_container
from copilot.presentation.main import app

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture(autouse=True)
def override_container():
    """Use a stub container: these requests short-circuit before ingestion runs."""

    async def _unused_container():
        return None

    app.dependency_overrides[get_container] = _unused_container
    yield
    app.dependency_overrides.pop(get_container, None)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uuid4(), 'admin')}"}


async def _upload(files: dict, data: dict | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            "/api/v1/candidates",
            data=data or {},
            files=files,
            headers=_auth_headers(),
        )


async def test_multipart_file_field_is_parsed_and_unsupported_type_rejected():
    # Regression: if the multipart body were dropped this would return "missing_file".
    response = await _upload({"file": ("resume.png", b"\x89PNG\r\n", "image/png")})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "unsupported_file_type"


async def test_upload_accepts_docx_and_then_requires_job_id():
    response = await _upload({"file": ("resume.docx", b"PK\x03\x04fake-docx", _DOCX_MIME)})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "missing_job_id"


async def test_upload_accepts_docx_with_generic_octet_stream_mime():
    response = await _upload(
        {"file": ("resume.docx", b"PK\x03\x04fake-docx", "application/octet-stream")}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "missing_job_id"


async def test_upload_accepts_pdf_and_then_requires_job_id():
    response = await _upload({"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "missing_job_id"


async def test_upload_accepts_txt_and_then_requires_job_id():
    response = await _upload({"file": ("resume.txt", b"Senior Python engineer", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "missing_job_id"


async def test_upload_accepts_alt_field_name_cv():
    # The backend tolerates common alternative multipart field names.
    response = await _upload({"cv": ("resume.txt", b"Senior Python engineer", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "missing_job_id"
