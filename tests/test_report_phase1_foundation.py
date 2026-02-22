"""
Phase 1 Tests: Foundation -- schemas, data hydrator, retrieval gate.

Tests 1-5: Schema validation (pure logic, no external deps).
Tests 6-10: Data hydrator (requires Databricks).
Tests 11-15: Retrieval quality gate (pure logic, no external deps).
"""

import pytest

from nlp.reportagent.schemas import (
    DemoCaseComparison,
    EvidenceCitation,
    LabPanelSummary,
    MedicalResearchReport,
    QualityMetrics,
    ReportSection,
)
from nlp.shared.schemas import (
    Cluster,
    DiseaseCandidate,
    ResearchResult,
    RetrievedPassage,
)


# ---------------------------------------------------------------------------
# Tests 1-5: Schema validation (no external deps)
# ---------------------------------------------------------------------------

def test_report_schemas_import():
    """Test 1: All report schemas resolve without ImportError."""
    from nlp.reportagent.schemas import (
        MedicalResearchReport,
        QualityMetrics,
        LabPanelSummary,
        EvidenceCitation,
        ReportSection,
        DemoCaseComparison,
    )
    assert MedicalResearchReport is not None
    assert QualityMetrics is not None


def test_medical_research_report_validates():
    """Test 2: Construct MedicalResearchReport with all required fields."""
    report = _build_sample_report()
    assert report.patient_id == "test_001"
    assert report.cluster_alignment == Cluster.SYSTEMIC
    assert report.cluster_alignment_score == 0.85
    assert len(report.disease_candidates) == 1
    assert len(report.highlighted_lab_panels) == 1
    assert report.quality_metrics.total_tokens == 1500


def test_lab_panel_summary_validates():
    """Test 3: Construct LabPanelSummary with sample data."""
    panel = LabPanelSummary(
        marker_name="CRP",
        latest_value=12.5,
        unit="mg/L",
        reference_range="0.0-5.0",
        flag="HIGH",
        trend="escalating",
        clinical_note="CRP is elevated, suggesting active inflammation.",
        z_score=2.1,
    )
    assert panel.marker_name == "CRP"
    assert panel.flag == "HIGH"
    assert panel.z_score == 2.1


def test_evidence_citation_validates():
    """Test 4: Construct EvidenceCitation with and without DOI."""
    with_doi = EvidenceCitation(
        claim="Elevated NLR correlates with SLE flare.",
        doi="10.1234/example.2024",
        journal="Arthritis & Rheumatology",
        year=2024,
        relevance_score=0.92,
        passage_excerpt="In a cohort of 200 patients...",
    )
    assert with_doi.doi == "10.1234/example.2024"

    without_doi = EvidenceCitation(
        claim="CRP elevation is a nonspecific marker.",
        relevance_score=0.65,
        passage_excerpt="CRP levels above 10 mg/L...",
    )
    assert without_doi.doi is None
    assert without_doi.relevance_score == 0.65


def test_quality_metrics_validates():
    """Test 5: Construct QualityMetrics with sample data."""
    qm = QualityMetrics(
        retrieval_confidence=0.72,
        faithfulness_score=0.88,
        fk_grade_level=8.5,
        tool_calls_used=3,
        total_tokens=2500,
        passages_retrieved=10,
        passages_cited=6,
    )
    assert qm.retrieval_confidence == 0.72
    assert qm.passages_cited <= qm.passages_retrieved
    assert qm.tool_calls_used == 3


# ---------------------------------------------------------------------------
# Tests 6-10: Data hydrator (requires Databricks)
# ---------------------------------------------------------------------------

def test_hydrate_patient_returns_bundle(requires_databricks):
    """Test 6: hydrate_patient returns a PatientBundle with non-None lab_report."""
    from nlp.reportagent.data_hydrator import hydrate_patient
    bundle = hydrate_patient("harvard_08670")
    assert bundle.patient_id == "harvard_08670"
    assert bundle.lab_report is not None


def test_hydrate_patient_has_markers(requires_databricks):
    """Test 7: Hydrated bundle has lab_report.markers with at least 1 entry."""
    from nlp.reportagent.data_hydrator import hydrate_patient
    bundle = hydrate_patient("harvard_08670")
    assert len(bundle.lab_report.markers) >= 1


def test_hydrate_patient_has_bio_fingerprint(requires_databricks):
    """Test 8: Hydrated bundle has a non-default bio_fingerprint."""
    from nlp.reportagent.data_hydrator import hydrate_patient
    bundle = hydrate_patient("harvard_08670")
    fp = bundle.lab_report.bio_fingerprint
    assert fp is not None
    # At least one ratio should be populated for a systemic case
    has_any_ratio = (
        bool(fp.NLR) or bool(fp.PLR) or bool(fp.MLR)
        or bool(fp.SII) or bool(fp.CRP_Albumin) or bool(fp.C3_C4)
    )
    assert has_any_ratio, "Bio-fingerprint should have at least one computed ratio"


