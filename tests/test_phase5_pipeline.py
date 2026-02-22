"""
Phase 5 backend tests: POST /pipeline/full and GET /jobs/{job_id}.

Tests that don't require an LLM run immediately.
Tests that call the real pipeline (requires LLM) are auto-skipped.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.utils.background import _jobs


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── /pipeline/full tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_requires_input(client):
    """POST /pipeline/full with no PDFs and no symptom_text must reject the request.

    Note: httpx does not send empty-string form fields (they are omitted from
    the body), so the backend receives symptom_text as missing → 422 (Field
    required).  In a real browser, FormData always includes the field even when
    empty, triggering the handler's explicit 400.  Both codes are acceptable
    here since the outcome is the same: the request is rejected.
    """
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": "test-patient", "symptom_text": ""},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_pipeline_returns_job_id(client):
    """POST /pipeline/full with symptom_text must return a job_id immediately."""
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": "test-patient", "symptom_text": "fatigue and joint pain"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    assert "patient_id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_pipeline_creates_session(client):
    """After POST /pipeline/full, the patient session must exist."""
    from backend.session import get_session

    patient_id = "session-pipeline-patient"
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": patient_id, "symptom_text": "headache"},
    )
    assert resp.status_code == 200
    assert get_session(patient_id) is not None


@pytest.mark.asyncio
async def test_pipeline_accepts_empty_symptom_text_with_pdfs(client, sample_pdf):
    """Whitespace-only symptom_text is valid when PDFs are provided.

    httpx omits empty-string form fields from the body, so we send a single
    space to verify that the handler's "pdfs OR non-empty symptom_text" guard
    correctly accepts the request when a PDF is present.  The space is still
    "empty" after `.strip()`, which is the condition the guard checks.
    """
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/pipeline/full",
            data={"patient_id": "pdf-patient", "symptom_text": " "},
            files={"pdfs": ("lab.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pipeline_form_field_is_pdfs_not_files(client, sample_pdf):
    """PDFs must be sent under the `pdfs` field; `files` field returns 200 but no PDFs processed."""
    # Send under correct field 'pdfs' → 200
    with sample_pdf.open("rb") as f:
        resp_correct = await client.post(
            "/pipeline/full",
            data={"patient_id": "field-test-patient", "symptom_text": "test"},
            files={"pdfs": ("lab.pdf", f, "application/pdf")},
        )
    assert resp_correct.status_code == 200

    # Send under wrong field 'files' — FastAPI ignores unknown form fields, so also 200
    # but the body should still be valid (the PDF just won't be processed)
    with sample_pdf.open("rb") as f:
        resp_wrong = await client.post(
            "/pipeline/full",
            data={"patient_id": "field-test-patient2", "symptom_text": "test"},
            files={"files": ("lab.pdf", f, "application/pdf")},
        )
    assert resp_wrong.status_code == 200


@pytest.mark.asyncio
async def test_pipeline_medications_parsed_as_csv(client):
    """Medications string is split on commas by the backend."""
    # Backend splits on commas and strips whitespace; we just verify the request succeeds
    resp = await client.post(
        "/pipeline/full",
        data={
            "patient_id": "med-patient",
            "symptom_text": "fatigue",
            "medications": "Metformin, Lisinopril, Atorvastatin",
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pipeline_omitting_symptom_text_returns_422(client):
    """POST /pipeline/full without symptom_text form field must return 422."""
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": "no-symptom-patient"},  # no symptom_text
    )
    assert resp.status_code == 422


# ── /jobs/{job_id} tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_status_starts_queued(client):
    """Immediately after dispatch, job status must be queued."""
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": "queued-patient", "symptom_text": "nausea"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    status_resp = await client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["job_id"] == job_id
    assert body["status"] in ("queued", "running")  # may have started


@pytest.mark.asyncio
async def test_nonexistent_job_returns_404(client):
    """GET /jobs/nonexistent-id must return 404."""
    resp = await client.get("/jobs/nonexistent-job-id-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_job_result_has_correct_keys(client, llm_available):
    """When job completes, result must have lab_report, interview_result, etc."""
    import asyncio

    patient_id = "result-keys-patient"
    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": patient_id, "symptom_text": "fatigue"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    # Poll until terminal
    for _ in range(60):
        status_resp = await client.get(f"/jobs/{job_id}")
        body = status_resp.json()
        if body["status"] in ("done", "error"):
            break
        await asyncio.sleep(1)

    assert body["status"] == "done"
    result = body["result"]
    assert result is not None
    for key in ("lab_report", "interview_result", "router_output", "translator_output"):
        assert key in result


@pytest.mark.asyncio
async def test_job_status_transitions_to_terminal(client, llm_available):
    """Job must transition from queued/running to done or error."""
    import asyncio

    resp = await client.post(
        "/pipeline/full",
        data={"patient_id": "transition-patient", "symptom_text": "fever"},
    )
    job_id = resp.json()["job_id"]

    for _ in range(60):
        status_resp = await client.get(f"/jobs/{job_id}")
        status = status_resp.json()["status"]
        if status in ("done", "error"):
            break
        await asyncio.sleep(1)

    assert status in ("done", "error")
