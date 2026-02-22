"""
Phase 3 Tests: API + Formatter -- endpoint, markdown renderer.

Tests 1-5: Formatter (pure logic, uses sample report fixture).
Tests 6-10: Backend endpoint (requires running backend + Databricks + LLM).
"""

import re

import pytest

from nlp.reportagent.schemas import (
    EvidenceCitation,
    LabPanelSummary,
    MedicalResearchReport,
    QualityMetrics,
    ReportSection,
)
from nlp.shared.schemas import Cluster, DiseaseCandidate


# ---------------------------------------------------------------------------
# Shared fixture: sample report for formatter tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_report() -> MedicalResearchReport:
    """Build a minimal valid MedicalResearchReport for formatter testing."""
    return MedicalResearchReport(
        patient_id="test_fmt_001",
        generated_at="2026-02-21T12:00:00Z",
        executive_summary=(
            "This patient shows 85% Systemic cluster alignment with elevated "
            "inflammatory markers. Further specialist evaluation is recommended."
        ),
        cluster_alignment=Cluster.SYSTEMIC,
        cluster_alignment_score=0.85,
        disease_candidates=[
            DiseaseCandidate(
                disease="Systemic Lupus Erythematosus",
                disease_alignment_score=0.72,
                supporting_dois=["10.1234/sle.2024"],
                criteria_met=["ANA positive", "Low C3/C4"],
                criteria_count=2,
            ),
        ],
        highlighted_lab_panels=[
            LabPanelSummary(
                marker_name="CRP",
                latest_value=12.5,
                unit="mg/L",
                reference_range="0.0-5.0",
                flag="HIGH",
                trend="escalating",
                clinical_note="CRP is elevated, suggesting active inflammation.",
                z_score=2.1,
            ),
        ],
        bio_fingerprint_summary=(
            "NLR of 4.2 is elevated above the 3.0 threshold."
        ),
        key_findings=ReportSection(
            heading="Key Findings",
            content="Elevated NLR and CRP suggest systemic inflammation.",
            citations=[
                EvidenceCitation(
                    claim="Elevated NLR correlates with SLE flare.",
                    doi="10.1234/example.2024",
                    journal="Arthritis & Rheumatology",
                    year=2024,
                    relevance_score=0.92,
                    passage_excerpt="In a cohort of 200 patients...",
                ),
            ],
        ),
        cross_study_patterns=ReportSection(
            heading="Cross-Study Patterns",
            content="Multiple studies confirm NLR as a biomarker.",
        ),
        knowledge_gaps=ReportSection(
            heading="Knowledge Gaps",
            content="Limited data on NLR thresholds for early-stage SLE.",
        ),
        evidence_quality=ReportSection(
            heading="Evidence Quality",
            content="Most studies are retrospective with moderate sample sizes.",
        ),
        bibliography=[
            EvidenceCitation(
                claim="NLR and autoimmune disease activity.",
                doi="10.5678/nlr.2023",
                journal="Lupus",
                year=2023,
                relevance_score=0.88,
                passage_excerpt="NLR values above 3.0...",
            ),
        ],
        quality_metrics=QualityMetrics(
            retrieval_confidence=0.72,
            faithfulness_score=0.88,
            fk_grade_level=8.5,
            tool_calls_used=3,
            total_tokens=1500,
            passages_retrieved=10,
            passages_cited=6,
        ),
        methodology_note="Generated using PydanticAI report agent.",
    )


# ---------------------------------------------------------------------------
# Tests 1-5: Formatter (no external deps)
# ---------------------------------------------------------------------------

def test_formatter_imports():
    """Test 1: Formatter module imports resolve without error."""
    from nlp.reportagent.formatter import render_markdown
    assert render_markdown is not None


def test_render_markdown_produces_string(sample_report):
    """Test 2: render_markdown returns a non-empty string."""
    from nlp.reportagent.formatter import render_markdown
    md = render_markdown(sample_report)
    assert isinstance(md, str)
    assert len(md) > 100


def test_render_markdown_has_all_sections(sample_report):
    """Test 3: Output contains all 11 section headings."""
    from nlp.reportagent.formatter import render_markdown
    md = render_markdown(sample_report)

    expected_headings = [
        "## 1. Executive Summary",
        "## 2. Cluster Alignment",
        "## 3. Key Lab Panel Findings",
        "## 4. Bio-Fingerprint Analysis",
        "## 5. Key Findings",
        "## 6. Cross-Study Patterns",
        "## 7. Knowledge Gaps",
        "## 8. Evidence Quality",
        # Section 9 is conditional (demo_case_comparison)
        "## 10. Bibliography",
        "## 11. Methodology",
    ]
    for heading in expected_headings:
        assert heading in md, f"Missing section heading: {heading}"


