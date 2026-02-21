"""
Natural language explanation generation for individual predictions.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CaseExplanation:
    """Structured explanation for a single prediction."""

    patient_id: str
    category: str
    category_confidence: float

    # Top contributing features
    top_positive_features: List[Dict[str, Any]] = field(default_factory=list)
    top_negative_features: List[Dict[str, Any]] = field(default_factory=list)

    # Natural language
    summary: str = ""
    clinical_narrative: str = ""

    # Optional disease-level prediction
    disease: Optional[str] = None
    disease_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "category": self.category,
            "category_confidence": self.category_confidence,
            "disease": self.disease,
            "disease_confidence": self.disease_confidence,
            "top_positive_features": self.top_positive_features,
            "top_negative_features": self.top_negative_features,
            "summary": self.summary,
            "clinical_narrative": self.clinical_narrative,
        }


# Feature name to clinical description mapping
FEATURE_DESCRIPTIONS = {
    # Demographics
    "age": "patient age",
    "sex": "patient sex",
    "bmi": "BMI",

    # CBC
    "wbc": "white blood cell count",
    "rbc": "red blood cell count",
    "hemoglobin": "hemoglobin level",
    "hematocrit": "hematocrit",
    "platelet_count": "platelet count",
    "mcv": "mean corpuscular volume",
    "mch": "mean corpuscular hemoglobin",
    "rdw": "red cell distribution width",

    # Inflammatory
    "esr": "ESR (sed rate)",
    "crp": "CRP (C-reactive protein)",

    # Z-scores
    "wbc_zscore": "WBC relative to normal",
    "crp_zscore": "CRP relative to normal",
    "esr_zscore": "ESR relative to normal",
    "hemoglobin_zscore": "hemoglobin relative to normal",

    # Missingness flags
    "wbc_missing": "WBC test ordered",
    "crp_missing": "CRP test ordered",
    "esr_missing": "ESR test ordered",
    "mch_missing": "MCH test ordered",
    "hemoglobin_missing": "hemoglobin test ordered",

    # Autoantibodies
    "ana_status": "ANA status",
    "anti_dsdna": "anti-dsDNA antibody",
    "rf_status": "rheumatoid factor",
    "anti_ccp": "anti-CCP antibody",
    "c3": "complement C3",
    "c4": "complement C4",

    # GI
    "fecal_calprotectin": "fecal calprotectin",
    "crp_esr_combined": "combined inflammatory score",

    # Engineered
    "inflammatory_burden": "overall inflammatory burden",
    "autoantibody_count": "number of positive autoantibodies",
    "lab_abnormality_count": "number of abnormal lab values",
}


def get_feature_description(feature: str) -> str:
    """Get human-readable description for a feature."""
    return FEATURE_DESCRIPTIONS.get(feature, feature.replace("_", " "))


def format_feature_contribution(
    feature: str,
    value: Any,
    shap_value: float,
    direction: str = "positive"
) -> str:
    """
    Format a single feature contribution as natural language.

    Args:
        feature: Feature name
        value: Feature value
        shap_value: SHAP contribution
        direction: 'positive' (increases risk) or 'negative' (decreases risk)

    Returns:
        Human-readable string
    """
    desc = get_feature_description(feature)

    # Handle binary/missing flags
    if feature.endswith("_missing"):
        if value == 1:
            return f"{desc.replace('ordered', 'was not ordered')}"
        else:
            return f"{desc}"

    # Handle z-scores
    if feature.endswith("_zscore"):
        if value > 2:
            return f"elevated {desc}"
        elif value < -2:
            return f"low {desc}"
        elif value > 1:
            return f"slightly elevated {desc}"
        elif value < -1:
            return f"slightly low {desc}"
        else:
            return f"normal {desc}"

    # Handle regular values
    if isinstance(value, (int, float)):
        if not np.isnan(value):
            return f"{desc} of {value:.1f}"
        else:
            return f"missing {desc}"

    return f"{desc}: {value}"


def generate_explanation(
    patient_id: str,
    patient_features: pd.Series,
    shap_explanation: Dict[str, Any],
    prediction_result: Dict[str, Any],
    n_features: int = 5
) -> CaseExplanation:
    """
    Generate natural language explanation for a prediction.

    Args:
        patient_id: Patient identifier
        patient_features: Feature values for the patient
        shap_explanation: Output from get_sample_explanation()
        prediction_result: DualScoreResult as dict
        n_features: Number of top features to include

    Returns:
        CaseExplanation with natural language
    """
    category = prediction_result["category"]
    confidence = prediction_result["category_confidence"]

    # Format top features
    positive_features = []
    for feat in shap_explanation.get("top_positive_features", [])[:n_features]:
        positive_features.append({
            "feature": feat["feature"],
            "value": feat["value"],
            "shap_value": feat["shap_value"],
            "description": format_feature_contribution(
                feat["feature"], feat["value"], feat["shap_value"], "positive"
            )
        })

    negative_features = []
    for feat in shap_explanation.get("top_negative_features", [])[:n_features]:
        negative_features.append({
            "feature": feat["feature"],
            "value": feat["value"],
            "shap_value": feat["shap_value"],
            "description": format_feature_contribution(
                feat["feature"], feat["value"], feat["shap_value"], "negative"
            )
        })

    # Generate summary
    if category == "healthy":
        summary = f"Patient shows low autoimmune risk ({confidence:.0%} confidence)."
    else:
        cluster_name = category.replace("_", " ").title()
        summary = f"Patient flagged for {cluster_name} autoimmune evaluation ({confidence:.0%} confidence)."

    # Generate clinical narrative
    narrative_parts = [summary, "", "Key contributing factors:"]

    for feat in positive_features[:3]:
        narrative_parts.append(f"  - {feat['description']}")

    if negative_features:
        narrative_parts.append("")
        narrative_parts.append("Factors reducing risk:")
        for feat in negative_features[:2]:
            narrative_parts.append(f"  - {feat['description']}")

    clinical_narrative = "\n".join(narrative_parts)

    return CaseExplanation(
        patient_id=patient_id,
        category=category,
        category_confidence=confidence,
        disease=prediction_result.get("disease"),
        disease_confidence=prediction_result.get("disease_confidence"),
        top_positive_features=positive_features,
        top_negative_features=negative_features,
        summary=summary,
        clinical_narrative=clinical_narrative,
    )


def format_clinical_summary(explanation: CaseExplanation) -> str:
    """
    Format explanation as clinical summary for physician review.

    Returns:
        Formatted clinical summary string
    """
    lines = [
        "=" * 60,
        "AURA CLINICAL DECISION SUPPORT - RISK ASSESSMENT",
        "=" * 60,
        f"Patient ID: {explanation.patient_id}",
        "",
        f"PRIMARY CLASSIFICATION: {explanation.category.upper()}",
        f"Confidence: {explanation.category_confidence:.1%}",
        "",
        "SUMMARY:",
        explanation.summary,
        "",
        "KEY FINDINGS:",
    ]

    for feat in explanation.top_positive_features[:5]:
        lines.append(f"  [+] {feat['description']}")

    if explanation.top_negative_features:
        lines.append("")
        lines.append("PROTECTIVE FACTORS:")
        for feat in explanation.top_negative_features[:3]:
            lines.append(f"  [-] {feat['description']}")

    lines.extend([
        "",
        "-" * 60,
        "NOTE: This is a clinical decision support tool.",
        "All findings should be validated by a qualified physician.",
        "-" * 60,
    ])

    return "\n".join(lines)


def format_patient_summary(explanation: CaseExplanation) -> str:
    """
    Format explanation in patient-friendly language.

    For the "Layman's Compass" output.
    """
    if explanation.category == "healthy":
        intro = "Based on your lab results, you appear to have a low risk of autoimmune conditions."
    else:
        cluster_friendly = {
            "systemic": "conditions affecting multiple body systems (like lupus or rheumatoid arthritis)",
            "gastrointestinal": "conditions affecting your digestive system (like inflammatory bowel disease)",
            "endocrine": "conditions affecting your hormones (like thyroid disorders)",
        }
        condition_desc = cluster_friendly.get(
            explanation.category,
            f"{explanation.category} autoimmune conditions"
        )
        intro = f"Your results suggest you may benefit from further evaluation for {condition_desc}."

    lines = [
        "YOUR HEALTH ASSESSMENT",
        "=" * 40,
        "",
        intro,
        "",
        f"Confidence Level: {explanation.category_confidence:.0%}",
        "",
        "What this means:",
    ]

    if explanation.category == "healthy":
        lines.append("  Your lab values fall within normal ranges for most markers.")
    else:
        lines.append("  Some of your lab values show patterns that warrant attention:")
        for feat in explanation.top_positive_features[:3]:
            # Simplify for patients
            simple_desc = feat['description'].replace("relative to normal", "")
            lines.append(f"    - {simple_desc}")

    lines.extend([
        "",
        "NEXT STEPS:",
        "  - Share these results with your doctor",
        "  - Ask about any symptoms you've been experiencing",
        "  - Follow up on any recommended specialist referrals",
        "",
        "Remember: This assessment is a tool to help guide conversation",
        "with your healthcare provider, not a diagnosis.",
    ])

    return "\n".join(lines)
