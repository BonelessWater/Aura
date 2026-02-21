"""
Router Pipeline — The Router (Phase 4 orchestrator).

Given patient bio-fingerprint + symptoms + retrieved passages,
computes Cluster Alignment Score and Disease Alignment Scores.

Outputs routing recommendations to a specialist — never a diagnosis.

Usage:
    from nlp.router.pipeline import run_router
    output = run_router(patient_id="P001", lab_report=lab,
                        interview_result=interview, research_result=research)
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import (
    Cluster,
    DiseaseCandidate,
    InterviewResult,
    LabReport,
    ResearchResult,
    RouterOutput,
)
from nlp.shared.thought_stream import ThoughtStream
from nlp.router.cluster_scorer import get_cluster_scorer, LABELS
from nlp.router.disease_scorer import (
    DISEASE_CANDIDATES,
    ROUTING,
    build_patient_summary,
    score_disease,
)
from nlp.router.criteria_gates import apply_gate
from nlp.router.drug_flag import check_drug_flag

logger = logging.getLogger(__name__)


def run_router(
    patient_id:       str,
    lab_report:       Optional[LabReport]       = None,
    interview_result: Optional[InterviewResult] = None,
    research_result:  Optional[ResearchResult]  = None,
    medications:      Optional[list[str]]       = None,
    patient_age:      int = 40,
    patient_sex:      str = "F",
) -> RouterOutput:
    """
    Full router pipeline. Returns a RouterOutput.

    Steps:
      1. Build feature row from lab report
      2. Cluster Alignment Score (BiomedBERT or heuristic)
      3. For each disease in top cluster: NLI disease scoring
      4. ACR/EULAR criteria gating
      5. Drug-induced flag check
    """
    ThoughtStream.emit(
        agent="The Router",
        step="start",
        summary=f"Running cluster alignment for patient {patient_id}",
        patient_id=patient_id,
    )

    # ── Step 1: Build feature row ─────────────────────────────────────────────
    feature_row = _build_feature_row(lab_report, interview_result)

    # ── Step 2: Cluster Alignment Score ──────────────────────────────────────
    scorer       = get_cluster_scorer()
    cluster_probs = scorer.predict(feature_row)

    # Incorporate symptom signal counts
    if interview_result:
        for cluster, count in interview_result.cluster_counts.items():
            if cluster in cluster_probs:
                cluster_probs[cluster] = min(
                    1.0,
                    cluster_probs[cluster] + count * 0.05
                )

    # Renormalise
    total = sum(cluster_probs.values()) or 1.0
    cluster_probs = {k: round(v / total, 4) for k, v in cluster_probs.items()}

    top_cluster_name  = max(cluster_probs, key=cluster_probs.get)
    top_cluster       = Cluster(top_cluster_name)
    top_cluster_score = cluster_probs[top_cluster_name]

    # ── Step 3: Disease Alignment Scores ─────────────────────────────────────
    passages       = research_result.passages if research_result else []
    patient_summary = build_patient_summary(lab_report, interview_result)

    symptom_entities: list[str] = []
    if interview_result:
        symptom_entities = [s.entity for s in interview_result.symptoms]

    lab_markers: dict[str, float] = {}
    if lab_report:
        for timeline in lab_report.markers:
            if timeline.values:
                lab_markers[timeline.display_name] = timeline.values[-1].value

    drug_flagged, flagged_drugs = check_drug_flag(medications or [])

    disease_candidates: list[DiseaseCandidate] = []
    for disease in DISEASE_CANDIDATES.get(top_cluster, []):
        raw_score, supporting_dois = score_disease(
            disease, patient_summary, passages
        )

        # Apply ACR/EULAR gate
        capped_score, gate_result = apply_gate(
            disease, raw_score, symptom_entities, lab_markers
        )

        disease_candidates.append(DiseaseCandidate(
            disease                = disease,
            disease_alignment_score = capped_score,
            supporting_dois        = supporting_dois,
            criteria_met           = gate_result.criteria_met,
            criteria_count         = gate_result.criteria_count,
            criteria_cap_applied   = gate_result.cap_applied and (capped_score < raw_score),
            drug_induced_flag      = drug_flagged and bool(flagged_drugs),
        ))

    # Sort by score descending
    disease_candidates.sort(key=lambda d: d.disease_alignment_score, reverse=True)

    routing = ROUTING.get(top_cluster, "Internal Medicine Specialist")

    # ── Summary ────────────────────────────────────────────────────────────────
    top_disease = disease_candidates[0] if disease_candidates else None
    summary = (
        f"{top_cluster.value} cluster: {top_cluster_score:.0%} alignment. "
        f"Primary driver: {feature_row.get('sustained_abnormalities', 'biomarker pattern')}. "
    )
    if top_disease:
        summary += (
            f"{top_disease.disease} secondary flag at "
            f"{top_disease.disease_alignment_score:.0%} — "
            f"{top_disease.criteria_count} criteria met. "
        )
    summary += f"Routing: {routing}."
    if drug_flagged:
        summary += f" Drug-induced flag: {flagged_drugs}."

    ThoughtStream.emit(
        agent="The Router",
        step="cluster_scoring",
        summary=summary,
        patient_id=patient_id,
    )

    return RouterOutput(
        patient_id              = patient_id,
        cluster                 = top_cluster,
        cluster_alignment_score = top_cluster_score,
        routing_recommendation  = routing,
        disease_candidates      = disease_candidates,
    )


def _build_feature_row(
    lab_report:       Optional[LabReport],
    interview_result: Optional[InterviewResult],
) -> dict:
    """Build the feature dict expected by the cluster scorer."""
    row: dict = {}

    if lab_report:
        fp = lab_report.bio_fingerprint
        if fp.NLR:
            row["NLR"]     = fp.NLR[-1].value
            row["NLR_flag"] = fp.NLR[-1].flag
        if fp.PLR:
            row["PLR"] = fp.PLR[-1].value
        if fp.MLR:
            row["MLR"] = fp.MLR[-1].value
        if fp.SII:
            row["SII"] = fp.SII[-1].value
        if fp.CRP_Albumin:
            row["CRP_Albumin"] = fp.CRP_Albumin[-1].value
        if fp.C3_C4:
            row["C3_C4"] = fp.C3_C4[-1].value
        row["sustained_abnormalities"] = ",".join(fp.sustained_abnormalities)
        row["morphological_shifts"]    = ",".join(fp.morphological_shifts)
        if fp.ANA_titer_trend:
            row["ANA_titer_trend"] = fp.ANA_titer_trend.value

    if interview_result:
        counts = interview_result.cluster_counts
        row["symptom_systemic_count"]  = counts.get("Systemic", 0)
        row["symptom_gi_count"]        = counts.get("Gastrointestinal", 0)
        row["symptom_endocrine_count"] = counts.get("Endocrine", 0)

    return row
