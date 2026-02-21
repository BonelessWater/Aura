"""
Tests for the Aura data access layer (notebooks/aura_data.py).

The SQL views created by the notebook can only be tested on Databricks.
These tests validate the pure Python logic: disease-to-cluster lookup,
age bucketing, and constants that the notebook defines.

We replicate the relevant constants and functions here (they live in a
Databricks notebook, not an importable module) and test them directly.
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))


# ---------------------------------------------------------------------------
# Replicate the Python helpers from notebooks/aura_data.py for local testing.
# These must stay in sync with the notebook -- if you change the notebook,
# update these definitions to match.
# ---------------------------------------------------------------------------

AURA_CLUSTERS = [
    "healthy", "systemic", "endocrine", "gastrointestinal",
    "neurological", "dermatological", "ophthalmic",
    "other_autoimmune", "haematological", "renal", "pulmonary",
]

DISEASE_CLUSTER_MAP = {
    "rheumatoid arthritis":     "systemic",
    "systemic lupus erythematosus": "systemic",
    "sle":                      "systemic",
    "lupus":                    "systemic",
    "sjogren's syndrome":       "systemic",
    "sjogrens":                 "systemic",
    "psoriatic arthritis":      "systemic",
    "reactive arthritis":       "systemic",
    "ankylosing spondylitis":   "other_autoimmune",
    "scleroderma":              "systemic",
    "systemic sclerosis":       "systemic",
    "mixed connective tissue disease": "systemic",
    "dermatomyositis":          "systemic",
    "polymyositis":             "systemic",
    "hashimoto's thyroiditis":  "endocrine",
    "autoimmune thyroiditis":   "endocrine",
    "graves' disease":          "endocrine",
    "graves":                   "endocrine",
    "type 1 diabetes":          "endocrine",
    "t1d":                      "endocrine",
    "addison's disease":        "endocrine",
    "crohn's disease":          "gastrointestinal",
    "crohns":                   "gastrointestinal",
    "ulcerative colitis":       "gastrointestinal",
    "celiac disease":           "gastrointestinal",
    "celiac":                   "gastrointestinal",
    "ibd":                      "gastrointestinal",
    "inflammatory bowel disease": "gastrointestinal",
    "multiple sclerosis":       "neurological",
    "ms":                       "neurological",
    "myasthenia gravis":        "neurological",
    "guillain-barre syndrome":  "neurological",
    "psoriasis":                "dermatological",
    "vitiligo":                 "dermatological",
    "alopecia areata":          "dermatological",
    "pemphigus":                "dermatological",
    "uveitis":                  "ophthalmic",
    "itp":                      "haematological",
    "autoimmune hemolytic anemia": "haematological",
    "lupus nephritis":          "renal",
    "pulmonary fibrosis":       "pulmonary",
    "sarcoidosis":              "other_autoimmune",
}

AGE_BUCKETS = [
    (0, 17, "0-17"),
    (18, 30, "18-30"),
    (31, 45, "31-45"),
    (46, 60, "46-60"),
    (61, 200, "61+"),
]


def disease_to_cluster(name):
    """Map a disease name to its Aura diagnosis cluster (case-insensitive)."""
    return DISEASE_CLUSTER_MAP.get(name.lower().strip())


def _age_to_bucket(age):
    """Convert a numeric age to the healthy_baselines age bucket string."""
    for low, high, label in AGE_BUCKETS:
        if low <= age <= high:
            return label
    return "61+"


# ===========================================================================
# Constants and cluster definitions
# ===========================================================================
class TestConstants:
    """Validate the AURA_CLUSTERS list and DISEASE_CLUSTER_MAP."""

    def test_aura_clusters_has_11_entries(self):
        assert len(AURA_CLUSTERS) == 11

    def test_aura_clusters_includes_healthy(self):
        assert "healthy" in AURA_CLUSTERS

    def test_aura_clusters_includes_systemic(self):
        assert "systemic" in AURA_CLUSTERS

    def test_aura_clusters_no_duplicates(self):
        assert len(AURA_CLUSTERS) == len(set(AURA_CLUSTERS))

    def test_disease_map_not_empty(self):
        assert len(DISEASE_CLUSTER_MAP) > 30

    def test_all_map_values_are_valid_clusters(self):
        """Every value in DISEASE_CLUSTER_MAP must be a valid Aura cluster."""
        for disease, cluster in DISEASE_CLUSTER_MAP.items():
            assert cluster in AURA_CLUSTERS, (
                f"'{disease}' maps to '{cluster}' which is not in AURA_CLUSTERS"
            )


# ===========================================================================
# Disease-to-cluster lookup
# ===========================================================================
class TestDiseaseToCluster:
    """Validate the disease_to_cluster() lookup function."""

    def test_known_systemic_conditions(self):
        assert disease_to_cluster("Rheumatoid Arthritis") == "systemic"
        assert disease_to_cluster("lupus") == "systemic"
        assert disease_to_cluster("SLE") == "systemic"
        assert disease_to_cluster("Sjogren's Syndrome") == "systemic"

    def test_known_endocrine_conditions(self):
        assert disease_to_cluster("Hashimoto's Thyroiditis") == "endocrine"
        assert disease_to_cluster("Graves' Disease") == "endocrine"
        assert disease_to_cluster("Type 1 Diabetes") == "endocrine"
        assert disease_to_cluster("T1D") == "endocrine"

    def test_known_gi_conditions(self):
        assert disease_to_cluster("Crohn's Disease") == "gastrointestinal"
        assert disease_to_cluster("Celiac Disease") == "gastrointestinal"
        assert disease_to_cluster("Ulcerative Colitis") == "gastrointestinal"
        assert disease_to_cluster("IBD") == "gastrointestinal"

    def test_known_neurological_conditions(self):
        assert disease_to_cluster("Multiple Sclerosis") == "neurological"
        assert disease_to_cluster("MS") == "neurological"
        assert disease_to_cluster("Myasthenia Gravis") == "neurological"

    def test_known_dermatological_conditions(self):
        assert disease_to_cluster("Psoriasis") == "dermatological"
        assert disease_to_cluster("Vitiligo") == "dermatological"
        assert disease_to_cluster("Alopecia Areata") == "dermatological"

    def test_known_other_clusters(self):
        assert disease_to_cluster("Uveitis") == "ophthalmic"
        assert disease_to_cluster("ITP") == "haematological"
        assert disease_to_cluster("Lupus Nephritis") == "renal"
        assert disease_to_cluster("Pulmonary Fibrosis") == "pulmonary"
        assert disease_to_cluster("Sarcoidosis") == "other_autoimmune"

    def test_case_insensitive(self):
        assert disease_to_cluster("rheumatoid arthritis") == "systemic"
        assert disease_to_cluster("RHEUMATOID ARTHRITIS") == "systemic"
        assert disease_to_cluster("Rheumatoid Arthritis") == "systemic"

    def test_whitespace_stripped(self):
        assert disease_to_cluster("  lupus  ") == "systemic"
        assert disease_to_cluster("  celiac  ") == "gastrointestinal"

    def test_unknown_disease_returns_none(self):
        assert disease_to_cluster("Not A Real Disease") is None
        assert disease_to_cluster("") is None

    def test_abbreviations_work(self):
        assert disease_to_cluster("SLE") == "systemic"
        assert disease_to_cluster("MS") == "neurological"
        assert disease_to_cluster("T1D") == "endocrine"
        assert disease_to_cluster("ITP") == "haematological"
        assert disease_to_cluster("IBD") == "gastrointestinal"


# ===========================================================================
# Age bucketing
# ===========================================================================
class TestAgeBucketing:
    """Validate the _age_to_bucket() helper."""

    def test_infant(self):
        assert _age_to_bucket(0) == "0-17"

    def test_child(self):
        assert _age_to_bucket(10) == "0-17"

    def test_teenager(self):
        assert _age_to_bucket(17) == "0-17"

    def test_young_adult(self):
        assert _age_to_bucket(18) == "18-30"
        assert _age_to_bucket(25) == "18-30"
        assert _age_to_bucket(30) == "18-30"

    def test_adult(self):
        assert _age_to_bucket(31) == "31-45"
        assert _age_to_bucket(40) == "31-45"
        assert _age_to_bucket(45) == "31-45"

    def test_middle_aged(self):
        assert _age_to_bucket(46) == "46-60"
        assert _age_to_bucket(55) == "46-60"
        assert _age_to_bucket(60) == "46-60"

    def test_senior(self):
        assert _age_to_bucket(61) == "61+"
        assert _age_to_bucket(75) == "61+"
        assert _age_to_bucket(90) == "61+"

    def test_very_old(self):
        """Ages beyond 200 should still return 61+."""
        assert _age_to_bucket(250) == "61+"


# ===========================================================================
# Cross-check against the wrangling pipeline's ICD10_TO_CLUSTER
# ===========================================================================
class TestCrossCheckWithPipeline:
    """Verify that DISEASE_CLUSTER_MAP is consistent with the pipeline's
    ICD10_TO_CLUSTER mapping used in 02_wrangle_data.py."""

    @pytest.fixture(autouse=True)
    def load_pipeline_mappings(self):
        """Import the pipeline's dictionaries for cross-validation."""
        import importlib
        try:
            wrangle = importlib.import_module("02_wrangle_data")
            self.icd10_to_cluster = wrangle.ICD10_TO_CLUSTER
            self.disease_to_icd10 = wrangle.DISEASE_TO_ICD10
        except ImportError:
            pytest.skip("02_wrangle_data.py not importable")

    def test_ra_cluster_matches_pipeline(self):
        """RA in our map should match the pipeline's cluster for M06.9."""
        assert disease_to_cluster("rheumatoid arthritis") == "systemic"
        pipeline_cluster = self.icd10_to_cluster.get("M06.9")
        assert pipeline_cluster == "systemic", (
            f"Pipeline maps M06.9 to '{pipeline_cluster}', expected 'systemic'"
        )

    def test_lupus_cluster_matches_pipeline(self):
        assert disease_to_cluster("lupus") == "systemic"
        pipeline_cluster = self.icd10_to_cluster.get("M32.9")
        assert pipeline_cluster == "systemic"

    def test_celiac_cluster_matches_pipeline(self):
        assert disease_to_cluster("celiac disease") == "gastrointestinal"
        pipeline_cluster = self.icd10_to_cluster.get("K90.0")
        assert pipeline_cluster == "gastrointestinal"

    def test_ms_cluster_matches_pipeline(self):
        assert disease_to_cluster("multiple sclerosis") == "neurological"
        pipeline_cluster = self.icd10_to_cluster.get("G35")
        assert pipeline_cluster == "neurological"

    def test_psoriasis_cluster_matches_pipeline(self):
        assert disease_to_cluster("psoriasis") == "dermatological"
        pipeline_cluster = self.icd10_to_cluster.get("L40.9")
        assert pipeline_cluster == "dermatological"

    def test_hashimotos_cluster_matches_pipeline(self):
        assert disease_to_cluster("hashimoto's thyroiditis") == "endocrine"
        pipeline_cluster = self.icd10_to_cluster.get("E06.3")
        assert pipeline_cluster == "endocrine"
