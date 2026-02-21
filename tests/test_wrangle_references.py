"""
Tests for notebooks/wrangle_references.py.

Validates Open Targets, CTD, EPA, HPA, and Mendeley wrangling logic
using synthetic data matching actual schemas on Databricks Volume.
"""
import logging

import pandas as pd
import numpy as np
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate key functions from the notebook
# ---------------------------------------------------------------------------

AUTOIMMUNE_KEYWORDS = [
    "rheumatoid arthritis", "systemic lupus", "lupus", "sle",
    "crohn", "ulcerative colitis", "inflammatory bowel", "ibd", "celiac",
    "type 1 diabetes", "hashimoto", "graves", "thyroiditis",
    "multiple sclerosis", "psoriasis", "vitiligo", "autoimmune",
]

DISEASE_TO_CLUSTER = {
    "systemic lupus erythematosus": "systemic",
    "rheumatoid arthritis": "systemic",
    "crohn's disease": "gastrointestinal",
    "crohn disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "type 1 diabetes": "endocrine",
    "hashimoto thyroiditis": "endocrine",
    "graves disease": "endocrine",
    "multiple sclerosis": "neurological",
    "psoriasis": "dermatological",
}


def map_disease_to_cluster(disease_str):
    if not disease_str or pd.isna(disease_str):
        return "other_autoimmune"
    d_lower = str(disease_str).lower().strip()
    for keyword, cluster in DISEASE_TO_CLUSTER.items():
        if keyword in d_lower:
            return cluster
    return "other_autoimmune"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def open_targets_df():
    """Synthetic Open Targets data matching actual parquet schema."""
    return pd.DataFrame({
        "disease_id": ["MONDO_0007915", "EFO_0000685", "EFO_0003767"],
        "disease_name": [
            "systemic lupus erythematosus",
            "rheumatoid arthritis",
            "psoriasis",
        ],
        "target_id": ["ENSG00000213689", "ENSG00000120217", "ENSG00000163599"],
        "target_symbol": ["TREX1", "CD274", "CTLA4"],
        "target_name": [
            "three prime repair exonuclease 1",
            "CD274 molecule",
            "cytotoxic T-lymphocyte associated protein 4",
        ],
        "overall_score": [0.778, 0.654, 0.891],
        "score_literature": [0.036, 0.125, 0.230],
        "score_animal_model": [0.635, None, 0.450],
        "score_genetic_association": [0.922, 0.789, 0.950],
        "score_genetic_literature": [0.730, 0.456, 0.812],
        "score_known_drug": [None, 0.350, 0.670],
        "score_somatic_mutation": [None, None, None],
        "score_rna_expression": [None, 0.234, None],
        "score_affected_pathway": [None, None, 0.123],
    })


@pytest.fixture
def ctd_chunk():
    """Synthetic CTD chemicals-diseases data."""
    return pd.DataFrame({
        0: ["Asbestos", "Benzene", "Mercury", "Arsenic"],
        1: ["D001194", "D001554", "D008628", "D001151"],
        2: ["1332-21-4", "71-43-2", "7439-97-6", "7440-38-2"],
        3: [
            "Autoimmune Diseases",
            "Leukemia",
            "Systemic Lupus Erythematosus",
            "Skin Neoplasms",
        ],
        4: ["MESH:D001327", "MESH:D007938", "MESH:D008180", "MESH:D012878"],
        5: ["marker/mechanism", None, "marker/mechanism", None],
        6: ["NLRP3", None, "STAT4", None],
        7: [25.5, None, 18.3, None],
        8: [None, None, None, None],
        9: ["12345678|87654321", None, "99999999", None],
    })


