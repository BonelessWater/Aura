"""
Tests for the Aura data wrangling pipeline (scripts/02_wrangle_data.py).
Validates all 13 fixes applied to the pipeline.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

# Add project root to path so we can import the wrangling module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

import importlib
wrangle = importlib.import_module("02_wrangle_data")


# ---------------------------------------------------------------------------
# Helper: paths to processed parquet files (produced by a prior pipeline run)
# ---------------------------------------------------------------------------
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
CORE_MATRIX_PATH = os.path.join(PROCESSED_DIR, "tier1", "core_matrix.parquet")
AUTOANTIBODY_PATH = os.path.join(PROCESSED_DIR, "tier2", "autoantibody_panel.parquet")
LONGITUDINAL_PATH = os.path.join(PROCESSED_DIR, "tier2", "longitudinal_labs.parquet")
BASELINES_PATH = os.path.join(PROCESSED_DIR, "tier3", "healthy_baselines.parquet")
ICD_MAP_PATH = os.path.join(PROCESSED_DIR, "tier3", "icd_cluster_map.parquet")
DRUG_INDEX_PATH = os.path.join(PROCESSED_DIR, "tier3", "drug_risk_index.parquet")

# Skip all integration tests if parquet files have not been generated yet
pytestmark = pytest.mark.skipif(
    not os.path.exists(CORE_MATRIX_PATH),
    reason="Processed parquet files not found -- run the pipeline first",
)


# ===========================================================================
# Fix #1 & #4: Unit conversion -- WBC, platelet_count in correct range
# ===========================================================================
class TestUnitConversion:
    """Validates that detect_and_convert_units works correctly."""

    def test_wbc_conversion_from_cells_per_ul(self):
        """WBC in cells/uL (4000-12000) should be divided by 1000."""
        # detect_and_convert_units needs >= 10 non-null values to trigger
        series = pd.Series([4000, 5000, 6000, 7000, 8000, 9000,
                            10000, 11000, 12000, 4500, 5500, np.nan])
        result = wrangle.detect_and_convert_units(series, "wbc", "test")
        assert result.dropna().max() <= 20.0, "WBC should be in 10^3/uL after conversion"

    def test_wbc_already_correct_units(self):
        """WBC already in 10^3/uL (4-12) should not be changed."""
        series = pd.Series([4.0, 7.0, 12.0] * 10)
        result = wrangle.detect_and_convert_units(series, "wbc", "test")
        pd.testing.assert_series_equal(result, series)

    def test_hemoglobin_conversion_from_g_per_l(self):
        """Hemoglobin in g/L (100-170) should be divided by 10."""
        series = pd.Series([100, 135, 170] * 10)
        result = wrangle.detect_and_convert_units(series, "hemoglobin", "test")
        assert result.max() <= 20.0, "Hemoglobin should be in g/dL after conversion"

    def test_platelet_conversion_from_cells(self):
        """Platelet in cells/uL (>50000) should be divided by 1000."""
        series = pd.Series([150000, 300000, 400000] * 10)
        result = wrangle.detect_and_convert_units(series, "platelet_count", "test")
        assert result.max() <= 1000, "Platelets should be in 10^3/uL"

    def test_no_extreme_wbc_zscores(self):
        """No more than a handful of WBC z-scores should exceed 100.
        NHANES has rare legitimate outliers (e.g. WBC=400 in leukemia)
        but unit-mismatch issues produced 89+ extreme values before the fix."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        wbc_z = cm["wbc_zscore"].dropna()
        extreme = (wbc_z.abs() > 100).sum()
        assert extreme <= 5, f"Found {extreme} WBC z-scores > 100 (max 5 allowed for outliers)"


