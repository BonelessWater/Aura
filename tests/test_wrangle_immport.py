"""
Tests for the ImmPort study wrangler in scripts/02_wrangle_data.py.
Validates the generic wrangle_immport_study() function and wrangle_all_immport().
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

import importlib
wrangle = importlib.import_module("02_wrangle_data")

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
CORE_MATRIX_PATH = os.path.join(PROCESSED_DIR, "tier1", "core_matrix.parquet")
AUTOANTIBODY_PATH = os.path.join(PROCESSED_DIR, "tier2", "autoantibody_panel.parquet")
LONGITUDINAL_PATH = os.path.join(PROCESSED_DIR, "tier2", "longitudinal_labs.parquet")
IMMPORT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "immport")

pytestmark = pytest.mark.skipif(
    not os.path.exists(CORE_MATRIX_PATH),
    reason="Processed parquet files not found -- run the pipeline first",
)


# ===========================================================================
# Configuration tests
# ===========================================================================
class TestImmPortConfig:
    """Validate study configuration and lab name mappings."""

    def test_all_studies_have_required_config(self):
        for study_id, config in wrangle.IMMPORT_STUDIES.items():
            assert "diagnosis_raw" in config, f"{study_id} missing diagnosis_raw"
            assert "diagnosis_icd10" in config, f"{study_id} missing diagnosis_icd10"

    def test_all_icd10_codes_map_to_clusters(self):
        for study_id, config in wrangle.IMMPORT_STUDIES.items():
            icd10 = config["diagnosis_icd10"]
            assert icd10 in wrangle.ICD10_TO_CLUSTER, (
                f"{study_id} ICD-10 code {icd10} not in ICD10_TO_CLUSTER"
            )

    def test_lab_name_map_has_core_columns(self):
        core_cols = {"wbc", "rbc", "hemoglobin", "hematocrit", "platelet_count",
                     "mcv", "mch", "rdw", "crp", "esr",
                     "neutrophil_pct", "lymphocyte_pct"}
        mapped_cols = set(wrangle.IMMPORT_LAB_NAME_MAP.values())
        assert core_cols == mapped_cols, (
            f"Missing: {core_cols - mapped_cols}, Extra: {mapped_cols - core_cols}"
        )

    def test_no_duplicate_lab_mappings_to_different_columns(self):
        seen = {}
        for name, col in wrangle.IMMPORT_LAB_NAME_MAP.items():
            if name in seen and seen[name] != col:
                pytest.fail(
                    f"Lab name '{name}' maps to both '{seen[name]}' and '{col}'"
                )
            seen[name] = col


# ===========================================================================
# Core matrix output tests
# ===========================================================================
class TestImmPortCoreMatrix:
    """Validate the wrangled core_matrix parquet output."""

    @pytest.fixture(scope="class")
    def core_df(self):
        return pd.read_parquet(CORE_MATRIX_PATH)

    def test_has_immport_sources(self, core_df):
        immport_sources = core_df[core_df["source"].str.startswith("immport_")]["source"].unique()
        assert len(immport_sources) >= 1, "No ImmPort sources found in core_matrix"

    def test_immport_row_count(self, core_df):
        immport_rows = core_df[core_df["source"].str.startswith("immport_")]
        assert len(immport_rows) >= 600, (
            f"Expected >= 600 ImmPort rows, got {len(immport_rows)}"
        )

    def test_patient_ids_are_unique(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        assert immport["patient_id"].is_unique, "Duplicate patient_ids in ImmPort data"

    def test_patient_id_format(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        for pid in immport["patient_id"]:
            assert pid.startswith("immport_sdy"), (
                f"Patient ID '{pid}' does not start with 'immport_sdy'"
            )

    def test_all_have_diagnosis(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        assert immport["diagnosis_raw"].notna().all(), "Some ImmPort rows missing diagnosis_raw"
        assert immport["diagnosis_icd10"].notna().all(), "Some ImmPort rows missing diagnosis_icd10"
        assert immport["diagnosis_cluster"].notna().all(), "Some ImmPort rows missing diagnosis_cluster"

    def test_hemoglobin_in_valid_range(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        hgb = immport["hemoglobin"].dropna()
        if len(hgb) > 0:
            assert hgb.min() > 3.0, f"Hemoglobin too low: {hgb.min()}"
            assert hgb.max() < 25.0, f"Hemoglobin too high: {hgb.max()}"

    def test_wbc_in_valid_range(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        wbc = immport["wbc"].dropna()
        if len(wbc) > 0:
            assert wbc.min() >= 0.1, f"WBC too low: {wbc.min()}"
            assert wbc.max() < 100.0, f"WBC too high (wrong units?): {wbc.max()}"

    def test_platelet_count_in_valid_range(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        plt_ct = immport["platelet_count"].dropna()
        if len(plt_ct) > 0:
            assert plt_ct.min() >= 10, f"Platelet count too low: {plt_ct.min()}"
            assert plt_ct.max() < 2000, f"Platelet count too high (wrong units?): {plt_ct.max()}"

    def test_sex_values(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        valid_sex = immport["sex"].dropna().unique()
        for v in valid_sex:
            assert v in ("M", "F"), f"Invalid sex value: {v}"

    def test_age_in_valid_range(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        age = immport["age"].dropna()
        if len(age) > 0:
            assert age.min() >= 0, f"Negative age: {age.min()}"
            assert age.max() <= 120, f"Age too high: {age.max()}"

    def test_disease_clusters_are_valid(self, core_df):
        immport = core_df[core_df["source"].str.startswith("immport_")]
        valid_clusters = set(wrangle.ICD10_TO_CLUSTER.values())
        for cluster in immport["diagnosis_cluster"].dropna().unique():
            assert cluster in valid_clusters, f"Invalid cluster: {cluster}"


# ===========================================================================
# Autoantibody extension tests
# ===========================================================================
class TestImmPortAutoantibody:
    """Validate the autoantibody panel extension."""

    @pytest.fixture(scope="class")
    def ab_df(self):
        if not os.path.exists(AUTOANTIBODY_PATH):
            pytest.skip("Autoantibody parquet not found")
        return pd.read_parquet(AUTOANTIBODY_PATH)

    def test_has_immport_rows(self, ab_df):
        immport = ab_df[ab_df["patient_id"].str.startswith("immport_")]
        assert len(immport) > 0, "No ImmPort rows in autoantibody_panel"

    def test_patient_ids_exist_in_core(self, ab_df):
        core_df = pd.read_parquet(CORE_MATRIX_PATH)
        immport_ab = ab_df[ab_df["patient_id"].str.startswith("immport_")]
        core_pids = set(core_df["patient_id"])
        for pid in immport_ab["patient_id"]:
            assert pid in core_pids, (
                f"Autoantibody patient_id '{pid}' not found in core_matrix"
            )


# ===========================================================================
# Longitudinal labs tests
# ===========================================================================
class TestImmPortLongitudinal:
    """Validate the longitudinal labs extension."""

    @pytest.fixture(scope="class")
    def long_df(self):
        if not os.path.exists(LONGITUDINAL_PATH):
            pytest.skip("Longitudinal parquet not found")
        return pd.read_parquet(LONGITUDINAL_PATH)

    def test_has_immport_rows(self, long_df):
        immport = long_df[long_df["source"].str.startswith("immport_")]
        assert len(immport) > 0, "No ImmPort rows in longitudinal_labs"

    def test_lab_items_are_valid(self, long_df):
        immport = long_df[long_df["source"].str.startswith("immport_")]
        valid_items = set(wrangle.IMMPORT_LAB_NAME_MAP.values())
        for item in immport["lab_item"].dropna().unique():
            assert item in valid_items, f"Unknown lab_item: {item}"

    def test_more_longitudinal_than_core(self, long_df):
        core_df = pd.read_parquet(CORE_MATRIX_PATH)
        immport_core = core_df[core_df["source"].str.startswith("immport_")]
        immport_long = long_df[long_df["source"].str.startswith("immport_")]
        assert len(immport_long) > len(immport_core), (
            "Longitudinal should have more records than core (multiple timepoints)"
        )


# ===========================================================================
# Per-study wrangler smoke tests
# ===========================================================================
class TestPerStudyWrangler:
    """Test that individual studies can be wrangled without errors."""

    @pytest.fixture(scope="class")
    def available_studies(self):
        available = []
        for study_id in wrangle.IMMPORT_STUDIES:
            tab_dir = wrangle._find_immport_tab_dir(study_id)
            if tab_dir is not None:
                available.append(study_id)
        return available

    def test_at_least_one_study_available(self, available_studies):
        assert len(available_studies) >= 1, "No ImmPort study data found in raw dir"

    def test_each_study_produces_core_rows(self, available_studies):
        for study_id in available_studies:
            config = wrangle.IMMPORT_STUDIES[study_id]
            core, ab, longitudinal = wrangle.wrangle_immport_study(study_id, config)
            assert core is not None, f"{study_id} returned None core"
            assert len(core) > 0, f"{study_id} returned empty core"
            assert "patient_id" in core.columns, f"{study_id} missing patient_id"
            assert "source" in core.columns, f"{study_id} missing source"
            assert core["source"].iloc[0].startswith("immport_"), (
                f"{study_id} source doesn't start with immport_"
            )