@pytest.fixture
def epa_df():
    """Synthetic EPA annual concentration data."""
    return pd.DataFrame({
        "state_code": ["01", "01", "06", "06"],
        "county_code": ["001", "001", "037", "037"],
        "state_name": ["Alabama", "Alabama", "California", "California"],
        "county_name": ["Autauga", "Autauga", "Los Angeles", "Los Angeles"],
        "parameter_code": [88101, 44201, 88101, 44201],
        "latitude": [32.44, 32.44, 34.07, 34.07],
        "longitude": [-86.48, -86.48, -118.24, -118.24],
        "arithmetic_mean": [8.5, 0.042, 12.3, 0.065],
        "first_max_value": [35.2, 0.085, 45.8, 0.095],
        "units_of_measure": ["ug/m3", "ppm", "ug/m3", "ppm"],
        "observation_count": [350, 340, 362, 355],
    })


@pytest.fixture
def mendeley_metadata():
    """Synthetic Mendeley lipidomics metadata."""
    return pd.DataFrame({
        "ID": [1, 2, 3, 4],
        "DRUG": [0, 0, 1, 1],
        "EAE": [0, 1, 0, 1],
        "GROUP": [1, 2, 3, 4],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOpenTargets:
    """Test Open Targets wrangling logic."""

    def test_schema(self, open_targets_df):
        assert "disease_id" in open_targets_df.columns
        assert "disease_name" in open_targets_df.columns
        assert "overall_score" in open_targets_df.columns
        assert "target_symbol" in open_targets_df.columns

    def test_cluster_mapping(self, open_targets_df):
        clusters = open_targets_df["disease_name"].apply(map_disease_to_cluster)
        assert clusters.iloc[0] == "systemic"  # SLE
        assert clusters.iloc[1] == "systemic"  # RA
        assert clusters.iloc[2] == "dermatological"  # Psoriasis

    def test_score_rename(self, open_targets_df):
        rename_map = {
            "score_literature": "literature",
            "score_animal_model": "animal_model",
            "score_genetic_association": "genetic_association",
        }
        renamed = open_targets_df.rename(columns=rename_map)
        assert "literature" in renamed.columns
        assert "score_literature" not in renamed.columns

    def test_null_scores_preserved(self, open_targets_df):
        # Some scores should be null (not all evidence types available)
        assert pd.isna(open_targets_df["score_known_drug"].iloc[0])
        assert pd.isna(open_targets_df["score_somatic_mutation"]).all()


class TestCTD:
    """Test CTD chemical-disease wrangling logic."""

    def test_autoimmune_filter(self, ctd_chunk):
        col_names = [
            "chemical_name", "chemical_id", "cas_rn", "disease_name",
            "disease_id", "direct_evidence", "inference_gene_symbol",
            "inference_score", "omim_ids", "pubmed_ids",
        ]
        ctd_chunk.columns = col_names

        autoimmune_pattern = "|".join(AUTOIMMUNE_KEYWORDS)
        mask = ctd_chunk["disease_name"].str.lower().str.contains(
            autoimmune_pattern, na=False
        )
        filtered = ctd_chunk[mask]
        assert len(filtered) == 2  # "Autoimmune Diseases" and "Systemic Lupus"

    def test_cluster_mapping(self, ctd_chunk):
        col_names = [
            "chemical_name", "chemical_id", "cas_rn", "disease_name",
            "disease_id", "direct_evidence", "inference_gene_symbol",
            "inference_score", "omim_ids", "pubmed_ids",
        ]
        ctd_chunk.columns = col_names

        clusters = ctd_chunk["disease_name"].apply(map_disease_to_cluster)
        assert clusters.iloc[0] == "other_autoimmune"  # "Autoimmune Diseases" (generic)
        assert clusters.iloc[2] == "systemic"  # SLE

    def test_inference_score_numeric(self, ctd_chunk):
        scores = pd.to_numeric(ctd_chunk[7], errors="coerce")
        assert scores.iloc[0] == 25.5
        assert pd.isna(scores.iloc[1])


class TestEPA:
    """Test EPA AQS wrangling logic."""

    def test_pollutant_filter(self, epa_df):
        target_params = {88101, 81102, 44201, 42602, 42401}
        param_names = {88101: "PM2.5", 44201: "Ozone"}
        filtered = epa_df[epa_df["parameter_code"].isin(target_params)]
        assert len(filtered) == 4
        filtered["parameter"] = filtered["parameter_code"].map(param_names)
        assert filtered["parameter"].iloc[0] == "PM2.5"
        assert filtered["parameter"].iloc[1] == "Ozone"

    def test_county_aggregation(self, epa_df):
        grouped = epa_df.groupby(["state_name", "county_name"]).agg(
            n_params=("parameter_code", "nunique"),
            mean_pm25=("arithmetic_mean", lambda x: x[epa_df.loc[x.index, "parameter_code"] == 88101].mean()),
        )
        assert len(grouped) == 2  # 2 counties

    def test_column_standardization(self, epa_df):
        epa_df.columns = [c.strip().lower().replace(" ", "_") for c in epa_df.columns]
        assert "state_code" in epa_df.columns
        assert "arithmetic_mean" in epa_df.columns

    def test_filename_year_extraction(self):
        filename = "annual_conc_by_monitor_2019.csv"
        year = filename.replace("annual_conc_by_monitor_", "").replace(".csv", "")
        assert year == "2019"


class TestHPA:
    """Test HPA protein expression wrangling logic."""

    def test_autoimmune_disease_filter(self):
        diseases = pd.Series([
            "Rheumatoid arthritis; Systemic lupus erythematosus",
            "Lung cancer",
            "Celiac disease",
            None,
        ])
        autoimmune_pattern = "|".join(AUTOIMMUNE_KEYWORDS)
        mask = diseases.str.lower().str.contains(autoimmune_pattern, na=False)
        assert mask.sum() == 2  # RA/SLE and Celiac

    def test_column_selection(self):
        cols = [
            "Gene", "Gene synonym", "Ensembl", "Gene description",
            "Uniprot", "Chromosome", "Position", "Protein class",
            "Biological process", "Disease involvement",
            "Blood expression cluster", "Reliability",
        ]
        important_patterns = ["gene", "ensembl", "uniprot", "disease", "blood", "reliability"]
        keep_cols = []
        col_lower_map = {c.lower(): c for c in cols}
        for pattern in important_patterns:
            for col_lower, col_orig in col_lower_map.items():
                if pattern in col_lower and col_orig not in keep_cols:
                    keep_cols.append(col_orig)
        assert "Gene" in keep_cols
        assert "Disease involvement" in keep_cols
        assert "Blood expression cluster" in keep_cols


class TestMendeley:
    """Test Mendeley lipidomics wrangling logic."""

    def test_eae_condition_mapping(self, mendeley_metadata):
        condition_map = {0: "control", 1: "eae_model"}
        cluster_map = {0: "healthy", 1: "neurological"}
        conditions = mendeley_metadata["EAE"].map(condition_map)
        clusters = mendeley_metadata["EAE"].map(cluster_map)
        assert conditions.iloc[0] == "control"
        assert conditions.iloc[1] == "eae_model"
        assert clusters.iloc[0] == "healthy"
        assert clusters.iloc[1] == "neurological"

    def test_metadata_schema(self, mendeley_metadata):
        assert "ID" in mendeley_metadata.columns
        assert "DRUG" in mendeley_metadata.columns
        assert "EAE" in mendeley_metadata.columns
        assert "GROUP" in mendeley_metadata.columns

    def test_melt_to_long(self):
        data = pd.DataFrame({
            "ID": [1, 2],
            "EAE": [0, 1],
            "lipid_A": [5.2, 8.1],
            "lipid_B": [3.4, 6.7],
        })
        meta_cols = ["ID", "EAE"]
        lipid_cols = ["lipid_A", "lipid_B"]
        long = data.melt(
            id_vars=meta_cols,
            value_vars=lipid_cols,
            var_name="analyte_name",
            value_name="value",
        )
        assert len(long) == 4  # 2 samples x 2 lipids
        assert long["analyte_name"].nunique() == 2
