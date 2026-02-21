"""
Tests for the HugeAmp GWAS wrangling logic in
notebooks/wrangle_additional_datasets.py.

Since the notebook runs on Databricks, these tests validate the
core transformation functions in isolation using synthetic data
that mirrors the HugeAmp API response structure.
"""
import logging

import pandas as pd
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate the key constants and functions from the notebook so we can test
# them without a Databricks runtime.
# ---------------------------------------------------------------------------

HUGEAMP_CLUSTER_MAP = {
    "T1D": ("endocrine", "E10"),
    "RhA": ("rheumatological", "M06.9"),
    "SLE": ("rheumatological", "M32.9"),
    "CD": ("gastrointestinal", "K50.9"),
    "UC": ("gastrointestinal", "K51.9"),
    "IBD": ("gastrointestinal", "K50.9"),
    "MultipleSclerosis": ("neurological", "G35"),
    "Psoriasis": ("dermatological", "L40.9"),
    "Celiac": ("gastrointestinal", "K90.0"),
    "Graves": ("endocrine", "E05.0"),
    "Vitiligo": ("dermatological", "L80"),
    "LADA": ("endocrine", "E10"),
    "Addison": ("endocrine", "E27.1"),
}

FINNGEN_CLUSTER_MAP = {
    "M13_RHEUMA": ("rheumatological", "M06.9"),
    "SLE_FG": ("rheumatological", "M32.9"),
    "K11_IBD_STRICT": ("gastrointestinal", "K50.9"),
    "E4_THYROIDITAUTOIM": ("endocrine", "E06.3"),
    "L12_PSORIASIS": ("dermatological", "L40.9"),
}


def clean_nearest_column(df):
    """Convert 'nearest' from list to comma-separated string."""
    if "nearest" in df.columns:
        df["nearest"] = df["nearest"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else str(x) if pd.notna(x) else ""
        )
    return df


def drop_af_dict_column(df):
    """Drop 'af' column if it contains dicts; keep 'maf' instead."""
    if "af" in df.columns:
        af_sample = df["af"].dropna().iloc[0] if len(df["af"].dropna()) > 0 else None
        if isinstance(af_sample, dict):
            df = df.drop(columns=["af"])
    return df


def build_hugeamp_rows(gwas_df):
    """Build standardized rows from HugeAmp data (lowercased columns)."""
    rows = []
    for _, row in gwas_df.iterrows():
        phenotype = row.get("queried_phenotype", "")
        cluster_info = HUGEAMP_CLUSTER_MAP.get(phenotype, ("", ""))
        rows.append({
            "source": "hugeamp",
            "variant_id": row.get("varid", row.get("dbsnp", "")),
            "gene": row.get("nearest", ""),
            "chrom": str(row.get("chromosome", "")),
            "pos": row.get("position", None),
            "ref": row.get("reference", ""),
            "alt": row.get("alt", ""),
            "pvalue": row.get("pvalue", None),
            "beta": row.get("beta", None),
            "se": row.get("stderr", None),
            "af": row.get("maf", None),
            "finngen_endpoint": "",
            "diagnosis_cluster": cluster_info[0],
            "diagnosis_icd10": cluster_info[1],
            "queried_phenotype": phenotype,
        })
    return rows


# ---------------------------------------------------------------------------
# Fixtures: synthetic HugeAmp data mirroring actual API response
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_hugeamp_record():
    """Single HugeAmp API response record (original camelCase)."""
    return {
        "varId": "11:2176105:A:G",
        "alt": "G",
        "ancestry": "Mixed",
        "beta": 0.6205,
        "chromosome": "11",
        "dataset": "bottom-line_analysis_T1D_Mixed",
        "n": 166189.0,
        "pValue": 5e-324,
        "phenotype": "T1D",
        "position": 2176105,
        "posteriorProbability": 0.091,
        "reference": "A",
        "source": "bottom-line_analysis_common",
        "stdErr": 0.0116,
        "dbSNP": "rs7110099",
        "consequence": "intron_variant",
        "nearest": ["IGF2"],
        "minorAllele": "A",
        "maf": 0.2115,
        "af": {"AA": 0.5983, "EA": 0.9544, "EU": 0.7803},
        "queried_phenotype": "T1D",
        "queried_label": "Type 1 Diabetes",
    }