def test_render_markdown_has_disclaimer(sample_report):
    """Test 4: Output contains disclaimer text."""
    from nlp.reportagent.formatter import render_markdown
    md = render_markdown(sample_report)
    assert "not a diagnosis" in md.lower()
    assert "qualified physician" in md.lower()


def test_render_markdown_doi_links_clickable(sample_report):
    """Test 5: DOIs rendered as clickable [doi:X](https://doi.org/X) links."""
    from nlp.reportagent.formatter import render_markdown
    md = render_markdown(sample_report)

    # Match pattern: [doi:SOME_DOI](https://doi.org/SOME_DOI)
    doi_pattern = r"\[doi:([^\]]+)\]\(https://doi\.org/\1\)"
    matches = re.findall(doi_pattern, md)
    assert len(matches) >= 1, (
        f"Expected at least 1 clickable DOI link, found {len(matches)}"
    )
    # Verify our known DOIs appear
    assert "10.1234/example.2024" in md
    assert "10.5678/nlr.2023" in md


# ---------------------------------------------------------------------------
# Tests 6-10: Backend endpoint (requires running backend + Databricks + LLM)
# ---------------------------------------------------------------------------

def test_endpoint_returns_job_id(requires_backend, requires_databricks):
    """Test 6: POST /report/{person_id} returns job_id and status: queued."""
    import httpx
    r = httpx.post("http://localhost:8000/report/harvard_08670", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["person_id"] == "harvard_08670"


def test_endpoint_requires_databricks(requires_backend):
    """Test 7: POST /report/ without Databricks returns 503.

    This test only works if the backend was started WITHOUT DATABRICKS_HOST.
    If Databricks IS available, the endpoint will succeed, so we skip.
    """
    import os
    if os.environ.get("DATABRICKS_HOST"):
        pytest.skip("Databricks is available, cannot test 503 path")

    import httpx
    r = httpx.post("http://localhost:8000/report/test_user", timeout=10)
    assert r.status_code == 503


def test_endpoint_job_reaches_terminal(requires_backend, requires_databricks, requires_llm):
    """Test 8: Poll GET /jobs/{job_id} until done or error (timeout 120s)."""
    import time
    import httpx

    # Start the report
    r = httpx.post("http://localhost:8000/report/harvard_08670", timeout=10)
    job_id = r.json()["job_id"]

    # Poll until terminal state
    deadline = time.time() + 120
    status = "queued"
    while time.time() < deadline and status not in ("done", "error"):
        time.sleep(3)
        poll = httpx.get(f"http://localhost:8000/jobs/{job_id}", timeout=10)
        status = poll.json().get("status", "unknown")

    assert status in ("done", "error"), (
        f"Job {job_id} did not reach terminal state within 120s, got: {status}"
    )


def test_endpoint_result_is_valid_report(requires_backend, requires_databricks, requires_llm):
    """Test 9: When job is done, result deserializes to MedicalResearchReport."""
    import time
    import httpx

    r = httpx.post("http://localhost:8000/report/harvard_08670", timeout=10)
    job_id = r.json()["job_id"]

    deadline = time.time() + 120
    result = None
    while time.time() < deadline:
        time.sleep(3)
        poll = httpx.get(f"http://localhost:8000/jobs/{job_id}", timeout=10)
        data = poll.json()
        if data.get("status") == "done":
            result = data.get("result")
            break
        if data.get("status") == "error":
            pytest.fail(f"Job failed: {data.get('error')}")

    assert result is not None, "Job did not complete within 120s"
    report = MedicalResearchReport.model_validate(result)
    assert report.patient_id == "harvard_08670"


def test_endpoint_sse_emits_events(requires_backend, requires_databricks, requires_llm):
    """Test 10: SSE stream emits at least 1 'Report Agent' event during generation."""
    import httpx

    # Start the report
    httpx.post("http://localhost:8000/report/harvard_08670", timeout=10)

    # Listen on SSE stream for Report Agent events
    found_event = False
    try:
        with httpx.stream(
            "GET",
            "http://localhost:8000/stream/harvard_08670",
            timeout=60,
        ) as response:
            for line in response.iter_lines():
                if "Report Agent" in line:
                    found_event = True
                    break
    except httpx.ReadTimeout:
        pass

    assert found_event, (
        "SSE stream did not emit any 'Report Agent' events during generation"
    )
