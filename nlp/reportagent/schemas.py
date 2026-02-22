"""
Pydantic schemas for the agentic report generation system.

These models define the structured output of the Report Agent.
All outputs are framed as alignment scores and probability flags --
never diagnoses.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from nlp.shared.schemas import Cluster, DiseaseCandidate


class LabPanelSummary(BaseModel):
    """Agent-selected lab panel highlights."""
    marker_name:        str
    latest_value:       float
    unit:               str
    reference_range:    str                   # e.g. "3.5-5.0"
    flag:               str                   # HIGH / LOW / NORMAL
    trend:              Optional[str] = None  # stable / escalating / resolving
    clinical_note:      str                   # agent-written interpretation
    z_score:            Optional[float] = None


class EvidenceCitation(BaseModel):
    """A single research finding with provenance."""
    claim:              str
    doi:                Optional[str] = None
    journal:            Optional[str] = None
    year:               Optional[int] = None
    relevance_score:    float
    passage_excerpt:    str                   # supporting text (truncated)


class DemoCaseComparison(BaseModel):
    """Comparison to a known reference case."""
    case_id:            str
    case_label:         str                   # e.g. "Case 1: Systemic"
    similarity_notes:   str                   # agent-written comparison
    shared_markers:     list[str] = Field(default_factory=list)
    divergent_markers:  list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    """One section of the generated report."""
    heading:            str
    content:            str                   # markdown body
    citations:          list[EvidenceCitation] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    """Report quality metadata for audit trail."""
    retrieval_confidence:   float             # mean top-3 passage scores
    faithfulness_score:     float             # NLI grounding check
    fk_grade_level:         Optional[float] = None  # executive summary readability
    tool_calls_used:        int               # how many agent tool calls
    total_tokens:           int               # LLM token consumption
    passages_retrieved:     int               # total passages considered
    passages_cited:         int               # passages actually cited in report


class MedicalResearchReport(BaseModel):
    """The final agentic report output -- validated, structured, presentation-ready."""
    patient_id:                str
    generated_at:              str            # ISO 8601 timestamp

    # Core findings
    executive_summary:         str            # 2-3 sentence overview (FK grade <= 10)
    cluster_alignment:         Cluster
    cluster_alignment_score:   float
    disease_candidates:        list[DiseaseCandidate]

    # Lab analysis (agent-selected highlights)
    highlighted_lab_panels:    list[LabPanelSummary]
    bio_fingerprint_summary:   str            # agent-written narrative of key ratios

    # Research synthesis (inspired by google/pubmed-rag 11-section template)
    key_findings:              ReportSection   # findings organized by medical concept
    cross_study_patterns:      ReportSection   # patterns appearing across multiple studies
    knowledge_gaps:            ReportSection   # what the evidence does NOT cover
    evidence_quality:          ReportSection   # study types, sample sizes, journal quality

    # Comparison
    demo_case_comparison:      Optional[DemoCaseComparison] = None

    # Full bibliography
    bibliography:              list[EvidenceCitation] = Field(default_factory=list)

    # Quality and audit
    quality_metrics:           QualityMetrics

    # Legal
    disclaimer:                str = (
        "This report is a data-backed High Probability Flag for specialist referral. "
        "It is not a diagnosis. Only a qualified physician can diagnose."
    )

    # Methodology
    methodology_note:          str = ""