@pytest.fixture
def hugeamp_df(raw_hugeamp_record):
    """DataFrame with multiple HugeAmp records, columns lowercased."""
    records = []
    for pheno in ["T1D", "SLE", "MultipleSclerosis", "Psoriasis", "Addison"]:
        rec = raw_hugeamp_record.copy()
        rec["queried_phenotype"] = pheno
        rec["phenotype"] = pheno
        rec["nearest"] = ["GENE1", "GENE2"] if pheno == "SLE" else ["IGF2"]
        records.append(rec)

    df = pd.DataFrame(records)
    # Lowercase columns (same as wrangle_gwas)
    col_map = {col: col.lower().replace(" ", "_") for col in df.columns}
    df = df.rename(columns=col_map)
    return df


# ===========================================================================
# Tests
# ===========================================================================

class TestHugeAmpClusterMap:
    """All 13 HugeAmp phenotypes must map to valid clusters."""

    def test_all_phenotypes_have_cluster(self):
        for pheno, (cluster, icd10) in HUGEAMP_CLUSTER_MAP.items():
            assert cluster, f"{pheno} has empty cluster"
            assert icd10, f"{pheno} has empty ICD-10"

    def test_cluster_names_match_finngen(self):
        """Clusters used for overlapping conditions should be consistent."""
        # RA -> rheumatological in both
        assert HUGEAMP_CLUSTER_MAP["RhA"][0] == FINNGEN_CLUSTER_MAP["M13_RHEUMA"][0]
        # SLE -> rheumatological in both
        assert HUGEAMP_CLUSTER_MAP["SLE"][0] == FINNGEN_CLUSTER_MAP["SLE_FG"][0]
        # IBD -> gastrointestinal in both
        assert HUGEAMP_CLUSTER_MAP["IBD"][0] == FINNGEN_CLUSTER_MAP["K11_IBD_STRICT"][0]
        # Psoriasis -> dermatological in both
        assert HUGEAMP_CLUSTER_MAP["Psoriasis"][0] == FINNGEN_CLUSTER_MAP["L12_PSORIASIS"][0]

    def test_expected_cluster_count(self):
        clusters = set(c for c, _ in HUGEAMP_CLUSTER_MAP.values())
        assert len(clusters) == 5, f"Expected 5 unique clusters, got {clusters}"


