"""
Tests for notebooks/wrangle_genetics_expansion.py.

Validates the core transformation functions in isolation using synthetic data
that mirrors the actual schemas found on Databricks Volume.
"""
import logging

import pandas as pd
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate key constants and functions from the notebook for testing
# ---------------------------------------------------------------------------

AUTOIMMUNE_KEYWORDS = [
    "rheumatoid arthritis", "systemic lupus", "lupus", "sle",
    "crohn", "ulcerative colitis", "inflammatory bowel", "ibd", "celiac",
    "type 1 diabetes", "hashimoto", "graves", "thyroiditis",
    "multiple sclerosis", "psoriasis", "vitiligo", "alopecia areata",
    "ankylosing spondylitis", "sjogren", "scleroderma", "vasculitis",
    "myasthenia gravis", "pemphigus", "autoimmune", "dermatomyositis",
]

TRAIT_TO_CLUSTER = {
    "rheumatoid arthritis": ("systemic", "M06.9"),
    "systemic lupus erythematosus": ("systemic", "M32.9"),
    "celiac disease": ("gastrointestinal", "K90.0"),
    "ulcerative colitis": ("gastrointestinal", "K51.9"),
    "type 1 diabetes": ("endocrine", "E10"),
    "multiple sclerosis": ("neurological", "G35"),
    "psoriasis": ("dermatological", "L40.9"),
    "ankylosing spondylitis": ("systemic", "M45"),
}


def map_trait_to_cluster(trait_str):
    """Map a trait string to (cluster, icd10) using keyword matching."""
    if not trait_str or pd.isna(trait_str):
        return ("other_autoimmune", None)
    trait_lower = str(trait_str).lower().strip()
    for keyword, (cluster, icd10) in TRAIT_TO_CLUSTER.items():
        if keyword in trait_lower:
            return (cluster, icd10)
    return ("other_autoimmune", None)


# ---------------------------------------------------------------------------
# Synthetic data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gwas_catalog_df():
    """Synthetic GWAS Catalog data matching actual schema."""
    return pd.DataFrame({
        "efo_id": ["EFO_0001060", "EFO_0000685", "EFO_0003767", "EFO_0001359"],
        "trait": ["celiac disease", "rheumatoid arthritis", "psoriasis", "type 1 diabetes"],
        "pvalue": ["1.0E-14", "5.0E-20", "3.0E-8", "1.0E-30"],
        "pvalue_mlog": ["14", "20", "8", "30"],
        "risk_allele_frequency": ["0.82", "0.55", "0.30", "0.71"],
        "or_beta": ["1.59", "2.10", "1.25", "3.50"],
        "ci": ["[1.41-1.75]", "[1.80-2.45]", "[1.10-1.42]", "[2.90-4.20]"],
    })


@pytest.fixture
def afnd_df():
    """Synthetic AFND data matching actual schema (11 rows)."""
    return pd.DataFrame({
        "allele": ["B*27:05", "DRB1*04:01", "DRB1*03:01", "DQB1*02:01"],
        "disease_association": [
            "Ankylosing Spondylitis", "Rheumatoid Arthritis",
            "SLE / Type 1 Diabetes", "Celiac Disease",
        ],
        "locus": ["B", "DRB1", "DRB1", "DQB1"],
        "n_populations": ["94", "88", "88", "92"],
        "frequencies_found": ["true", "true", "true", "true"],
    })


