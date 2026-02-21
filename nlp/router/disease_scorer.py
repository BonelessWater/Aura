"""
Disease Alignment Scorer — The Router, Step 4.2.

Uses zero-shot NLI (cross-encoder/nli-deberta-v3-base) to score
each candidate disease against retrieved evidence passages.

Score = mean entailment probability across top-5 passages for a disease.
This makes the score traceable to specific evidence, not a black-box output.

CPU-compatible. No fine-tuning required for hackathon scope.
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import Cluster, RetrievedPassage

logger = logging.getLogger(__name__)

NLI_MODEL = "cross-encoder/nli-deberta-v3-base"

# Candidate diseases per cluster
DISEASE_CANDIDATES: dict[Cluster, list[str]] = {
    Cluster.SYSTEMIC: [
        "Systemic Lupus Erythematosus",
        "Rheumatoid Arthritis",
        "Ankylosing Spondylitis",
        "Sjögren's Syndrome",
        "Psoriatic Arthritis",
        "Reactive Arthritis",
    ],
    Cluster.GI: [
        "Crohn's Disease",
        "Ulcerative Colitis",
        "Irritable Bowel Syndrome",
        "Celiac Disease",
    ],
    Cluster.ENDOCRINE: [
        "Hashimoto's Thyroiditis",
        "Graves' Disease",
        "Type 1 Diabetes",
        "Addison's Disease",
    ],
}

# Specialist routing per cluster
ROUTING: dict[Cluster, str] = {
    Cluster.SYSTEMIC:  "Rheumatologist",
    Cluster.GI:        "Gastroenterologist",
    Cluster.ENDOCRINE: "Endocrinologist",
}


class NLIScorer:
    """
    Wraps cross-encoder/nli-deberta-v3-base for zero-shot NLI scoring.
    """

    def __init__(self) -> None:
        self._pipe = None

    def load(self) -> None:
        if self._pipe:
            return
        try:
            from transformers import pipeline
            self._pipe = pipeline(
                "zero-shot-classification",
                model=NLI_MODEL,
                device=-1,   # CPU; set to 0 for GPU
            )
            logger.info(f"Loaded NLI scorer: {NLI_MODEL}")
        except Exception as e:
            logger.warning(f"NLI model unavailable: {e}. Scores will be 0.0.")

    def entailment_score(self, premise: str, hypothesis: str) -> float:
        """
        Return the entailment probability for (premise, hypothesis).
        Returns 0.0 if model not available.
        """
        if not self._pipe:
            return 0.0
        try:
            result = self._pipe(
                premise[:512],
                candidate_labels=[hypothesis],
                hypothesis_template="This text is consistent with {}.",
            )
            return float(result["scores"][0])
        except Exception as e:
            logger.debug(f"NLI inference error: {e}")
            return 0.0


def score_disease(
    disease:        str,
    patient_summary: str,
    passages:       list[RetrievedPassage],
    top_n:          int = 5,
) -> tuple[float, list[str]]:
    """
    Score a disease hypothesis against the top-N most relevant passages.

    Args:
        disease:         disease name string
        patient_summary: brief text summary of patient findings
        passages:        retrieved passages from RAG
        top_n:           max passages to score against

    Returns:
        (mean_entailment_score, supporting_dois)
    """
    scorer = _get_scorer()
    hypothesis = f"this patient's findings are consistent with {disease}"

    scored_passages = passages[:top_n]
    if not scored_passages:
        return 0.0, []

    scores = []
    dois   = []
    for p in scored_passages:
        # Combine patient summary + passage as the premise
        premise = f"Patient findings: {patient_summary[:200]}\n\nEvidence: {p.text[:300]}"
        score   = scorer.entailment_score(premise, hypothesis)
        scores.append(score)
        if p.doi:
            dois.append(p.doi)

    mean_score = sum(scores) / len(scores) if scores else 0.0
    return round(mean_score, 4), dois[:5]


def build_patient_summary(
    lab_report:       Optional[object] = None,
    interview_result: Optional[object] = None,
) -> str:
    """Construct a brief text summary of patient findings for NLI input."""
    parts = []
    if lab_report:
        fp = lab_report.bio_fingerprint
        if fp.sustained_abnormalities:
            parts.append(f"Sustained abnormal markers: {', '.join(fp.sustained_abnormalities)}")
        if fp.NLR:
            parts.append(f"NLR: {fp.NLR[-1].value:.2f}")
        if fp.morphological_shifts:
            parts.append(f"Morphological shifts: {', '.join(fp.morphological_shifts)}")

    if interview_result:
        top_syms = [s.entity for s in interview_result.symptoms[:5]]
        if top_syms:
            parts.append(f"Symptoms: {', '.join(top_syms)}")

    return ". ".join(parts) if parts else "Patient with autoimmune symptoms"


# ── Singleton ─────────────────────────────────────────────────────────────────

_scorer: Optional[NLIScorer] = None


def _get_scorer() -> NLIScorer:
    global _scorer
    if _scorer is None:
        _scorer = NLIScorer()
        _scorer.load()
    return _scorer
