"""
Phase 7 backend tests: GET /results/{patient_id} endpoint.

All tests use ASGITransport — no live server required.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.session import get_or_create_session
from nlp.shared.schemas import (
    LabReport,
    BioFingerprint,
    MarkerTimeline,
    RouterOutput,
    DiseaseCandidate,
    TranslatorOutput,
    Cluster,
)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_results_returns_404_for_unknown_patient(client):
    """GET /results/{unknown_id} must return 404 when no session exists."""
    resp = await client.get("/results/no-such-patient-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_results_returns_null_fields_for_new_session(client):
    """A fresh session returns all null pipeline phase fields."""
    patient_id = "results-new-session"
    get_or_create_session(patient_id)

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["patient_id"] == patient_id
    assert data["lab_report"] is None
    assert data["interview_result"] is None
    assert data["research_result"] is None
    assert data["router_output"] is None
    assert data["translator_output"] is None


@pytest.mark.asyncio
async def test_results_returns_lab_report_after_extract(client):
    """Lab report stored in session is returned by /results."""
    patient_id = "results-lab-patient"
    session = get_or_create_session(patient_id)
    session.lab_report = LabReport(
        patient_id=patient_id,
        markers=[],
        bio_fingerprint=BioFingerprint(),
    )

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["lab_report"] is not None
    assert data["lab_report"]["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_lab_report_markers_structure(client):
    """LabReport markers list is returned with correct structure."""
    patient_id = "results-markers-patient"
    session = get_or_create_session(patient_id)
    session.lab_report = LabReport(
        patient_id=patient_id,
        markers=[
            MarkerTimeline(
                loinc_code="2093-3",
                display_name="CRP",
                values=[],
            )
        ],
        bio_fingerprint=BioFingerprint(),
    )

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    markers = data["lab_report"]["markers"]
    assert isinstance(markers, list)
    assert len(markers) == 1
    assert markers[0]["display_name"] == "CRP"


@pytest.mark.asyncio
async def test_router_output_has_disease_candidates(client):
    """RouterOutput with disease_candidates is returned intact."""
    patient_id = "results-router-patient"
    session = get_or_create_session(patient_id)
    session.router_output = RouterOutput(
        patient_id=patient_id,
        cluster=Cluster.SYSTEMIC,
        cluster_alignment_score=0.87,
        routing_recommendation="Rheumatology",
        disease_candidates=[
            DiseaseCandidate(
                disease="Systemic Lupus Erythematosus",
                disease_alignment_score=0.72,
            )
        ],
    )

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    ro = data["router_output"]
    assert ro is not None
    assert ro["cluster_alignment_score"] == pytest.approx(0.87)
    candidates = ro["disease_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["disease"] == "Systemic Lupus Erythematosus"
    assert candidates[0]["disease_alignment_score"] == pytest.approx(0.72)


@pytest.mark.asyncio
async def test_translator_output_soap_is_string(client):
    """TranslatorOutput.soap_note is returned as a plain string."""
    patient_id = "results-soap-patient"
    session = get_or_create_session(patient_id)
    session.translator_output = TranslatorOutput(
        patient_id=patient_id,
        soap_note="S: Patient reports fatigue.\nO: CRP elevated.\nA: Autoimmune pattern.\nP: Refer to rheumatology.",
        layman_compass="Your results suggest your immune system may be overactive.",
        faithfulness_score=0.91,
    )

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    to = data["translator_output"]
    assert to is not None
    assert isinstance(to["soap_note"], str)
    assert to["soap_note"].startswith("S:")


@pytest.mark.asyncio
async def test_translator_output_layman_is_string(client):
    """TranslatorOutput.layman_compass is returned as a plain string."""
    patient_id = "results-layman-patient"
    session = get_or_create_session(patient_id)
    session.translator_output = TranslatorOutput(
        patient_id=patient_id,
        soap_note="S: ...",
        layman_compass="In plain language: your inflammation markers are elevated.",
        faithfulness_score=0.88,
    )

    resp = await client.get(f"/results/{patient_id}")
    assert resp.status_code == 200

    data = resp.json()
    to = data["translator_output"]
    assert isinstance(to["layman_compass"], str)
    assert "inflammation" in to["layman_compass"]
