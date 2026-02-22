"""Tests for the diagnosis normalization and dataset formatting logic
used in the fine-tuning notebooks (08, 09, 10).

These tests verify the shared preprocessing code that all three notebooks
use to prepare the PMC-Patients data for training.
"""

import re
import math
import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


# ---------------------------------------------------------------------------
# Replicate the preprocessing functions from the notebooks so we can test
# them without running a full notebook.
# ---------------------------------------------------------------------------

SYNONYM_MAP = {
    "sle": "systemic lupus erythematosus",
    "ra": "rheumatoid arthritis",
    "ms": "multiple sclerosis",
    "ibd": "inflammatory bowel disease",
    "uc": "ulcerative colitis",
    "cd": "crohn disease",
    "gpa": "granulomatosis with polyangiitis",
    "wegener's granulomatosis": "granulomatosis with polyangiitis",
    "wegener granulomatosis": "granulomatosis with polyangiitis",
    "hashimoto's thyroiditis": "hashimoto thyroiditis",
    "grave's disease": "graves disease",
    "behcet's disease": "behcet disease",
    "sjogren's syndrome": "sjogren syndrome",
    "addison's disease": "addison disease",
    "crohn's disease": "crohn disease",
    "hodgkin's lymphoma": "hodgkin lymphoma",
    "non-hodgkin's lymphoma": "non-hodgkin lymphoma",
    "burkitt's lymphoma": "burkitt lymphoma",
    "cushing's syndrome": "cushing syndrome",
    "paget's disease": "paget disease",
    "wilson's disease": "wilson disease",
    "parkinson's disease": "parkinson disease",
    "alzheimer's disease": "alzheimer disease",
    "still's disease": "still disease",
    "kawasaki's disease": "kawasaki disease",
    "takayasu's arteritis": "takayasu arteritis",
    "goodpasture's syndrome": "goodpasture syndrome",
    "guillain-barre syndrome": "guillain barre syndrome",
    "guillain-barr\u00e9 syndrome": "guillain barre syndrome",
    "non-hodgkin lymphoma": "non-hodgkin lymphoma",
}

STRIP_PREFIXES = [
    "a diagnosis of ",
    "the diagnosis of ",
    "diagnosis of ",
    "diagnosed with ",
    "diagnosed as ",
    "final diagnosis: ",
    "final diagnosis of ",
]


