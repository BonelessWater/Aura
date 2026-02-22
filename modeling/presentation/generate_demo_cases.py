"""
Generate demo case outputs for the Aura presentation.

Loads the 4 canonical demo patients from case_ids.json, runs them through
the full Dual-Scorer pipeline, and writes one JSON file per case into
demo_cases/.

Usage (from modeling/):
    python presentation/generate_demo_cases.py

Or from project root:
    python modeling/presentation/generate_demo_cases.py
"""
import sys
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Path setup ────────────────────────────────────────────────────────────────
HERE      = Path(__file__).resolve().parent
MODELING  = HERE.parent
SRC       = MODELING / "src"
OUT_DIR   = HERE / "demo_cases"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.loaders          import load_modeling_data
from data.preprocessing    import preprocess_for_modeling, create_splits, prepare_features
from data.feature_engineering import engineer_all_features
from models.dual_scorer    import DualScorer

# ── Config ────────────────────────────────────────────────────────────────────
CASE_IDS_FILE  = HERE / "demo_cases" / "case_ids.json"
MODEL_PATH     = MODELING / "outputs" / "models" / "dual_scorer"
FEATURE_GROUPS = ["demographics", "cbc", "inflammatory", "zscore", "missing"]
RANDOM_STATE   = 42

LAB_COLS = [
    "wbc", "rbc", "hemoglobin", "hematocrit",
    "platelet_count", "mcv", "mch", "rdw",
    "esr", "crp",
]
ZSCORE_COLS = [c + "_zscore" for c in LAB_COLS if (c + "_zscore") in []]  # filled below
AUTOANTIBODY_COLS = [
    "ana_status", "anti_dsdna", "hla_b27",
    "anti_sm", "anti_ro", "anti_la",
    "rf_status", "anti_ccp", "c3", "c4",
]

