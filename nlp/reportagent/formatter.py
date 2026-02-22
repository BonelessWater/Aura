"""
Render a MedicalResearchReport into presentation-ready markdown.

Follows the google/pubmed-rag 11-section template adapted for Aura
autoimmune screening.  All citations use clickable DOI links.
"""

from __future__ import annotations

import logging

from nlp.reportagent.schemas import MedicalResearchReport, ReportSection

logger = logging.getLogger(__name__)


def render_markdown(report: MedicalResearchReport) -> str:
    """Render the report as presentation-ready markdown."""
    lines: list[str] = []

    # Header
    lines.append("# Medical Research Report")
    lines.append(f"**Patient ID**: {report.patient_id}")
    lines.append(f"**Generated**: {report.generated_at}")
    lines.append(
        f"**Retrieval Confidence**: "
        f"{report.quality_metrics.retrieval_confidence:.2f}"
    )
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append(report.executive_summary)
    lines.append("")

    # 2. Cluster Alignment
    lines.append("## 2. Cluster Alignment")
    lines.append(
        f"**{report.cluster_alignment.value}** cluster at "
        f"**{report.cluster_alignment_score:.0%}** alignment."
    )
    if report.disease_candidates:
        lines.append("")
        lines.append("| Disease | Alignment | Criteria Met |")
        lines.append("|---------|-----------|-------------|")
        for dc in report.disease_candidates:
            lines.append(
                f"| {dc.disease} | {dc.disease_alignment_score:.0%} | "
                f"{dc.criteria_count} |"
            )
    lines.append("")

    # 3. Key Lab Panel Findings
    lines.append("## 3. Key Lab Panel Findings")
    for panel in report.highlighted_lab_panels:
        lines.append(f"### {panel.marker_name}")
        lines.append(
            f"- **Value**: {panel.latest_value} {panel.unit} ({panel.flag})"
        )
        lines.append(f"- **Reference Range**: {panel.reference_range}")
        if panel.trend:
            lines.append(f"- **Trend**: {panel.trend}")
        if panel.z_score is not None:
            lines.append(f"- **NHANES Z-Score**: {panel.z_score:.2f}")
        lines.append(f"- **Interpretation**: {panel.clinical_note}")
        lines.append("")

    # 4. Bio-Fingerprint Analysis
    lines.append("## 4. Bio-Fingerprint Analysis")
    lines.append(report.bio_fingerprint_summary)
    lines.append("")

    # 5-8. Research sections
    _render_section(lines, "5", report.key_findings)
    _render_section(lines, "6", report.cross_study_patterns)
    _render_section(lines, "7", report.knowledge_gaps)
    _render_section(lines, "8", report.evidence_quality)

    # 9. Reference Case Comparison
    if report.demo_case_comparison:
        dcc = report.demo_case_comparison
        lines.append("## 9. Reference Case Comparison")
        lines.append(f"**Compared to**: {dcc.case_label} (`{dcc.case_id}`)")
        lines.append("")
        lines.append(dcc.similarity_notes)
        if dcc.shared_markers:
            lines.append(
                f"- **Shared signals**: {', '.join(dcc.shared_markers)}"
            )
        if dcc.divergent_markers:
            lines.append(
                f"- **Divergent signals**: {', '.join(dcc.divergent_markers)}"
            )
        lines.append("")

    # 10. Bibliography
    if report.bibliography:
        lines.append("## 10. Bibliography")
        lines.append("")
        for i, c in enumerate(report.bibliography, 1):
            doi_link = (
                f"[doi:{c.doi}](https://doi.org/{c.doi})"
                if c.doi
                else "no DOI"
            )
            lines.append(
                f"{i}. {c.claim} -- "
                f"{c.journal or 'unknown'}, {c.year or '?'}. "
                f"{doi_link} (relevance: {c.relevance_score:.2f})"
            )
        lines.append("")

    # 11. Methodology
    lines.append("## 11. Methodology")
    lines.append(report.methodology_note)
    lines.append("")
    lines.append(
        f"*Passages retrieved: {report.quality_metrics.passages_retrieved}. "
        f"Passages cited: {report.quality_metrics.passages_cited}. "
        f"Tool calls: {report.quality_metrics.tool_calls_used}. "
        f"Tokens used: {report.quality_metrics.total_tokens}.*"
    )
    lines.append("")

    # Disclaimer
    lines.append("---")
    lines.append(f"*{report.disclaimer}*")

    return "\n".join(lines)


def _render_section(
    lines: list[str], number: str, section: ReportSection
) -> None:
    """Render a ReportSection with numbered heading and citations."""
    lines.append(f"## {number}. {section.heading}")
    lines.append(section.content)
    if section.citations:
        lines.append("")
        lines.append("**References:**")
        for c in section.citations:
            doi_link = (
                f"[doi:{c.doi}](https://doi.org/{c.doi})"
                if c.doi
                else "no DOI"
            )
            lines.append(
                f"- {c.claim} -- "
                f"{c.journal or 'unknown'}, {c.year or '?'}. "
                f"{doi_link}"
            )
    lines.append("")