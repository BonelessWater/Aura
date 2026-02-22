"""
Phase 0 bootstrap tests.

Verifies the backend imports, NLP schemas, ThoughtStream, and health endpoint
all work correctly before any middleware work begins.

All tests run against the real FastAPI app via ASGITransport — no mocks.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── 1. Backend imports ────────────────────────────────────────────────────────

def test_backend_imports_without_error():
    from backend.session import get_or_create_session  # noqa: F401


# ── 2. NLP schema imports ─────────────────────────────────────────────────────

def test_nlp_schemas_import():
    from nlp.shared.schemas import (  # noqa: F401
        InterviewResult,
        LabReport,
        ModerationResult,
        ResearchResult,
        RouterOutput,
        TranslatorOutput,
    )


# ── 3. ThoughtStream import ───────────────────────────────────────────────────

def test_thought_stream_import():
    from nlp.shared.thought_stream import ThoughtStream  # noqa: F401


# ── 4. ThoughtStream.emit returns event ──────────────────────────────────────

def test_thought_stream_emit_returns_event():
    from nlp.shared.thought_stream import ThoughtStream

    event = ThoughtStream.emit(agent="test", step="init", summary="ok")
    assert hasattr(event, "agent")
    assert hasattr(event, "step")
    assert hasattr(event, "summary")
    assert hasattr(event, "timestamp")
    assert event.agent == "test"
    assert event.step == "init"
    assert event.summary == "ok"


# ── 5. LabReport has markers field (not biomarkers) ──────────────────────────

def test_lab_report_has_markers_field():
    from nlp.shared.schemas import LabReport

    report = LabReport(patient_id="x")
    assert hasattr(report, "markers"), "LabReport must have 'markers', not 'biomarkers'"
    assert isinstance(report.markers, list)
    assert not hasattr(report, "biomarkers")


# ── 6. RouterOutput has disease_candidates (not conditions) ──────────────────

def test_router_output_has_disease_candidates():
    from nlp.shared.schemas import Cluster, RouterOutput

    output = RouterOutput(
        patient_id="x",
        cluster=Cluster.SYSTEMIC,
        cluster_alignment_score=0.8,
        routing_recommendation="Rheumatology",
        disease_candidates=[],
    )
    assert hasattr(output, "disease_candidates")
    assert not hasattr(output, "conditions")


# ── 7. TranslatorOutput.soap_note is a string ────────────────────────────────

def test_translator_output_soap_is_string():
    from nlp.shared.schemas import TranslatorOutput

    output = TranslatorOutput(
        patient_id="x",
        soap_note="S: ...\nO: ...\nA: ...\nP: ...",
        layman_compass="You have inflammation.",
        faithfulness_score=0.92,
    )
    assert isinstance(output.soap_note, str)


# ── 8. ModerationResult uses action enum (not flagged bool) ──────────────────

def test_moderation_result_uses_action_enum():
    from nlp.shared.schemas import ModerationAction, ModerationResult

    result = ModerationResult(
        post_id="p1",
        text="some text",
        action=ModerationAction.ALLOW,
        confidence=0.95,
    )
    assert isinstance(result.action, ModerationAction)
    assert not hasattr(result, "flagged")


# ── 9. Backend app starts and /health returns 200 ────────────────────────────

@pytest.mark.asyncio
async def test_backend_app_starts():
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ── 10. ThoughtStream patch applies (events reach session) ───────────────────

def test_thought_stream_patch_applies():
    from backend.thought_stream_patch import apply_patch
    from backend.session import _sessions, get_or_create_session
    from nlp.shared.thought_stream import ThoughtStream

    apply_patch()
    patient_id = "patch-test-001"
    get_or_create_session(patient_id)

    ThoughtStream.emit(
        agent="The Extractor",
        step="test_step",
        summary="patch works",
        patient_id=patient_id,
    )

    session = _sessions.get(patient_id)
    assert session is not None
    assert len(session.events) > 0
    last_event = session.events[-1]
    assert last_event.get("agent") == "The Extractor"
    assert last_event.get("summary") == "patch works"


# ── 11. run_extractor is callable ────────────────────────────────────────────

def test_run_extractor_callable():
    from nlp.extractor.pipeline import run_extractor

    result = run_extractor(
        patient_id="callable-test",
        pdf_paths=[],
        patient_age=40,
        patient_sex="F",
        write_to_databricks=False,
    )
    from nlp.shared.schemas import LabReport
    assert isinstance(result, LabReport)


# ── 12. run_moderator is callable ────────────────────────────────────────────

def test_run_moderator_callable():
    from nlp.moderator.pipeline import run_moderator

    result = run_moderator(
        post_id="p1",
        text="some community post text",
        log_to_delta=False,
    )
    from nlp.shared.schemas import ModerationResult
    assert isinstance(result, ModerationResult)


# ── 13. Health endpoint reads settings.vllm_base_url, not os.environ ─────────

@pytest.mark.asyncio
async def test_health_vllm_uses_settings_not_environ():
    """
    The health endpoint must report vllm status from settings.vllm_base_url
    (which reads AURA_VLLM_BASE_URL), not from the bare VLLM_BASE_URL env var.
    """
    from backend.main import app

    # Ensure the bare VLLM_BASE_URL is NOT set and AURA_VLLM_BASE_URL is NOT set.
    # The response's vllm field must match what settings.vllm_base_url resolves to.
    original_aura = os.environ.pop("AURA_VLLM_BASE_URL", None)
    os.environ.pop("VLLM_BASE_URL", None)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "vllm" in data
        # With no AURA_VLLM_BASE_URL set, vllm must be False
        assert data["vllm"] is False, (
            "Health endpoint is reporting from VLLM_BASE_URL instead of AURA_VLLM_BASE_URL. "
            "Fix: use settings.vllm_base_url in the /health endpoint."
        )
    finally:
        if original_aura is not None:
            os.environ["AURA_VLLM_BASE_URL"] = original_aura
