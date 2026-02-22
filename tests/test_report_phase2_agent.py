"""
Phase 2 Tests: Agent -- agent definition, tools, validators, pipeline.

Tests 1-3: Agent structure (pure logic, no external deps).
Tests 4-12: Full agent integration (requires Databricks + LLM).
Test 13: Pipeline import (pure logic).
"""

import asyncio

import pytest

from nlp.reportagent.schemas import MedicalResearchReport


# ---------------------------------------------------------------------------
# Tests 1-3: Agent structure (no external deps)
# ---------------------------------------------------------------------------

def test_agent_imports():
    """Test 1: Agent module imports resolve without error."""
    from nlp.reportagent.agent import report_agent, ReportDeps
    assert report_agent is not None
    assert ReportDeps is not None


def test_agent_has_tools_registered():
    """Test 2: Agent has all 4 expected tools registered."""
    from nlp.reportagent.agent import report_agent

    tool_names = set(report_agent._function_toolset.tools.keys())
    expected = {
        "pull_additional_research",
        "get_lab_panel_detail",
        "get_demo_case_context",
        "get_population_baseline",
    }
    assert expected.issubset(tool_names), (
        f"Missing tools: {expected - tool_names}"
    )


def test_agent_has_output_validators():
    """Test 3: Agent has at least 2 output validators registered."""
    from nlp.reportagent.agent import report_agent

    assert len(report_agent._output_validators) >= 2, (
        f"Expected >= 2 output validators, got {len(report_agent._output_validators)}"
    )


# ---------------------------------------------------------------------------
# Tests 4-12: Full agent integration (requires Databricks + LLM)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def systemic_report(requires_databricks, requires_llm):
    """Generate a report for the systemic demo case (harvard_08670).

    Cached at module scope so all integration tests share a single LLM call.
    """
    from nlp.reportagent.pipeline import generate_report
    report = asyncio.get_event_loop().run_until_complete(
        generate_report("harvard_08670")
    )
    return report


@pytest.fixture(scope="module")
def healthy_report(requires_databricks, requires_llm):
    """Generate a report for the healthy demo case (nhanes_79163)."""
    from nlp.reportagent.pipeline import generate_report
    report = asyncio.get_event_loop().run_until_complete(
        generate_report("nhanes_79163")
    )
    return report


def test_report_systemic_case(systemic_report):
    """Test 4: Systemic case produces a valid MedicalResearchReport."""
    report = systemic_report
    assert isinstance(report, MedicalResearchReport)
    assert report.patient_id == "harvard_08670"
    assert report.cluster_alignment is not None


def test_report_systemic_has_lab_panels(systemic_report):
    """Test 5: Systemic case has at least 1 highlighted lab panel."""
    report = systemic_report
    assert len(report.highlighted_lab_panels) >= 1, (
        "Systemic case should highlight at least 1 lab panel"
    )


def test_report_systemic_has_citations(systemic_report):
    """Test 6: Key findings section has at least 1 DOI citation."""
    report = systemic_report
    dois = [
        c.doi
        for c in report.key_findings.citations
        if c.doi
    ]
    assert len(dois) >= 1, (
        "Key findings should have at least 1 DOI citation"
    )


def test_report_healthy_case_low_alignment(healthy_report):
    """Test 7: Healthy case has cluster_alignment_score < 0.5."""
    report = healthy_report
    assert report.cluster_alignment_score < 0.5, (
        f"Healthy case should have low alignment, got {report.cluster_alignment_score}"
    )


def test_report_no_diagnostic_language(systemic_report):
    """Test 8: Report text contains no forbidden diagnostic phrases."""
    report = systemic_report
    forbidden = [
        "patient has", "diagnosed with", "suffering from",
        "confirmed diagnosis", "definitive diagnosis",
    ]
    text_to_check = (
        report.executive_summary
        + " " + report.key_findings.content
        + " " + report.bio_fingerprint_summary
    )
    text_lower = text_to_check.lower()
    for phrase in forbidden:
        assert phrase not in text_lower, (
            f"Report contains forbidden diagnostic language: '{phrase}'"
        )


def test_report_has_bibliography(systemic_report):
    """Test 9: Report has at least 1 bibliography entry."""
    report = systemic_report
    assert len(report.bibliography) >= 1, (
        "Report should have at least 1 bibliography entry"
    )


def test_report_quality_metrics_populated(systemic_report):
    """Test 10: QualityMetrics has all fields populated."""
    qm = systemic_report.quality_metrics
    assert qm.retrieval_confidence >= 0.0
    assert qm.tool_calls_used >= 0
    assert qm.total_tokens > 0, "Token usage should be tracked"
    assert qm.passages_retrieved >= 0


def test_report_tool_call_budget_enforced(systemic_report):
    """Test 11: Agent did not exceed MAX_TOOL_CALLS (5)."""
    from nlp.reportagent.agent import MAX_TOOL_CALLS
    qm = systemic_report.quality_metrics
    assert qm.tool_calls_used <= MAX_TOOL_CALLS, (
        f"Tool calls ({qm.tool_calls_used}) exceeded budget ({MAX_TOOL_CALLS})"
    )


def test_report_executive_summary_nonempty(systemic_report):
    """Test 12: Executive summary is a non-empty string with substance."""
    report = systemic_report
    assert len(report.executive_summary) > 10, (
        f"Executive summary too short: '{report.executive_summary}'"
    )


# ---------------------------------------------------------------------------
# Test 13: Pipeline import (no external deps)
# ---------------------------------------------------------------------------

def test_pipeline_imports():
    """Test 13: Pipeline module imports resolve without error."""
    from nlp.reportagent.pipeline import generate_report
    assert generate_report is not None
    assert asyncio.iscoroutinefunction(generate_report)
