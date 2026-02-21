"""
Interviewer Pipeline — The Interviewer (Phase 2 orchestrator).

Converts patient free-text narrative + optional images
into a structured InterviewResult with cluster-tagged symptoms.

Usage:
    from nlp.interviewer.pipeline import run_interviewer
    result = run_interviewer(
        patient_id="P001",
        symptom_text="I have had severe joint pain in both knees for 8 months...",
        image_paths=["/path/to/rash.jpg"],
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from nlp.shared.schemas import Cluster, InterviewResult, SymptomEntity
from nlp.shared.thought_stream import ThoughtStream
from nlp.interviewer.ner_pipeline import extract_entities, _get_default_pipeline
from nlp.interviewer.cluster_mapper import tag_cluster_signal, link_snomed
from nlp.interviewer.relation_extractor import extract_relations
from nlp.interviewer.temporal_normalizer import normalize_duration, normalize_date
from nlp.interviewer.vision_translator import image_to_clinical_keywords, video_to_clinical_keywords

logger = logging.getLogger(__name__)


def run_interviewer(
    patient_id: str,
    symptom_text: str,
    image_paths: Optional[list[str | Path]] = None,
    video_paths: Optional[list[str | Path]] = None,
) -> InterviewResult:
    """
    Full Interviewer pipeline. Returns an InterviewResult.

    Steps:
      1. NER on symptom_text
      2. Cluster signal mapping + SNOMED linking
      3. Relation extraction (symptom → location, duration, severity)
      4. Temporal normalisation
      5. Vision translation (if images/video provided)
    """
    ThoughtStream.emit(
        agent="The Interviewer",
        step="start",
        summary=f"Processing symptom narrative ({len(symptom_text)} chars) for patient {patient_id}",
        patient_id=patient_id,
    )

    nlp = _get_default_pipeline()

    # ── Step 1: NER ──────────────────────────────────────────────────────────
    raw_entities = extract_entities(symptom_text, nlp=nlp)
    disease_ents = [e for e in raw_entities if e["label"] in ("DISEASE", "CHEMICAL", "SYMPTOM", "PROBLEM")]

    # ── Step 2: Cluster mapping ───────────────────────────────────────────────
    # ── Step 3: Relation extraction ───────────────────────────────────────────
    relations = extract_relations(raw_entities, symptom_text)

    symptoms: list[SymptomEntity] = []
    for rel in relations:
        cluster, conf = tag_cluster_signal(rel.symptom)
        snomed = link_snomed(rel.symptom)

        duration_months = None
        onset           = None
        if rel.duration_text:
            duration_months = normalize_duration(rel.duration_text)
            onset           = normalize_date(rel.duration_text)

        symptoms.append(SymptomEntity(
            entity          = rel.symptom,
            location        = rel.location,
            duration_months = duration_months,
            severity        = rel.severity,
            onset           = onset,
            cluster_signal  = cluster if conf >= 0.6 else None,
            snomed_concept  = snomed,
        ))

    # Also capture entities that had no relation match
    relation_entities = {r.symptom.lower() for r in relations}
    for ent in disease_ents:
        if ent["text"].lower() not in relation_entities:
            cluster, conf = tag_cluster_signal(ent["text"])
            symptoms.append(SymptomEntity(
                entity         = ent["text"],
                cluster_signal = cluster if conf >= 0.6 else None,
            ))

    # ── Step 4: Vision keywords (Phase 6) ────────────────────────────────────
    visual_keywords: list[str] = []
    if image_paths:
        for img in image_paths:
            try:
                kws = image_to_clinical_keywords(img)
                visual_keywords.extend(kws)
            except Exception as e:
                logger.warning(f"Vision translation failed for {img}: {e}")
    if video_paths:
        for vid in video_paths:
            try:
                kws = video_to_clinical_keywords(vid)
                visual_keywords.extend(kws)
            except Exception as e:
                logger.warning(f"Video translation failed for {vid}: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    cluster_counts = {}
    for s in symptoms:
        if s.cluster_signal:
            cluster_counts[s.cluster_signal.value] = cluster_counts.get(s.cluster_signal.value, 0) + 1

    ambiguous = sum(1 for s in symptoms if s.cluster_signal is None)
    summary_parts = [f"{count} {cluster} signal(s)" for cluster, count in cluster_counts.items()]
    summary_parts.append(f"{ambiguous} ambiguous")

    ThoughtStream.emit(
        agent="The Interviewer",
        step="symptom_extraction",
        summary=(
            f"Extracted {len(symptoms)} symptoms. "
            + ", ".join(summary_parts)
            + (f". Visual keywords: {visual_keywords[:5]}" if visual_keywords else "")
        ),
        patient_id=patient_id,
    )

    return InterviewResult(
        patient_id    = patient_id,
        raw_text      = symptom_text,
        symptoms      = symptoms,
        visual_keywords = list(set(visual_keywords)),
    )