def normalize_diagnosis(text):
    """Normalize a diagnosis string for consistent labeling."""
    if not text or (isinstance(text, float) and math.isnan(text)):
        return None
    text = str(text).strip().lower()
    if not text:
        return None
    for prefix in STRIP_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = text.rstrip(".")
    if text in SYNONYM_MAP:
        text = SYNONYM_MAP[text]
    text = re.sub(r"'s\b", "", text)
    text = text.strip()
    return text if text else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNormalizeDiagnosis:
    """Test the normalize_diagnosis function handles various input formats."""

    def test_basic_lowercase(self):
        assert normalize_diagnosis("Tuberculosis") == "tuberculosis"

    def test_strip_whitespace(self):
        assert normalize_diagnosis("  tuberculosis  ") == "tuberculosis"

    def test_strip_trailing_period(self):
        assert normalize_diagnosis("tuberculosis.") == "tuberculosis"

    def test_strip_prefix_diagnosis_of(self):
        assert normalize_diagnosis("diagnosis of tuberculosis") == "tuberculosis"

    def test_strip_prefix_a_diagnosis_of(self):
        assert normalize_diagnosis("A diagnosis of Crohn disease") == "crohn disease"

    def test_strip_prefix_diagnosed_with(self):
        assert normalize_diagnosis("diagnosed with SLE") == "systemic lupus erythematosus"

    def test_strip_prefix_final_diagnosis(self):
        assert normalize_diagnosis("Final diagnosis: pneumonia") == "pneumonia"

    def test_synonym_sle(self):
        assert normalize_diagnosis("SLE") == "systemic lupus erythematosus"

    def test_synonym_ra(self):
        assert normalize_diagnosis("RA") == "rheumatoid arthritis"

    def test_synonym_gpa(self):
        assert normalize_diagnosis("GPA") == "granulomatosis with polyangiitis"

    def test_synonym_wegeners(self):
        assert normalize_diagnosis("Wegener's granulomatosis") == "granulomatosis with polyangiitis"

    def test_possessive_normalization(self):
        assert normalize_diagnosis("Crohn's disease") == "crohn disease"

    def test_possessive_normalization_hashimoto(self):
        assert normalize_diagnosis("Hashimoto's thyroiditis") == "hashimoto thyroiditis"

    def test_possessive_normalization_graves(self):
        result = normalize_diagnosis("Grave's disease")
        assert result == "graves disease"

    def test_none_input(self):
        assert normalize_diagnosis(None) is None

    def test_empty_string(self):
        assert normalize_diagnosis("") is None

    def test_whitespace_only(self):
        assert normalize_diagnosis("   ") is None

    def test_nan_input(self):
        assert normalize_diagnosis(float("nan")) is None

    def test_numpy_nan(self):
        assert normalize_diagnosis(np.nan) is None

    def test_no_change_needed(self):
        assert normalize_diagnosis("pneumonia") == "pneumonia"

    def test_prefix_plus_synonym(self):
        """Prefix stripping followed by synonym lookup."""
        assert normalize_diagnosis("diagnosed with SLE") == "systemic lupus erythematosus"

    def test_case_insensitive_prefix(self):
        """Prefixes match after lowering case."""
        assert normalize_diagnosis("Diagnosed with tuberculosis") == "tuberculosis"

    def test_guillain_barre_accent(self):
        assert normalize_diagnosis("Guillain-Barr\u00e9 syndrome") == "guillain barre syndrome"

    def test_guillain_barre_no_accent(self):
        assert normalize_diagnosis("Guillain-Barre syndrome") == "guillain barre syndrome"

    def test_numeric_input(self):
        """Non-string numeric input should be converted."""
        assert normalize_diagnosis(42) == "42"


class TestDiagnosisConsistency:
    """Test that synonymous diagnoses all normalize to the same string."""

    @pytest.mark.parametrize("variant,expected", [
        ("Crohn's disease", "crohn disease"),
        ("crohn's disease", "crohn disease"),
        ("Crohn disease", "crohn disease"),
        ("CROHN'S DISEASE", "crohn disease"),
    ])
    def test_crohn_variants(self, variant, expected):
        assert normalize_diagnosis(variant) == expected

    @pytest.mark.parametrize("variant", [
        "SLE",
        "systemic lupus erythematosus",
        "Systemic Lupus Erythematosus",
        "diagnosed with SLE",
    ])
    def test_sle_variants(self, variant):
        assert normalize_diagnosis(variant) == "systemic lupus erythematosus"

    @pytest.mark.parametrize("variant", [
        "Wegener's granulomatosis",
        "wegener granulomatosis",
        "GPA",
    ])
    def test_gpa_variants(self, variant):
        assert normalize_diagnosis(variant) == "granulomatosis with polyangiitis"