def test_hydrate_patient_invalid_id_raises(requires_databricks):
    """Test 9: hydrate_patient with nonexistent ID raises RuntimeError."""
    from nlp.reportagent.data_hydrator import hydrate_patient
    with pytest.raises(RuntimeError, match="No lab data found"):
        hydrate_patient("NONEXISTENT_999")


def test_hydrate_patient_rejects_sql_injection():
    """Test 10: hydrate_patient rejects SQL injection attempts (no Databricks needed)."""
    from nlp.reportagent.data_hydrator import hydrate_patient
    with pytest.raises(ValueError, match="Invalid person_id format"):
        hydrate_patient("'; DROP TABLE--")

    with pytest.raises(ValueError, match="Invalid person_id format"):
        hydrate_patient("")

    with pytest.raises(ValueError, match="Invalid person_id format"):
        hydrate_patient("robert'; SELECT * FROM users--")


# ---------------------------------------------------------------------------
# Tests 11-15: Retrieval quality gate (no external deps)
# ---------------------------------------------------------------------------

def _make_research_result(scores: list[float]) -> ResearchResult:
    """Helper: build a ResearchResult with passages at the given scores."""
    passages = [
        RetrievedPassage(
            chunk_id=f"chunk_{i}",
            doi=f"10.1234/test.{i}",
            journal="Test Journal",
            year=2024,
            section="abstract",
            cluster_tag=None,
            text=f"Test passage content {i}.",
            score=score,
        )
        for i, score in enumerate(scores)
    ]
    return ResearchResult(
        patient_id="test_001",
        sub_queries=["test query"],
        passages=passages,
    )


def test_retrieval_gate_high_confidence():
    """Test 11: Three high-scored passages yield tier=high, action=proceed."""
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    result = _make_research_result([0.85, 0.80, 0.75])
    quality = assess_retrieval_quality(result)
    assert quality["tier"] == "high"
    assert quality["action"] == "proceed"
    assert quality["confidence"] == pytest.approx(0.80, abs=0.01)
    assert quality["passage_count"] == 3


def test_retrieval_gate_medium_confidence():
    """Test 12: Three medium-scored passages yield tier=medium, action=supplement."""
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    result = _make_research_result([0.55, 0.50, 0.45])
    quality = assess_retrieval_quality(result)
    assert quality["tier"] == "medium"
    assert quality["action"] == "supplement"
    assert quality["confidence"] == pytest.approx(0.50, abs=0.01)


def test_retrieval_gate_low_confidence():
    """Test 13: Two low-scored passages yield tier=low, action=widen_search."""
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    result = _make_research_result([0.15, 0.10])
    quality = assess_retrieval_quality(result)
    assert quality["tier"] == "low"
    assert quality["action"] == "widen_search"
    assert quality["confidence"] == pytest.approx(0.125, abs=0.01)


def test_retrieval_gate_empty_passages():
    """Test 14: Empty passage list yields confidence=0.0, action=widen_search."""
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    result = ResearchResult(
        patient_id="test_001",
        sub_queries=["test query"],
        passages=[],
    )
    quality = assess_retrieval_quality(result)
    assert quality["confidence"] == 0.0
    assert quality["tier"] == "low"
    assert quality["action"] == "widen_search"
    assert quality["passage_count"] == 0


def test_retrieval_gate_single_passage():
    """Test 15: Single passage scored 0.90 yields tier=high (average of 1)."""
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    result = _make_research_result([0.90])
    quality = assess_retrieval_quality(result)
    assert quality["tier"] == "high"
    assert quality["confidence"] == pytest.approx(0.90, abs=0.01)
    assert quality["passage_count"] == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_sample_report() -> MedicalResearchReport:
    """Build a minimal valid MedicalResearchReport for testing."""
    return MedicalResearchReport(
        patient_id="test_001",
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
            "NLR of 4.2 is elevated above the 3.0 threshold, suggesting "
            "systemic inflammatory activation."
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
            content="Multiple studies confirm NLR as a biomarker for SLE activity.",
        ),
        knowledge_gaps=ReportSection(
            heading="Knowledge Gaps",
            content="Limited data on NLR thresholds specific to early-stage SLE.",
        ),
        evidence_quality=ReportSection(
            heading="Evidence Quality",
            content="Most studies are retrospective with moderate sample sizes.",
        ),
        quality_metrics=QualityMetrics(
            retrieval_confidence=0.72,
            faithfulness_score=0.88,
            fk_grade_level=8.5,
            tool_calls_used=3,
            total_tokens=1500,
            passages_retrieved=10,
            passages_cited=6,
        ),
        methodology_note="Generated using PydanticAI report agent with MedCPT retrieval.",
    )