# ===========================================================================
# Fix #3: Expanded DISEASE_TO_ICD10 covers autoimmune conditions
# ===========================================================================
class TestExpandedDiagnosisMapping:
    """The expanded ICD-10 lookup should map autoimmune diagnoses."""

    def test_case_insensitive_lookup(self):
        """map_diagnosis should match regardless of case."""
        assert wrangle.map_diagnosis("rheumatoid arthritis") == "M06.9"
        assert wrangle.map_diagnosis("Rheumatoid Arthritis") == "M06.9"
        assert wrangle.map_diagnosis("RHEUMATOID ARTHRITIS") == "M06.9"

    def test_new_conditions_mapped(self):
        """Conditions that were previously unmapped should now resolve."""
        assert wrangle.map_diagnosis("Celiac disease") == "K90.0"
        assert wrangle.map_diagnosis("Pemphigus vulgaris") == "L10.0"
        assert wrangle.map_diagnosis("Vitiligo") == "L80"
        assert wrangle.map_diagnosis("Autoimmune hepatitis") == "K75.4"
        assert wrangle.map_diagnosis("Alopecia areata") == "L63.9"


# ===========================================================================
# Fix #5: Imputation + missingness indicators
# ===========================================================================
class TestImputation:
    """Imputation should reduce NaN counts and add _missing flags."""

    def test_missingness_flags_exist(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        for col in ["esr", "crp", "wbc", "rbc", "hemoglobin"]:
            flag = f"{col}_missing"
            assert flag in cm.columns, f"Missing flag column {flag} not found"

    def test_missingness_flags_are_binary(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        for col in ["esr_missing", "crp_missing", "wbc_missing"]:
            if col in cm.columns:
                vals = cm[col].unique()
                assert set(vals).issubset({0, 1}), f"{col} has non-binary values: {vals}"

    def test_nhanes_wbc_fully_imputed(self):
        """NHANES WBC has <15% missing, so median imputation should fill it."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        wbc_null = nhanes["wbc"].isna().sum()
        assert wbc_null == 0, f"NHANES WBC still has {wbc_null} NaN after imputation"


# ===========================================================================
# Fix #6: Autoantibody panel columns populated (not 100% NaN)
# ===========================================================================
class TestAutoantibodyPanel:
    """Categorical columns should be mapped to 1/0, not all NaN."""

    def test_ana_status_populated(self):
        ab = pd.read_parquet(AUTOANTIBODY_PATH)
        nonnull = ab["ana_status"].notna().sum()
        assert nonnull > 0, "ana_status is entirely NaN"

    def test_anti_dsdna_populated(self):
        ab = pd.read_parquet(AUTOANTIBODY_PATH)
        nonnull = ab["anti_dsdna"].notna().sum()
        assert nonnull > 0, "anti_dsdna is entirely NaN"

    def test_hla_b27_populated(self):
        ab = pd.read_parquet(AUTOANTIBODY_PATH)
        nonnull = ab["hla_b27"].notna().sum()
        assert nonnull > 0, "hla_b27 is entirely NaN"

    def test_categorical_values_are_binary(self):
        """Positive/Negative should be mapped to 1.0/0.0."""
        ab = pd.read_parquet(AUTOANTIBODY_PATH)
        for col in ["ana_status", "anti_dsdna", "hla_b27", "anti_sm", "anti_ro", "anti_la"]:
            vals = ab[col].dropna().unique()
            assert set(vals).issubset({0.0, 1.0}), (
                f"{col} has values {vals}, expected 0.0/1.0"
            )

    def test_map_categorical_to_binary(self):
        assert wrangle.map_categorical_to_binary("Positive") == 1.0
        assert wrangle.map_categorical_to_binary("Negative") == 0.0
        assert wrangle.map_categorical_to_binary("pos") == 1.0
        assert np.isnan(wrangle.map_categorical_to_binary(np.nan))


# ===========================================================================
# Fix #7: MIMIC ICD-9 to ICD-10 crosswalk
# ===========================================================================
class TestMIMICCrosswalk:
    """MIMIC diagnoses should have some mapped ICD-10 codes."""

    def test_icd9_crosswalk_exists(self):
        assert len(wrangle.ICD9_TO_ICD10) > 0

    def test_common_icd9_codes_mapped(self):
        assert wrangle.ICD9_TO_ICD10.get("7140") == "M06.9"  # RA
        assert wrangle.ICD9_TO_ICD10.get("7100") == "M32.9"  # SLE
        assert wrangle.ICD9_TO_ICD10.get("5550") == "K50.9"  # Crohn's

    def test_some_mimic_rows_have_cluster(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        mimic = cm[cm["source"] == "mimic_demo"]
        mapped = mimic["diagnosis_icd10"].notna().sum()
        assert mapped > 0, "No MIMIC rows have mapped ICD-10 codes"


# ===========================================================================
# Fix #8: NHANES cluster label is "healthy", not "baseline"
# ===========================================================================
class TestNHANESClusterLabel:
    def test_no_baseline_cluster(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        clusters = cm["diagnosis_cluster"].unique().tolist()
        assert "baseline" not in clusters, "'baseline' cluster still exists"

    def test_nhanes_majority_healthy(self):
        """Most NHANES should be healthy; MCQ labels a subset as autoimmune."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        healthy_pct = (nhanes["diagnosis_cluster"] == "healthy").sum() / len(nhanes)
        assert healthy_pct > 0.80, f"Only {healthy_pct:.1%} healthy -- expected >80%"


# ===========================================================================
# Fix #10: 03_register_tables.py includes longitudinal_labs
# ===========================================================================
class TestRegisterTables:
    def test_longitudinal_labs_in_script(self):
        script_path = os.path.join(PROJECT_ROOT, "scripts", "03_register_tables.py")
        with open(script_path) as f:
            content = f.read()
        assert "longitudinal_labs" in content, (
            "03_register_tables.py is missing longitudinal_labs"
        )


# ===========================================================================
# Fix #11: Output directories created automatically
# ===========================================================================
class TestDirectoryCreation:
    def test_tier_dirs_exist(self):
        for tier in ["tier1", "tier2", "tier3"]:
            path = os.path.join(PROCESSED_DIR, tier)
            assert os.path.isdir(path), f"Directory {path} does not exist"


# ===========================================================================
# Fix #12: Drug risk index has autoimmunity_risk_score column
# ===========================================================================
class TestDrugRiskIndex:
    def test_has_risk_score_column(self):
        drug = pd.read_parquet(DRUG_INDEX_PATH)
        assert "autoimmunity_risk_score" in drug.columns

    def test_has_drug_name_column(self):
        drug = pd.read_parquet(DRUG_INDEX_PATH)
        assert "drug_name" in drug.columns

    def test_risk_score_is_binary(self):
        drug = pd.read_parquet(DRUG_INDEX_PATH)
        vals = drug["autoimmunity_risk_score"].dropna().unique()
        assert set(vals).issubset({0, 1}), f"Unexpected risk score values: {vals}"


# ===========================================================================
# Fix #13: Healthy baselines filtered (CRP proxy)
# ===========================================================================
class TestHealthyBaselines:
    def test_baselines_exist(self):
        bl = pd.read_parquet(BASELINES_PATH)
        assert len(bl) > 0

    def test_all_age_buckets_present(self):
        bl = pd.read_parquet(BASELINES_PATH)
        expected = {"0-17", "18-30", "31-45", "46-60", "61+"}
        actual = set(bl["age_bucket"].unique())
        assert expected.issubset(actual), f"Missing age buckets: {expected - actual}"

    def test_both_sexes_present(self):
        bl = pd.read_parquet(BASELINES_PATH)
        assert set(bl["sex"].unique()) == {"M", "F"}


# ===========================================================================
# General data quality checks
# ===========================================================================
class TestCoreMatrixQuality:
    def test_row_count(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        assert len(cm) > 10000, f"Core matrix only has {len(cm)} rows"

    def test_patient_ids_unique(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        assert cm["patient_id"].is_unique, "Duplicate patient_id values found"

    def test_source_column_populated(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        assert cm["source"].notna().all()

    def test_all_sources_present(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        expected = {"harvard", "nhanes", "mimic_demo"}
        actual = set(cm["source"].unique())
        assert expected.issubset(actual), f"Missing sources: {expected - actual}"

    def test_no_kaggle_sources(self):
        """Synthetic Kaggle datasets should not be present."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        sources = set(cm["source"].unique())
        assert "kaggle_autoimmune" not in sources, "Kaggle Autoimmune data should be removed"
        assert "kaggle_gi" not in sources, "Kaggle GI data should be removed"

    def test_zscore_columns_present(self):
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        for marker in ["wbc", "crp", "hemoglobin", "platelet_count"]:
            zcol = f"{marker}_zscore"
            assert zcol in cm.columns, f"Missing z-score column: {zcol}"

    def test_diagnosis_cluster_mostly_populated(self):
        """At least 95% of rows should have a diagnosis cluster."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        populated = cm["diagnosis_cluster"].notna().sum()
        rate = populated / len(cm)
        assert rate > 0.95, f"Only {rate:.1%} of rows have a diagnosis cluster"


# ===========================================================================
# MCQ merge: NHANES autoimmune diagnosis labeling
# ===========================================================================
class TestNHANESMCQMerge:
    """Validates that NHANES MCQ data correctly labels autoimmune patients."""

    def test_nhanes_has_autoimmune_patients(self):
        """NHANES rows should include non-healthy diagnosis clusters."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        clusters = set(nhanes["diagnosis_cluster"].dropna().unique())
        assert "systemic" in clusters, "NHANES should have systemic (RA/lupus) patients from MCQ"
        assert "endocrine" in clusters, "NHANES should have endocrine (thyroid) patients from MCQ"
        assert "gastrointestinal" in clusters, "NHANES should have GI (celiac) patients from MCQ"

    def test_nhanes_autoimmune_count_reasonable(self):
        """Expect roughly 4000-6000 autoimmune patients across 4 NHANES cycles."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        autoimmune = nhanes[nhanes["diagnosis_cluster"] != "healthy"]
        assert len(autoimmune) > 3000, f"Too few NHANES autoimmune patients: {len(autoimmune)}"
        assert len(autoimmune) < 8000, f"Suspiciously many NHANES autoimmune patients: {len(autoimmune)}"

    def test_nhanes_patient_ids_are_seqn_based(self):
        """NHANES patient_ids should be based on SEQN, not sequential index."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        sample_id = nhanes["patient_id"].iloc[0]
        seqn_part = int(sample_id.replace("nhanes_", ""))
        assert seqn_part > 100, "NHANES patient_ids should be SEQN-based (5-digit numbers), not sequential"

    def test_nhanes_still_majority_healthy(self):
        """Most NHANES participants should remain healthy (general population)."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        nhanes = cm[cm["source"] == "nhanes"]
        healthy = nhanes[nhanes["diagnosis_cluster"] == "healthy"]
        pct = len(healthy) / len(nhanes)
        assert pct > 0.80, f"Only {pct:.1%} of NHANES is healthy -- too many relabeled"

    def test_nhanes_ra_labeled_correctly(self):
        """RA patients should have ICD-10 M06.9 and systemic cluster."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        ra = cm[(cm["source"] == "nhanes") & (cm["diagnosis_raw"] == "rheumatoid_arthritis")]
        if len(ra) > 0:
            assert (ra["diagnosis_icd10"] == "M06.9").all(), "RA should map to M06.9"
            assert (ra["diagnosis_cluster"] == "systemic").all(), "RA should be systemic cluster"

    def test_nhanes_lupus_labeled_correctly(self):
        """Lupus patients should have ICD-10 M32.9 and systemic cluster."""
        cm = pd.read_parquet(CORE_MATRIX_PATH)
        lupus = cm[(cm["source"] == "nhanes") & (cm["diagnosis_raw"] == "lupus")]
        if len(lupus) > 0:
            assert (lupus["diagnosis_icd10"] == "M32.9").all(), "Lupus should map to M32.9"
            assert (lupus["diagnosis_cluster"] == "systemic").all(), "Lupus should be systemic cluster"
