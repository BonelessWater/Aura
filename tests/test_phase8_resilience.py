"""
Phase 8 backend tests: session resilience and edge-case request handling.

All tests use ASGITransport — no live server required.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.session import get_or_create_session, get_session, evict_stale_sessions


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_eviction_after_ttl(client):
    """Sessions older than TTL are evicted and subsequent requests return 404."""
    patient_id = "eviction-test-patient"
    session = get_or_create_session(patient_id)

    # Fast-forward last_accessed to be older than the TTL
    from datetime import datetime, timedelta
    session.last_accessed = datetime.utcnow() - timedelta(seconds=3700)

    # Evict sessions with 1-hour TTL
    evict_stale_sessions(3600)

    # Session should be gone
    assert get_session(patient_id) is None

    # Results endpoint returns 404 for the evicted session
    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_sessions_isolated(client):
    """Two patient sessions do not share state."""
    id_a = "isolation-patient-a"
    id_b = "isolation-patient-b"

    session_a = get_or_create_session(id_a)
    session_b = get_or_create_session(id_b)

    from nlp.shared.schemas import LabReport, BioFingerprint

    session_a.lab_report = LabReport(
        patient_id=id_a, markers=[], bio_fingerprint=BioFingerprint()
    )
    # session_b has no lab_report

    resp_a = await client.get(f"/results/{id_a}")
    resp_b = await client.get(f"/results/{id_b}")

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    data_a = resp_a.json()
    data_b = resp_b.json()

    assert data_a["lab_report"] is not None
    assert data_b["lab_report"] is None


@pytest.mark.asyncio
async def test_session_store_empty_on_fresh_app(client):
    """
    A patient that was never created returns 404 from /results.
    Confirms the session store starts clean for unknown IDs.
    """
    resp = await client.get("/results/definitely-never-created-xyz9999")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_malformed_request_returns_422(client):
    """
    Sending a request missing required fields returns 422 Unprocessable Entity.
    Confirms FastAPI validation is active and surfaces structured errors.
    """
    # /pipeline/full requires patient_id + symptom_text at minimum
    resp = await client.post("/pipeline/full", data={})
    # Either 400 (custom validation) or 422 (FastAPI field validation)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_backend_startup_import_order(client):
    """
    A basic health check verifies the app starts without import errors
    (including the results router that was added in Phase 7).
    """
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