class TestNearestColumnCleaning:
    """The 'nearest' field from HugeAmp is a list; must become a string."""

    def test_list_to_string(self):
        df = pd.DataFrame({"nearest": [["IGF2"], ["HLA-A", "HLA-B"]]})
        result = clean_nearest_column(df)
        assert result["nearest"].iloc[0] == "IGF2"
        assert result["nearest"].iloc[1] == "HLA-A,HLA-B"

    def test_already_string(self):
        df = pd.DataFrame({"nearest": ["IGF2", "HLA-A"]})
        result = clean_nearest_column(df)
        assert result["nearest"].iloc[0] == "IGF2"

    def test_nan_handling(self):
        df = pd.DataFrame({"nearest": [["IGF2"], None]})
        result = clean_nearest_column(df)
        assert result["nearest"].iloc[0] == "IGF2"
        assert result["nearest"].iloc[1] == ""

    def test_no_nearest_column(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = clean_nearest_column(df)
        assert "nearest" not in result.columns


class TestAfDictDropping:
    """The 'af' field is a dict of ancestry frequencies; should be dropped."""

    def test_dict_af_dropped(self):
        df = pd.DataFrame({
            "af": [{"EA": 0.95, "AA": 0.60}, {"EA": 0.80, "AA": 0.70}],
            "maf": [0.21, 0.15],
        })
        result = drop_af_dict_column(df)
        assert "af" not in result.columns
        assert "maf" in result.columns

    def test_scalar_af_kept(self):
        df = pd.DataFrame({"af": [0.21, 0.15]})
        result = drop_af_dict_column(df)
        assert "af" in result.columns


class TestBuildHugeAmpRows:
    """Test the row-building logic that maps lowercased HugeAmp columns."""

    def test_column_mapping(self, hugeamp_df):
        cleaned = clean_nearest_column(hugeamp_df.copy())
        cleaned = drop_af_dict_column(cleaned)
        rows = build_hugeamp_rows(cleaned)
        assert len(rows) == 5

        t1d_row = rows[0]
        assert t1d_row["source"] == "hugeamp"
        assert t1d_row["variant_id"] == "11:2176105:A:G"
        assert t1d_row["gene"] == "IGF2"
        assert t1d_row["chrom"] == "11"
        assert t1d_row["pos"] == 2176105
        assert t1d_row["ref"] == "A"
        assert t1d_row["alt"] == "G"
        assert t1d_row["pvalue"] == 5e-324
        assert t1d_row["beta"] == 0.6205
        assert t1d_row["se"] == 0.0116
        assert t1d_row["af"] == 0.2115

    def test_cluster_assignment(self, hugeamp_df):
        cleaned = clean_nearest_column(hugeamp_df.copy())
        cleaned = drop_af_dict_column(cleaned)
        rows = build_hugeamp_rows(cleaned)

        # T1D -> endocrine
        assert rows[0]["diagnosis_cluster"] == "endocrine"
        assert rows[0]["diagnosis_icd10"] == "E10"

        # SLE -> rheumatological
        assert rows[1]["diagnosis_cluster"] == "rheumatological"
        assert rows[1]["diagnosis_icd10"] == "M32.9"

        # MultipleSclerosis -> neurological
        assert rows[2]["diagnosis_cluster"] == "neurological"
        assert rows[2]["diagnosis_icd10"] == "G35"

        # Psoriasis -> dermatological
        assert rows[3]["diagnosis_cluster"] == "dermatological"

        # Addison -> endocrine
        assert rows[4]["diagnosis_cluster"] == "endocrine"
        assert rows[4]["diagnosis_icd10"] == "E27.1"

    def test_multi_gene_nearest(self, hugeamp_df):
        """SLE record has nearest=["GENE1","GENE2"], should become comma-separated."""
        cleaned = clean_nearest_column(hugeamp_df.copy())
        cleaned = drop_af_dict_column(cleaned)
        rows = build_hugeamp_rows(cleaned)
        sle_row = rows[1]
        assert sle_row["gene"] == "GENE1,GENE2"

    def test_queried_phenotype_preserved(self, hugeamp_df):
        cleaned = clean_nearest_column(hugeamp_df.copy())
        cleaned = drop_af_dict_column(cleaned)
        rows = build_hugeamp_rows(cleaned)
        phenotypes = [r["queried_phenotype"] for r in rows]
        assert phenotypes == ["T1D", "SLE", "MultipleSclerosis", "Psoriasis", "Addison"]

    def test_unknown_phenotype_gets_empty_cluster(self):
        """A phenotype not in HUGEAMP_CLUSTER_MAP should get empty cluster."""
        df = pd.DataFrame([{
            "varid": "1:1000:A:T",
            "nearest": "GENE",
            "chromosome": "1",
            "position": 1000,
            "reference": "A",
            "alt": "T",
            "pvalue": 1e-10,
            "beta": 0.5,
            "stderr": 0.01,
            "maf": 0.1,
            "dbsnp": "rs123",
            "queried_phenotype": "UnknownDisease",
        }])
        rows = build_hugeamp_rows(df)
        assert rows[0]["diagnosis_cluster"] == ""
        assert rows[0]["diagnosis_icd10"] == ""


class TestFinnGenHugeAmpSchemaCompatibility:
    """FinnGen and HugeAmp rows must produce compatible schemas."""

    def test_shared_columns(self, hugeamp_df):
        """Both sources must have the same output columns."""
        cleaned = clean_nearest_column(hugeamp_df.copy())
        cleaned = drop_af_dict_column(cleaned)
        hugeamp_rows = build_hugeamp_rows(cleaned)

        finngen_row = {
            "source": "finngen_r12",
            "variant_id": "rs123",
            "gene": "HLA-A",
            "chrom": "6",
            "pos": 123456,
            "ref": "A",
            "alt": "G",
            "pvalue": 1e-10,
            "beta": 0.5,
            "se": 0.01,
            "af": 0.1,
            "finngen_endpoint": "M13_RHEUMA",
            "diagnosis_cluster": "rheumatological",
            "diagnosis_icd10": "M06.9",
        }

        # All FinnGen columns must be in HugeAmp rows (except queried_phenotype)
        for col in finngen_row:
            assert col in hugeamp_rows[0], f"HugeAmp row missing FinnGen column: {col}"