HEALTHY_RANGES = {
    "wbc":           (4.5,  11.0,  "×10³/µL"),
    "rbc":           (4.2,   5.4,  "×10⁶/µL"),
    "hemoglobin":    (12.0,  17.5, "g/dL"),
    "hematocrit":    (37.0,  52.0, "%"),
    "platelet_count":(150,   400,  "×10³/µL"),
    "mcv":           (80.0,  100.0,"fL"),
    "mch":           (27.0,  33.0, "pg"),
    "rdw":           (11.5,  14.5, "%"),
    "esr":           (0.0,   20.0, "mm/hr"),
    "crp":           (0.0,    1.0, "mg/dL"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def flag_lab(col: str, value: float) -> str:
    """Return H / L / N flag for a lab value."""
    if pd.isna(value):
        return "N/A"
    lo, hi, _ = HEALTHY_RANGES.get(col, (None, None, ""))
    if lo is None:
        return "?"
    if value > hi:
        return "H"
    if value < lo:
        return "L"
    return "N"


def serialize(obj):
    """JSON-safe serializer for numpy scalars."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Not serializable: {type(obj)}")


def build_lab_panel(row: pd.Series) -> dict:
    """Build structured lab panel dict from a patient row."""
    panel = {}
    for col in LAB_COLS:
        val = row.get(col, np.nan)
        zscore = row.get(col + "_zscore", np.nan)
        missing = row.get(col + "_missing", np.nan)
        lo, hi, unit = HEALTHY_RANGES.get(col, (None, None, ""))
        panel[col] = {
            "value":         None if pd.isna(val) else float(round(val, 2)),
            "unit":          unit,
            "reference_low": lo,
            "reference_high": hi,
            "flag":          flag_lab(col, val) if not pd.isna(val) else "MISSING",
            "zscore":        None if pd.isna(zscore) else float(round(zscore, 3)),
            "was_ordered":   bool(missing == 0) if not pd.isna(missing) else None,
        }
    return panel


def build_autoantibody_panel(row: pd.Series) -> dict:
    """Build autoantibody panel dict — None if not available for this patient."""
    panel = {}
    for col in AUTOANTIBODY_COLS:
        val = row.get(col, np.nan)
        panel[col] = None if pd.isna(val) else float(val)
    # Return None entirely if all values are missing (patient has no ab panel)
    if all(v is None for v in panel.values()):
        return None
    return panel


def result_to_dict(result, categories) -> dict:
    """Convert a DualScoreResult to a clean dict."""
    # Normalise prob dict to cover all 4 categories
    probs = {cat: round(float(result.category_probabilities.get(cat, 0.0)), 4)
             for cat in categories}

    ranked = sorted(probs.items(), key=lambda x: x[1], reverse=True)

    out = {
        "predicted_category":    result.category,
        "category_confidence":   round(float(result.category_confidence), 4),
        "category_probabilities": probs,
        "category_ranking":      [{"category": c, "probability": p} for c, p in ranked],
    }

    if result.disease is not None:
        out["predicted_disease"]       = result.disease
        out["disease_confidence"]      = round(float(result.disease_confidence), 4)
        out["disease_probabilities"]   = {
            k: round(float(v), 4)
            for k, v in (result.disease_probabilities or {}).items()
        }

    return out


def build_case(
    case_label: str,
    patient_id: str,
    row: pd.Series,
    result,
    categories: list,
) -> dict:
    """Assemble the full case record."""
    pred   = result_to_dict(result, categories)
    is_correct = (pred["predicted_category"] == row.get("diagnosis_cluster", "?"))

    # Clinical interpretation
    cat = pred["predicted_category"]
    conf = pred["category_confidence"]

    if cat == "healthy":
        clinical_summary = (
            f"No autoimmune pattern detected ({conf:.0%} confidence). "
            "Lab values fall within normal ranges across all monitored markers."
        )
        patient_summary = (
            "Your results look healthy. Your lab values are within normal ranges "
            "and do not show patterns associated with autoimmune conditions."
        )
        recommended_action = "Routine follow-up with primary care physician."
    elif cat == "systemic":
        clinical_summary = (
            f"Systemic autoimmune pattern detected ({conf:.0%} confidence). "
            "Findings are consistent with systemic inflammation — consider evaluation "
            "for lupus, rheumatoid arthritis, Sjögren's syndrome, or related conditions."
        )
        patient_summary = (
            "Your results suggest patterns seen in conditions like lupus or "
            "rheumatoid arthritis. These are treatable — early evaluation matters."
        )
        recommended_action = (
            "Referral to Rheumatology. Consider: ANA panel, anti-dsDNA, RF, anti-CCP, "
            "complement levels (C3/C4), joint X-rays."
        )
    elif cat == "gastrointestinal":
        clinical_summary = (
            f"Gastrointestinal autoimmune pattern detected ({conf:.0%} confidence). "
            "Findings suggest evaluation for IBD, celiac disease, or related GI conditions."
        )
        patient_summary = (
            "Your results show patterns associated with digestive system conditions "
            "like Crohn's disease, ulcerative colitis, or celiac disease."
        )
        recommended_action = (
            "Referral to Gastroenterology. Consider: fecal calprotectin, tissue "
            "transglutaminase IgA, colonoscopy."
        )
    elif cat == "endocrine":
        clinical_summary = (
            f"Endocrine autoimmune pattern detected ({conf:.0%} confidence). "
            "Findings suggest evaluation for thyroid or metabolic autoimmune conditions."
        )
        patient_summary = (
            "Your results suggest patterns seen in thyroid conditions like "
            "Hashimoto's thyroiditis or Graves' disease."
        )
        recommended_action = (
            "Referral to Endocrinology. Consider: TSH, free T4, anti-TPO antibodies, "
            "anti-thyroglobulin antibodies."
        )
    else:
        clinical_summary = f"Pattern detected: {cat} ({conf:.0%} confidence)."
        patient_summary  = clinical_summary
        recommended_action = "Follow up with primary care."

    case = {
        "meta": {
            "case_label":       case_label,
            "generated_at":     datetime.utcnow().isoformat() + "Z",
            "model":            "Aura Hierarchical Dual-Scorer v1.0",
            "disclaimer":       (
                "This output is generated by an AI clinical decision support tool. "
                "It is not a diagnosis. All findings must be reviewed and validated "
                "by a qualified physician."
            ),
        },
        "patient": {
            "patient_id":         patient_id,
            "age":                None if pd.isna(row.get("age", np.nan)) else int(row["age"]),
            "sex":                row.get("sex", None),
            "bmi":                None if pd.isna(row.get("bmi", np.nan))
                                  else round(float(row["bmi"]), 1),
            "source_dataset":     row.get("source", None),
            "true_diagnosis_cluster": row.get("diagnosis_cluster", None),
            "true_diagnosis_raw":     row.get("diagnosis_raw", None),
            "true_diagnosis_icd10":   row.get("diagnosis_icd10", None),
        },
        "prediction": pred,
        "correct":             is_correct,
        "clinical_interpretation": {
            "summary":              clinical_summary,
            "patient_friendly":     patient_summary,
            "recommended_action":   recommended_action,
            "confidence_tier": (
                "High (>80%)"   if conf >= 0.80 else
                "Moderate (60–80%)" if conf >= 0.60 else
                "Low (<60%)"
            ),
        },
        "lab_panel":      build_lab_panel(row),
        "autoantibody_panel": build_autoantibody_panel(row),
    }

    return case


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Aura Demo Case Generator")
    print("=" * 60)

    # 1. Load case IDs
    with open(CASE_IDS_FILE) as f:
        case_ids: dict = json.load(f)
    print(f"\nLoaded {len(case_ids)} case IDs from case_ids.json")
    for label, pid in case_ids.items():
        print(f"  {label}: {pid}")

    # 2. Load + preprocess data
    print("\n[1/4] Loading data...")
    df = load_modeling_data()
    print(f"      Loaded {len(df):,} patients")

    print("[2/4] Preprocessing...")
    df = preprocess_for_modeling(df, priority_only=True)
    df = engineer_all_features(df)
    print(f"      After priority filter: {len(df):,} patients")

    # 3. Load or train the scorer
    print("[3/4] Loading model...")
    if MODEL_PATH.exists() and (MODEL_PATH / "dual_scorer_meta.joblib").exists():
        scorer = DualScorer.load(str(MODEL_PATH))
        print(f"      Loaded from {MODEL_PATH}")
    else:
        print("      No saved model found — training from scratch...")
        train, val, test = create_splits(df, random_state=RANDOM_STATE)
        X_train, features = prepare_features(train, FEATURE_GROUPS)
        X_val, _          = prepare_features(val, FEATURE_GROUPS)
        scorer = DualScorer()
        scorer.fit(
            X_train, train["diagnosis_cluster"],
            y_disease=train.get("diagnosis_raw"),
            X_val=X_val,
            y_val=val["diagnosis_cluster"],
            verbose=False,
        )
        print("      Training complete.")

    categories = scorer.categories

    # 4. Look up each patient and run inference
    print("\n[4/4] Running inference on demo cases...\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_cases = {}

    for case_label, patient_id in case_ids.items():
        # Find the patient row in the full dataset
        match = df[df["patient_id"] == patient_id]
        if match.empty:
            print(f"  WARNING: patient_id '{patient_id}' not found — skipping.")
            continue

        row = match.iloc[0]

        # Build feature vector — cast to numeric (object dtype after .T)
        feat_cols = scorer.feature_names if scorer.feature_names else scorer.category_classifier.feature_names
        X_patient = row[feat_cols].to_frame().T.reset_index(drop=True)
        X_patient = X_patient.apply(pd.to_numeric, errors="coerce")
        X_patient = X_patient.fillna(X_patient.median(numeric_only=True))

        result = scorer.predict(X_patient)[0]
        case   = build_case(case_label, patient_id, row, result, categories)
        all_cases[case_label] = case

        # Write individual case file
        out_file = OUT_DIR / f"{case_label}.json"
        with open(out_file, "w") as f:
            json.dump(case, f, indent=2, default=serialize)

        # Console summary
        correct_mark = "[OK]" if case["correct"] else "[X]"
        print(f"  {correct_mark}  {case_label}")
        print(f"     Patient ID:    {patient_id}")
        print(f"     Demographics:  age={case['patient']['age']}, sex={case['patient']['sex']}")
        print(f"     True label:    {case['patient']['true_diagnosis_cluster']}"
              f" ({case['patient']['true_diagnosis_raw']})")
        print(f"     Predicted:     {result.category} ({result.category_confidence:.1%} confidence)")
        print(f"     Probabilities:")
        for entry in case["prediction"]["category_ranking"]:
            bar = "|" * int(entry["probability"] * 30)
            print(f"       {entry['category']:20s} {entry['probability']:.3f}  {bar}")
        if result.disease:
            print(f"     Disease est.:  {result.disease} ({result.disease_confidence:.1%})")
        print(f"     Confidence tier: {case['clinical_interpretation']['confidence_tier']}")
        print(f"     Saved -> {out_file.name}\n")

    # 5. Write combined summary file
    summary_file = OUT_DIR / "all_cases_summary.json"
    with open(summary_file, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "n_cases":      len(all_cases),
            "cases":        all_cases,
        }, f, indent=2, default=serialize)

    print(f"Combined summary -> {summary_file.name}")
    print("\n" + "=" * 60)
    print(f"Done. {len(all_cases)} cases written to {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
