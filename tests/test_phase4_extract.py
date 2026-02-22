"""
Phase 4 backend tests: POST /extract endpoint.

Tests 1, 6, 7 run without an LLM.
Tests 2–5 require a configured LLM backend and are auto-skipped otherwise.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── No-LLM tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_requires_files(client):
    """POST /extract with no files must return 400."""
    resp = await client.post("/extract", data={"patient_id": "test-patient"})
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_rejects_empty_patient_id(client, sample_pdf):
    """POST /extract without patient_id form field must return 422."""
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/extract",
            files={"files": ("sample.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_file_cleanup(client, sample_pdf):
    """Temp files must be cleaned up after the request, even on 500 (no LLM)."""
    patient_id = "cleanup-test-xyz"
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/extract",
            data={"patient_id": patient_id},
            files={"files": ("sample.pdf", f, "application/pdf")},
        )
    # 200 (LLM present) or 500 (no LLM) — both must clean up
    assert resp.status_code in (200, 500)
    tmpdir = Path(tempfile.gettempdir())
    leftover = list(tmpdir.glob(f"aura_{patient_id}_*"))
    assert leftover == [], f"Temp files not cleaned up: {leftover}"


# ── LLM-required tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_accepts_pdf(client, sample_pdf, llm_available):
    """POST /extract with a real PDF must return 200 and a lab_report."""
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/extract",
            data={"patient_id": "llm-test-patient", "patient_age": "35", "patient_sex": "M"},
            files={"files": ("sample.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "lab_report" in body
    assert "patient_id" in body


@pytest.mark.asyncio
async def test_extract_lab_report_has_markers(client, sample_pdf, llm_available):
    """Extracted lab_report must have a `markers` field (list, possibly empty)."""
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/extract",
            data={"patient_id": "markers-test-patient"},
            files={"files": ("sample.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    lab_report = resp.json()["lab_report"]
    assert "markers" in lab_report
    assert isinstance(lab_report["markers"], list)


@pytest.mark.asyncio
async def test_extract_creates_session(client, sample_pdf, llm_available):
    """After /extract, the patient session must exist in the store."""
    from backend.session import get_session

    patient_id = "session-create-patient"
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/extract",
            data={"patient_id": patient_id},
            files={"files": ("sample.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    session = get_session(patient_id)
    assert session is not None
    assert session.patient_id == patient_id
    assert session.lab_report is not None


@pytest.mark.asyncio
async def test_extract_session_persists_across_calls(client, sample_pdf, llm_available):
    """Two /extract calls for the same patient_id must use the same session."""
    from backend.session import get_session

    patient_id = "persist-test-patient"

    for _ in range(2):
        with sample_pdf.open("rb") as f:
            resp = await client.post(
                "/extract",
                data={"patient_id": patient_id},
                files={"files": ("sample.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 200

    session = get_session(patient_id)
    assert session is not None
    assert session.patient_id == patient_id