class TestDataPreprocessingPipeline:
    """Test the full data preprocessing pipeline that the notebooks use."""

    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame mimicking pmc_patients_classified."""
        return pd.DataFrame({
            "patient_id": range(20),
            "preliminary_text": [
                "A 60-year-old woman presented with shortness of breath.",
                "A 45-year-old man had joint pain and fatigue.",
                "",  # empty text -- should be dropped
                "Patient with fever and rash for 2 weeks.",
                "Labs showed elevated CRP and ESR.",
                "A 30-year-old with chest pain and dyspnea.",
                "Elderly patient with progressive weakness.",
                "Child presented with recurrent infections.",
                "A 55-year-old diabetic with foot ulcer.",
                "Patient with bloody diarrhea and weight loss.",
                "A 70-year-old with tremor and rigidity.",
                "Young woman with butterfly rash and arthralgia.",
                "Man with hemoptysis and bilateral infiltrates.",
                "Patient with goiter and thyroid eye disease.",
                "A 25-year-old with skin lesions and oral ulcers.",
                "Infant with failure to thrive.",
                "A 40-year-old with chronic back pain.",
                "Patient with recurrent abdominal pain.",
                "A 35-year-old with proteinuria.",
                "Elderly man with pancytopenia.",
            ],
            "diagnosis": [
                "pneumonia",
                "Rheumatoid Arthritis",
                "tuberculosis",  # will be dropped (empty text)
                "SLE",
                "pneumonia",
                "pneumonia",
                "Parkinson's disease",
                "pneumonia",
                "pneumonia",
                "Crohn's disease",
                "Parkinson's disease",
                "SLE",
                "tuberculosis",
                None,  # missing diagnosis -- should be dropped
                "Behcet's disease",
                "pneumonia",
                "pneumonia",
                "Crohn's disease",
                "pneumonia",
                "tuberculosis",
            ],
        })

    def test_drop_empty_text(self, sample_df):
        """Rows with empty preliminary_text are dropped."""
        df = sample_df.dropna(subset=["preliminary_text", "diagnosis"])
        df = df[df["preliminary_text"].str.strip().astype(bool)]
        assert len(df) < len(sample_df)
        assert not any(df["preliminary_text"].str.strip() == "")

    def test_drop_missing_diagnosis(self, sample_df):
        """Rows with None diagnosis are dropped."""
        df = sample_df.dropna(subset=["preliminary_text", "diagnosis"])
        assert not df["diagnosis"].isna().any()

    def test_normalization_applied(self, sample_df):
        """Normalization produces consistent labels."""
        df = sample_df.dropna(subset=["preliminary_text", "diagnosis"])
        df = df[df["preliminary_text"].str.strip().astype(bool)]
        df["diagnosis_norm"] = df["diagnosis"].apply(normalize_diagnosis)
        df = df.dropna(subset=["diagnosis_norm"])

        # SLE variants should all be the same
        sle_rows = df[df["diagnosis"].isin(["SLE"])]
        assert all(sle_rows["diagnosis_norm"] == "systemic lupus erythematosus")

        # Crohn's variants
        crohn_rows = df[df["diagnosis"].str.contains("Crohn", na=False)]
        assert all(crohn_rows["diagnosis_norm"] == "crohn disease")

    def test_min_count_filter(self, sample_df):
        """Diagnoses with fewer than min_count examples are filtered out."""
        df = sample_df.dropna(subset=["preliminary_text", "diagnosis"])
        df = df[df["preliminary_text"].str.strip().astype(bool)]
        df["diagnosis_norm"] = df["diagnosis"].apply(normalize_diagnosis)
        df = df.dropna(subset=["diagnosis_norm"])

        min_count = 3
        counts = df["diagnosis_norm"].value_counts()
        valid = counts[counts >= min_count].index
        df_filtered = df[df["diagnosis_norm"].isin(valid)]

        # Every remaining diagnosis should have >= min_count examples
        remaining_counts = df_filtered["diagnosis_norm"].value_counts()
        assert all(remaining_counts >= min_count)

    def test_stratified_split_preserves_distribution(self, sample_df):
        """Stratified split keeps diagnosis distribution roughly proportional."""
        df = sample_df.dropna(subset=["preliminary_text", "diagnosis"])
        df = df[df["preliminary_text"].str.strip().astype(bool)]
        df["diagnosis_norm"] = df["diagnosis"].apply(normalize_diagnosis)
        df = df.dropna(subset=["diagnosis_norm"])

        # Only keep diagnoses with enough samples for stratification
        counts = df["diagnosis_norm"].value_counts()
        valid = counts[counts >= 3].index
        df = df[df["diagnosis_norm"].isin(valid)]

        if len(df) < 10:
            pytest.skip("Not enough data for meaningful split test")

        train_df, test_df = train_test_split(
            df, test_size=0.2, random_state=42,
            stratify=df["diagnosis_norm"],
        )

        # Check all diagnoses present in train are also in test
        train_dx = set(train_df["diagnosis_norm"])
        test_dx = set(test_df["diagnosis_norm"])
        assert test_dx.issubset(train_dx)


class TestPromptFormatting:
    """Test the prompt formatting functions for each model type."""

    def test_phi3_format_with_diagnosis(self):
        """Phi-3 format includes system, user, and assistant turns."""
        system_prompt = "You are an expert clinical diagnostician."

        def format_chat_phi3(preliminary_text, diagnosis=None):
            text = (
                f"<|system|>\n{system_prompt}<|end|>\n"
                f"<|user|>\n{preliminary_text}\n\n"
                "What is the most likely diagnosis?<|end|>\n"
                "<|assistant|>\n"
            )
            if diagnosis is not None:
                text += f"{diagnosis}<|end|>"
            return text

        result = format_chat_phi3("Patient has fever.", "pneumonia")
        assert "<|system|>" in result
        assert "<|user|>" in result
        assert "<|assistant|>" in result
        assert "Patient has fever." in result
        assert "pneumonia<|end|>" in result

    def test_phi3_format_without_diagnosis(self):
        """Without diagnosis, the assistant turn is open-ended."""
        system_prompt = "You are an expert clinical diagnostician."

        def format_chat_phi3(preliminary_text, diagnosis=None):
            text = (
                f"<|system|>\n{system_prompt}<|end|>\n"
                f"<|user|>\n{preliminary_text}\n\n"
                "What is the most likely diagnosis?<|end|>\n"
                "<|assistant|>\n"
            )
            if diagnosis is not None:
                text += f"{diagnosis}<|end|>"
            return text

        result = format_chat_phi3("Patient has fever.")
        assert result.endswith("<|assistant|>\n")
        assert "pneumonia" not in result

    def test_t5_format_input(self):
        """T5 format uses a simple task prefix."""
        prefix = "Diagnose this patient: "

        def format_input(preliminary_text):
            return f"{prefix}{preliminary_text}"

        result = format_input("Patient has fever and cough.")
        assert result.startswith("Diagnose this patient: ")
        assert "Patient has fever and cough." in result

    def test_t5_format_no_special_tokens(self):
        """T5 input should not contain chat-style special tokens."""
        prefix = "Diagnose this patient: "
        result = f"{prefix}Patient has fever."
        assert "<|" not in result
        assert "[INST]" not in result


class TestMetricsComputation:
    """Test the evaluation metrics functions."""

    def test_exact_match_perfect(self):
        preds = ["pneumonia", "tuberculosis", "sle"]
        refs = ["pneumonia", "tuberculosis", "sle"]
        exact = sum(
            normalize_diagnosis(p) == normalize_diagnosis(r)
            for p, r in zip(preds, refs)
        )
        assert exact / len(refs) == 1.0

    def test_exact_match_with_normalization(self):
        """Predictions that differ in casing/possessives should still match."""
        preds = ["Crohn's Disease", "SLE", "Wegener's granulomatosis"]
        refs = ["crohn disease", "systemic lupus erythematosus",
                "granulomatosis with polyangiitis"]
        matches = sum(
            normalize_diagnosis(p) == normalize_diagnosis(r)
            for p, r in zip(preds, refs)
        )
        assert matches == 3

    def test_exact_match_none(self):
        preds = ["pneumonia", "cancer", "flu"]
        refs = ["tuberculosis", "diabetes", "malaria"]
        exact = sum(
            normalize_diagnosis(p) == normalize_diagnosis(r)
            for p, r in zip(preds, refs)
        )
        assert exact == 0

    def test_top_k_accuracy(self):
        """Top-k accuracy: correct answer anywhere in top k candidates."""
        top_k_preds = [
            ["pneumonia", "bronchitis", "tuberculosis"],
            ["diabetes", "obesity", "metabolic syndrome"],
            ["sle", "ra", "sjogren syndrome"],
        ]
        refs = ["tuberculosis", "diabetes", "rheumatoid arthritis"]

        for k in [1, 3]:
            matches = sum(
                any(
                    normalize_diagnosis(p) == normalize_diagnosis(r)
                    for p in candidates[:k]
                )
                for candidates, r in zip(top_k_preds, refs)
            )
            if k == 1:
                # Only "diabetes" matches at position 1
                assert matches == 1
            elif k == 3:
                # "tuberculosis" at pos 3, "diabetes" at pos 1, "ra" at pos 2
                # (synonym: "ra" -> "rheumatoid arthritis")
                assert matches == 3
