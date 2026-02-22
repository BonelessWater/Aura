"""
Phase 4 Tests: Hardening -- faithfulness, FK grade, token tracking, Delta storage.

All tests require Databricks + LLM (full pipeline execution).
"""

import asyncio

import pytest

from nlp.reportagent.schemas import MedicalResearchReport
from nlp.shared.schemas import Cluster
from tests.conftest import DEMO_CASES


# ---------------------------------------------------------------------------
# Shared fixtures: generate reports for demo cases (cached at module scope)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def all_demo_reports(requires_databricks, requires_llm):
    """Generate reports for all 4 demo cases. Cached at module scope."""
    from nlp.reportagent.pipeline import generate_report

    loop = asyncio.get_event_loop()
    reports = {}
    for label, patient_id in DEMO_CASES.items():
        reports[label] = loop.run_until_complete(generate_report(patient_id))
    return reports


@pytest.fixture(scope="module")
def systemic_report(all_demo_reports):
    return all_demo_reports["systemic"]


@pytest.fixture(scope="module")
def gi_report(all_demo_reports):
    return all_demo_reports["gi"]


@pytest.fixture(scope="module")
def healthy_report(all_demo_reports):
    return all_demo_reports["healthy"]


# ---------------------------------------------------------------------------
# Tests 1-5: Quality metrics populated
# ---------------------------------------------------------------------------

def test_faithfulness_check_runs(systemic_report):
    """Test 1: Faithfulness checker ran and produced a score > 0."""
    qm = systemic_report.quality_metrics
    assert qm.faithfulness_score > 0.0, (
        f"Faithfulness score should be > 0, got {qm.faithfulness_score}"
    )


def test_fk_grade_level_computed(systemic_report):
    """Test 2: FK grade level was computed (not None)."""
    qm = systemic_report.quality_metrics
    assert qm.fk_grade_level is not None, (
        "FK grade level should be computed for executive summary"
    )


def test_fk_grade_level_within_range(systemic_report):
    """Test 3: FK grade level is between 1 and 16."""
    fk = systemic_report.quality_metrics.fk_grade_level
    assert fk is not None
    assert 1 <= fk <= 16, (
        f"FK grade level should be 1-16, got {fk}"
    )


def test_token_tracking_populated(systemic_report):
    """Test 4: total_tokens > 0 after generation."""
    qm = systemic_report.quality_metrics
    assert qm.total_tokens > 0, (
        f"Token usage should be tracked, got {qm.total_tokens}"
    )


def test_passages_cited_vs_retrieved(systemic_report):
    """Test 5: passages_cited <= passages_retrieved (logical constraint)."""
    qm = systemic_report.quality_metrics
    assert qm.passages_cited <= qm.passages_retrieved, (
        f"Cited ({qm.passages_cited}) should not exceed "
        f"retrieved ({qm.passages_retrieved})"
    )


# ---------------------------------------------------------------------------
# Test 6: Delta storage
# ---------------------------------------------------------------------------

def test_report_stored_in_delta(systemic_report, requires_databricks):
    """Test 6: After generation, report exists in aura.reports.generated."""
    from nlp.shared.databricks_client import get_client
    db = get_client()
    rows = db.run_sql(
        "SELECT patient_id FROM aura.reports.generated "
        f"WHERE patient_id = '{systemic_report.patient_id}' "
        "ORDER BY generated_at DESC LIMIT 1"
    )
    assert len(rows) >= 1, (
        f"Report for {systemic_report.patient_id} not found in Delta"
    )


# ---------------------------------------------------------------------------
# Tests 7-9: All demo cases produce valid reports with correct clusters
# ---------------------------------------------------------------------------

def test_all_demo_cases_produce_reports(all_demo_reports):
    """Test 7: All 4 demo cases produce valid MedicalResearchReport objects."""
    assert len(all_demo_reports) == 4
    for label, report in all_demo_reports.items():
        assert isinstance(report, MedicalResearchReport), (
            f"Demo case '{label}' did not produce a valid report"
        )
        assert report.patient_id == DEMO_CASES[label]


def test_gi_case_cluster_is_gi(gi_report):
    """Test 8: GI demo case has cluster_alignment == Cluster.GI."""
    assert gi_report.cluster_alignment == Cluster.GI, (
        f"GI case should align to GI cluster, got {gi_report.cluster_alignment}"
    )


def test_systemic_case_cluster_is_systemic(systemic_report):
    """Test 9: Systemic demo case has cluster_alignment == Cluster.SYSTEMIC."""
    assert systemic_report.cluster_alignment == Cluster.SYSTEMIC, (
        f"Systemic case should align to Systemic cluster, "
        f"got {systemic_report.cluster_alignment}"
    )
