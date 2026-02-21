"""
Cluster Vocabulary Mapper — The Interviewer, Step 2.

Maps extracted symptom entities to cluster signals:
  Systemic, Gastrointestinal, Endocrine

Uses a curated synonym map as the primary signal, with
optional QuickUMLS SNOMED CT linking when available.
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import Cluster

logger = logging.getLogger(__name__)

# ── Cluster vocabulary maps ───────────────────────────────────────────────────

CLUSTER_VOCABULARY: dict[Cluster, set[str]] = {
    Cluster.SYSTEMIC: {
        "fatigue", "chronic fatigue", "joint pain", "arthralgia", "arthritis",
        "malar rash", "butterfly rash", "photosensitivity", "light sensitivity",
        "raynaud", "raynaud's", "raynaud phenomenon", "pleuritis", "pleurisy",
        "morning stiffness", "oral ulcers", "mouth sores", "alopecia",
        "hair loss", "lymphadenopathy", "swollen lymph nodes",
        "fever", "low grade fever", "night sweats", "serositis",
        "pericarditis", "protein in urine", "hematuria",
        "synovitis", "muscle weakness", "myalgia", "muscle pain",
        "dry eyes", "dry mouth", "xerostomia", "keratoconjunctivitis",
        "back pain", "sacroiliac pain", "heel pain", "enthesitis",
        "psoriasis", "skin plaques", "nail pitting",
        "swollen fingers", "sausage digits", "dactylitis",
        "leukopenia", "thrombocytopenia", "hemolytic anemia",
        "anti-nuclear antibody", "ana positive", "positive ana",
    },
    Cluster.GI: {
        "abdominal pain", "abdominal cramping", "stomach pain", "belly pain",
        "bloody stool", "rectal bleeding", "blood in stool", "hematochezia",
        "bloating", "abdominal distension", "gas", "flatulence",
        "diarrhea", "frequent bowel movements", "loose stools",
        "constipation", "alternating bowel habits",
        "fecal urgency", "urgency to defecate",
        "mucus in stool", "mucus per rectum",
        "tenesmus", "rectal pressure", "incomplete evacuation",
        "nausea", "vomiting", "regurgitation",
        "heartburn", "acid reflux", "gerd",
        "difficulty swallowing", "dysphagia",
        "weight loss", "malabsorption", "nutritional deficiency",
        "perianal fistula", "perianal abscess", "anal fissure",
        "mouth ulcers", "aphthous ulcers",
        "liver disease", "elevated liver enzymes",
        "celiac", "gluten sensitivity", "wheat intolerance",
    },
    Cluster.ENDOCRINE: {
        "weight gain", "unexplained weight gain", "weight loss",
        "cold intolerance", "feeling cold", "sensitivity to cold",
        "heat intolerance", "feeling hot",
        "hair loss", "hair thinning", "brittle hair",
        "dry skin", "coarse skin",
        "polyuria", "frequent urination", "excessive urination",
        "polydipsia", "excessive thirst",
        "polyphagia", "excessive hunger",
        "brain fog", "cognitive impairment", "memory problems", "difficulty concentrating",
        "fatigue", "tiredness", "weakness",
        "tremor", "shaking hands", "palpitations", "rapid heartbeat",
        "anxiety", "nervousness", "irritability",
        "depression", "low mood",
        "neck lump", "goiter", "neck swelling",
        "irregular periods", "menstrual irregularity", "amenorrhea",
        "galactorrhea", "nipple discharge",
        "infertility", "difficulty conceiving",
        "pretibial myxedema", "skin thickening on shins",
        "acanthosis nigricans", "dark skin patches",
        "high blood sugar", "hyperglycemia",
        "low blood sugar", "hypoglycemia",
        "adrenal insufficiency", "hypotension", "low blood pressure",
    },
}

# Flatten to lookup: symptom_lower → cluster
_SYMPTOM_TO_CLUSTER: dict[str, Cluster] = {}
for _cluster, _terms in CLUSTER_VOCABULARY.items():
    for _term in _terms:
        _SYMPTOM_TO_CLUSTER[_term.lower()] = _cluster

# Ambiguous terms that could belong to multiple clusters
_AMBIGUOUS: set[str] = {"fatigue", "weight loss", "hair loss"}


def tag_cluster_signal(entity: str) -> tuple[Optional[Cluster], float]:
    """
    Map an extracted entity string to a cluster signal.

    Returns (Cluster, confidence) where confidence is:
      1.0 — exact match
      0.8 — partial match
      None — no match
    """
    e_lower = entity.lower().strip()

    # Exact match
    if e_lower in _SYMPTOM_TO_CLUSTER:
        if e_lower in _AMBIGUOUS:
            return _SYMPTOM_TO_CLUSTER[e_lower], 0.6
        return _SYMPTOM_TO_CLUSTER[e_lower], 1.0

    # Partial / substring match
    for term, cluster in _SYMPTOM_TO_CLUSTER.items():
        if term in e_lower or e_lower in term:
            return cluster, 0.8

    return None, 0.0


def count_cluster_signals(entities: list[str]) -> dict[str, int]:
    """Return counts of cluster signals across all entities."""
    counts: dict[str, int] = {c.value: 0 for c in Cluster}
    for e in entities:
        cluster, conf = tag_cluster_signal(e)
        if cluster and conf >= 0.6:
            counts[cluster.value] += 1
    return counts


# ── Optional QuickUMLS linking ────────────────────────────────────────────────

def link_snomed(entity: str) -> Optional[str]:
    """
    Attempt QuickUMLS SNOMED CT concept linking.
    Returns a SNOMED CT concept ID string, or None if unavailable.
    """
    try:
        from quickumls import QuickUMLS
        # QuickUMLS requires a local UMLS installation path
        # Set QUICKUMLS_INSTALL_PATH env var to enable
        import os
        install_path = os.environ.get("QUICKUMLS_INSTALL_PATH")
        if not install_path:
            return None

        matcher = QuickUMLS(install_path)
        matches = matcher.match(entity, best_match=True, ignore_syntax=False)
        if matches:
            top = matches[0]
            if top:
                return top[0].get("cui")
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"QuickUMLS failed for '{entity}': {e}")
    return None
