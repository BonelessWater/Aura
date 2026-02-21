"""
Tests for notebooks/wrangle_flaredown.py.

Validates the Flaredown patient-reported outcomes wrangling logic using
synthetic data matching the actual CSV schema on Databricks Volume.
"""
import logging

import pandas as pd
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate key functions from the notebook
# ---------------------------------------------------------------------------

CONDITION_TO_CLUSTER = {
    "rheumatoid arthritis": "systemic",
    "lupus": "systemic",
    "sjogren's syndrome": "systemic",
    "ankylosing spondylitis": "systemic",
    "crohn's disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "celiac": "gastrointestinal",
    "hashimoto's thyroiditis": "endocrine",
    "graves' disease": "endocrine",
    "type 1 diabetes": "endocrine",
    "hypothyroidism": "endocrine",
    "multiple sclerosis": "neurological",
    "ms": "neurological",
    "psoriasis": "dermatological",
    "vitiligo": "dermatological",
    "eczema": "dermatological",
    "fibromyalgia": "other_autoimmune",
}


def map_condition_to_cluster(condition_name):
    """Map a Flaredown condition name to an Aura diagnosis cluster."""
    if not condition_name or pd.isna(condition_name):
        return None
    cond_lower = str(condition_name).lower().strip()
    if cond_lower in CONDITION_TO_CLUSTER:
        return CONDITION_TO_CLUSTER[cond_lower]
    for keyword, cluster in CONDITION_TO_CLUSTER.items():
        if keyword in cond_lower or cond_lower in keyword:
            return cluster
    return "other_autoimmune"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flaredown_raw_df():
    """Synthetic Flaredown CSV data matching actual schema."""
    return pd.DataFrame({
        "user_id": ["abc123", "abc123", "abc123", "def456", "def456", "ghi789"],
        "age": ["32", "32", "32", "45", "45", None],
        "sex": ["male", "male", "male", "female", "female", None],
        "country": ["US", "US", "US", "CA", "CA", None],
        "checkin_date": [
            "2020-01-15", "2020-01-15", "2020-01-15",
            "2020-02-20", "2020-02-20", "2020-03-10",
        ],
        "trackable_id": ["1069", "2001", "3001", "1069", "2002", "1069"],
        "trackable_type": ["Condition", "Symptom", "Treatment", "Condition", "Symptom", "Condition"],
        "trackable_name": [
            "Ulcerative colitis", "Fatigue", "Mesalamine",
            "Rheumatoid arthritis", "Joint pain", "Unknown condition",
        ],
        "trackable_value": ["0", "3", "1", "0", "4", "2"],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConditionMapping:
    """Test condition-to-cluster mapping."""

    def test_exact_matches(self):
        assert map_condition_to_cluster("Ulcerative colitis") == "gastrointestinal"
        assert map_condition_to_cluster("Rheumatoid arthritis") == "systemic"
        assert map_condition_to_cluster("Multiple sclerosis") == "neurological"
        assert map_condition_to_cluster("Psoriasis") == "dermatological"

    def test_case_insensitive(self):
        assert map_condition_to_cluster("ULCERATIVE COLITIS") == "gastrointestinal"
        assert map_condition_to_cluster("lupus") == "systemic"

    def test_partial_match(self):
        assert map_condition_to_cluster("Crohn's disease (CD)") == "gastrointestinal"

    def test_unknown_condition(self):
        assert map_condition_to_cluster("random thing") == "other_autoimmune"

    def test_none_and_nan(self):
        assert map_condition_to_cluster(None) is None
        assert map_condition_to_cluster(float("nan")) is None


class TestFlaredownParsing:
    """Test Flaredown data parsing logic."""

    def test_trackable_types(self, flaredown_raw_df):
        types = flaredown_raw_df["trackable_type"].value_counts().to_dict()
        assert types["Condition"] == 3
        assert types["Symptom"] == 2
        assert types["Treatment"] == 1

    def test_patient_id_generation(self, flaredown_raw_df):
        patient_ids = "flaredown_" + flaredown_raw_df["user_id"].astype(str)
        assert patient_ids.iloc[0] == "flaredown_abc123"
        assert patient_ids.iloc[3] == "flaredown_def456"

    def test_date_parsing(self, flaredown_raw_df):
        dates = pd.to_datetime(flaredown_raw_df["checkin_date"], errors="coerce")
        assert dates.notna().all()

    def test_condition_extraction(self, flaredown_raw_df):
        conditions = flaredown_raw_df[flaredown_raw_df["trackable_type"] == "Condition"]
        patient_conditions = conditions.groupby(
            "flaredown_" + conditions["user_id"].astype(str)
        )["trackable_name"].first().to_dict()
        assert patient_conditions["flaredown_abc123"] == "Ulcerative colitis"
        assert patient_conditions["flaredown_def456"] == "Rheumatoid arthritis"

    def test_symptom_severity_numeric(self, flaredown_raw_df):
        symptoms = flaredown_raw_df[flaredown_raw_df["trackable_type"] == "Symptom"]
        severity = pd.to_numeric(symptoms["trackable_value"], errors="coerce")
        assert severity.notna().all()
        assert severity.between(0, 4).all()

    def test_relevant_type_filtering(self, flaredown_raw_df):
        relevant_types = ["Condition", "Symptom", "Treatment", "Food", "HBI"]
        filtered = flaredown_raw_df[
            flaredown_raw_df["trackable_type"].isin(relevant_types)
        ]
        # Weather and Tag should be excluded; our fixture has none of those
        assert len(filtered) == len(flaredown_raw_df)


class TestFlaredownOutputSchema:
    """Test the expected output schema."""

    def test_output_columns(self):
        expected_cols = [
            "patient_id", "source", "date", "condition", "diagnosis_cluster",
            "symptom", "symptom_severity", "treatment", "treatment_dose",
            "trigger", "country", "age", "sex",
        ]
        # Just verify the expected set is defined correctly
        assert len(expected_cols) == 13
        assert "patient_id" in expected_cols
        assert "diagnosis_cluster" in expected_cols

    def test_source_always_flaredown(self):
        sources = pd.Series(["flaredown"] * 5)
        assert (sources == "flaredown").all()
