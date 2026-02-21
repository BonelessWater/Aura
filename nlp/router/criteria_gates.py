"""
ACR/EULAR Criteria Gates — The Router, Step 4.3.

Hard-rule score caps based on published classification criteria.
These gates prevent the model from assigning high alignment scores
to diseases where the patient clearly doesn't meet diagnostic thresholds.

Outputs are routing flags, NOT diagnoses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CriteriaResult:
    disease:        str
    criteria_met:   list[str]
    criteria_count: int
    max_score_cap:  float          # 0.0–1.0 hard cap on alignment score
    cap_applied:    bool


# ── SLE — 2012 SLICC Classification Criteria ─────────────────────────────────
# ≥4/11 criteria (at least 1 clinical + 1 immunological) → can score up to 0.90
# Alternatively: biopsy-proven lupus nephritis + ANA or anti-dsDNA → 0.90

SLICC_CLINICAL = {
    "malar rash":          "Acute cutaneous lupus (malar rash)",
    "discoid rash":        "Chronic cutaneous lupus (discoid rash)",
    "photosensitivity":    "Photosensitivity",
    "oral ulcers":         "Oral ulcers / nasopharyngeal ulcers",
    "alopecia":            "Non-scarring alopecia",
    "arthritis":           "Synovitis ≥2 joints with synovitis signs",
    "pleuritis":           "Serositis (pleuritis)",
    "pericarditis":        "Serositis (pericarditis)",
    "renal":               "Renal involvement (proteinuria / casts)",
    "seizure":             "Neurological involvement (seizure)",
    "psychosis":           "Neurological involvement (psychosis)",
    "hemolytic anemia":    "Hemolytic anemia",
    "leukopenia":          "Leukopenia (<4000/mm³)",
    "thrombocytopenia":    "Thrombocytopenia (<100,000/mm³)",
}

SLICC_IMMUNOLOGICAL = {
    "ana positive":        "ANA above reference range",
    "anti-dsdna":          "Anti-dsDNA above reference range",
    "anti-sm":             "Anti-Sm",
    "antiphospholipid":    "Antiphospholipid antibody positive",
    "low complement":      "Low complement (C3, C4, or CH50)",
    "low c3":              "Low C3",
    "low c4":              "Low C4",
    "direct coombs":       "Direct Coombs test positive",
}


def apply_slicc(
    symptom_entities: list[str],
    lab_markers: dict[str, float],  # display_name → value
) -> CriteriaResult:
    """Apply 2012 SLICC SLE criteria and return cap."""
    met: list[str] = []
    entities_lower = {e.lower() for e in symptom_entities}

    for key, label in {**SLICC_CLINICAL, **SLICC_IMMUNOLOGICAL}.items():
        if key in entities_lower:
            met.append(label)
            continue
        # Lab-based criteria
        if key == "low c3" and lab_markers.get("C3", 999) < 90:
            met.append(label)
        elif key == "low c4" and lab_markers.get("C4", 999) < 16:
            met.append(label)
        elif key == "thrombocytopenia" and lab_markers.get("Platelets", 999) < 100:
            met.append(label)
        elif key == "leukopenia" and lab_markers.get("WBC", 999) < 4.0:
            met.append(label)
        elif key == "hemolytic anemia" and lab_markers.get("Hemoglobin", 999) < 10:
            met.append(label)

    n = len(met)
    if n >= 4:
        cap = 0.90
    elif n == 3:
        cap = 0.65
    elif n == 2:
        cap = 0.40
    elif n == 1:
        cap = 0.25
    else:
        cap = 0.15

    return CriteriaResult(
        disease       = "Systemic Lupus Erythematosus",
        criteria_met  = met,
        criteria_count = n,
        max_score_cap  = cap,
        cap_applied    = True,
    )


# ── RA — 2010 ACR/EULAR Classification Criteria ──────────────────────────────
# Score ≥6 → high alignment; <4 → low

def apply_acr_eular_ra(
    symptom_entities: list[str],
    lab_markers: dict[str, float],
) -> CriteriaResult:
    """Apply 2010 ACR/EULAR RA criteria."""
    score = 0
    met:  list[str] = []
    entities_lower = {e.lower() for e in symptom_entities}

    # Joint involvement (0–5 pts)
    joint_count = sum(1 for e in entities_lower if "joint" in e or "arthritis" in e)
    if joint_count >= 10:
        score += 5; met.append("≥10 joints affected")
    elif joint_count >= 4:
        score += 3; met.append("4–9 joints affected")
    elif joint_count >= 1:
        score += 2; met.append("1–3 large joints")

    # Serology (0–3 pts)
    rf   = lab_markers.get("RF", 0)
    accp = lab_markers.get("Anti-CCP", 0)
    if rf > 42 or accp > 51:   # high positive (>3× ULN approx)
        score += 3; met.append("High-positive RF or Anti-CCP")
    elif rf > 14 or accp > 17:
        score += 2; met.append("Low-positive RF or Anti-CCP")

    # Acute-phase reactants (0–1 pt)
    if lab_markers.get("CRP", 0) > 10 or lab_markers.get("ESR", 0) > 30:
        score += 1; met.append("Abnormal CRP or ESR")

    # Duration ≥6 weeks (0–1 pt) — inferred from sustained abnormality
    score += 1; met.append("Symptom duration ≥6 weeks (assumed)")

    cap = 0.90 if score >= 6 else (0.55 if score >= 4 else 0.25)
    return CriteriaResult(
        disease       = "Rheumatoid Arthritis",
        criteria_met  = met,
        criteria_count = score,
        max_score_cap  = cap,
        cap_applied    = True,
    )


# ── Sjögren's ─────────────────────────────────────────────────────────────────

def apply_sjogrens(
    symptom_entities: list[str],
    lab_markers: dict[str, float],
) -> CriteriaResult:
    met:  list[str] = []
    entities_lower = {e.lower() for e in symptom_entities}

    if "dry eyes" in entities_lower or "keratoconjunctivitis" in entities_lower:
        met.append("Keratoconjunctivitis sicca")
    if "dry mouth" in entities_lower or "xerostomia" in entities_lower:
        met.append("Xerostomia")
    if lab_markers.get("anti-Ro") or "anti-ro" in entities_lower:
        met.append("Anti-Ro (SSA) positive")
    if lab_markers.get("anti-La") or "anti-la" in entities_lower:
        met.append("Anti-La (SSB) positive")

    n   = len(met)
    cap = 0.85 if n >= 3 else (0.50 if n == 2 else 0.25)
    return CriteriaResult(
        disease       = "Sjögren's Syndrome",
        criteria_met  = met,
        criteria_count = n,
        max_score_cap  = cap,
        cap_applied    = True,
    )


# ── AS — Ankylosing Spondylitis ───────────────────────────────────────────────

def apply_as(
    symptom_entities: list[str],
    lab_markers: dict[str, float],
) -> CriteriaResult:
    met: list[str] = []
    entities_lower = {e.lower() for e in symptom_entities}

    if lab_markers.get("HLA-B27") or "hla-b27" in entities_lower:
        met.append("HLA-B27 positive")
    if "back pain" in entities_lower or "sacroiliac pain" in entities_lower:
        met.append("Inflammatory back pain")
    if "morning stiffness" in entities_lower:
        met.append("Morning stiffness ≥30 min")

    n   = len(met)
    cap = 0.85 if n >= 2 else 0.35
    return CriteriaResult(
        disease       = "Ankylosing Spondylitis",
        criteria_met  = met,
        criteria_count = n,
        max_score_cap  = cap,
        cap_applied    = True,
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

GATES: dict[str, callable] = {
    "Systemic Lupus Erythematosus": apply_slicc,
    "Rheumatoid Arthritis":          apply_acr_eular_ra,
    "Sjögren's Syndrome":            apply_sjogrens,
    "Ankylosing Spondylitis":        apply_as,
}


def apply_gate(
    disease:          str,
    raw_score:        float,
    symptom_entities: list[str],
    lab_markers:      dict[str, float],
) -> tuple[float, CriteriaResult]:
    """
    Apply the appropriate criteria gate for a disease.
    Returns (capped_score, CriteriaResult).
    If no gate exists for the disease, returns (raw_score, None-ish result).
    """
    gate_fn = GATES.get(disease)
    if not gate_fn:
        return raw_score, CriteriaResult(
            disease=disease, criteria_met=[], criteria_count=0,
            max_score_cap=1.0, cap_applied=False,
        )

    result = gate_fn(symptom_entities, lab_markers)
    capped = min(raw_score, result.max_score_cap)
    return capped, result