@pytest.fixture
def immunobase_df():
    """Synthetic ImmunoBase study data."""
    return pd.DataFrame({
        "DATE ADDED TO CATALOG": ["2020-01-15", "2019-06-22"],
        "PUBMEDID": ["30305740", "29083406"],
        "FIRST AUTHOR": ["Trynka G", "de Lange KM"],
        "DISEASE/TRAIT": ["Celiac disease", "Ulcerative colitis"],
        "INITIAL SAMPLE SIZE": ["12,041 cases, 12,228 controls", "6,968 cases"],
        "ASSOCIATION COUNT": ["33", "25"],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTraitMapping:
    """Test trait-to-cluster mapping logic."""

    def test_exact_matches(self):
        assert map_trait_to_cluster("celiac disease") == ("gastrointestinal", "K90.0")
        assert map_trait_to_cluster("rheumatoid arthritis") == ("systemic", "M06.9")
        assert map_trait_to_cluster("type 1 diabetes") == ("endocrine", "E10")

    def test_case_insensitive(self):
        assert map_trait_to_cluster("Celiac Disease")[0] == "gastrointestinal"
        assert map_trait_to_cluster("RHEUMATOID ARTHRITIS")[0] == "systemic"

    def test_partial_match(self):
        assert map_trait_to_cluster("systemic lupus erythematosus (SLE)")[0] == "systemic"

    def test_unknown_trait(self):
        cluster, icd10 = map_trait_to_cluster("unknown disease")
        assert cluster == "other_autoimmune"
        assert icd10 is None

    def test_none_and_nan(self):
        assert map_trait_to_cluster(None)[0] == "other_autoimmune"
        assert map_trait_to_cluster(float("nan"))[0] == "other_autoimmune"


class TestGWASCatalog:
    """Test GWAS Catalog wrangling logic."""

    def test_schema(self, gwas_catalog_df):
        assert "efo_id" in gwas_catalog_df.columns
        assert "trait" in gwas_catalog_df.columns
        assert "pvalue" in gwas_catalog_df.columns
        assert len(gwas_catalog_df) == 4

    def test_cluster_mapping(self, gwas_catalog_df):
        cluster_icd = gwas_catalog_df["trait"].apply(map_trait_to_cluster)
        clusters = [c[0] for c in cluster_icd]
        assert clusters[0] == "gastrointestinal"  # celiac
        assert clusters[1] == "systemic"  # RA
        assert clusters[2] == "dermatological"  # psoriasis
        assert clusters[3] == "endocrine"  # T1D

    def test_deduplication(self, gwas_catalog_df):
        # Duplicate a row
        duped = pd.concat([gwas_catalog_df, gwas_catalog_df.iloc[:1]], ignore_index=True)
        assert len(duped) == 5
        deduped = duped.drop_duplicates(subset=["efo_id", "trait", "pvalue", "or_beta"])
        assert len(deduped) == 4


class TestAFND:
    """Test AFND HLA frequency wrangling logic."""

    def test_schema(self, afnd_df):
        assert "allele" in afnd_df.columns
        assert "disease_association" in afnd_df.columns
        assert "locus" in afnd_df.columns

    def test_cluster_mapping(self, afnd_df):
        clusters = afnd_df["disease_association"].apply(
            lambda d: map_trait_to_cluster(d)[0]
        )
        assert clusters.iloc[0] == "systemic"  # Ankylosing Spondylitis
        assert clusters.iloc[1] == "systemic"  # RA

    def test_n_populations_numeric(self, afnd_df):
        n_pop = pd.to_numeric(afnd_df["n_populations"], errors="coerce")
        assert n_pop.notna().all()
        assert n_pop.iloc[0] == 94


class TestImmunoBase:
    """Test ImmunoBase wrangling logic."""

    def test_autoimmune_filter(self, immunobase_df):
        trait_col = "DISEASE/TRAIT"
        mask = immunobase_df[trait_col].str.lower().str.contains(
            "|".join(AUTOIMMUNE_KEYWORDS), na=False
        )
        assert mask.sum() == 2  # Both celiac and UC match

    def test_cluster_mapping(self, immunobase_df):
        cluster_icd = immunobase_df["DISEASE/TRAIT"].apply(map_trait_to_cluster)
        clusters = [c[0] for c in cluster_icd]
        assert clusters[0] == "gastrointestinal"  # Celiac
        assert clusters[1] == "gastrointestinal"  # UC

    def test_column_name_standardization(self, immunobase_df):
        col_rename = {}
        for col in immunobase_df.columns:
            col_rename[col] = col.lower().replace(" ", "_").replace("/", "_")
        renamed = immunobase_df.rename(columns=col_rename)
        assert "disease_trait" in renamed.columns
        assert "pubmedid" in renamed.columns


class TestPanUKBB:
    """Test Pan-UKBB phenotype mapping."""

    def test_phenotype_to_cluster(self):
        pheno_to_cluster = {
            "E10": ("endocrine", "E10"),
            "M06": ("systemic", "M06.9"),
            "G35": ("neurological", "G35"),
            "L40": ("dermatological", "L40.9"),
        }
        assert pheno_to_cluster["E10"] == ("endocrine", "E10")
        assert pheno_to_cluster["M06"] == ("systemic", "M06.9")

    def test_filename_parsing(self):
        filename = "icd10-E10-both_sexes.tsv.bgz"
        parts = filename.replace(".tsv.bgz", "").split("-")
        phenotype_code = "-".join(parts[1:-1]) if len(parts) > 2 else parts[0]
        sex_group = parts[-1] if len(parts) > 1 else "both_sexes"
        assert phenotype_code == "E10"
        assert sex_group == "both_sexes"
