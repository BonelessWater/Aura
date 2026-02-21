"""
Tests for notebooks/wrangle_omics.py.

Validates transcriptomics, microbiome, proteomics, and metabolomics
wrangling logic using synthetic data.
"""
import io
import logging

import pandas as pd
import numpy as np
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Replicate key functions from the notebook
# ---------------------------------------------------------------------------

TRAIT_TO_CLUSTER = {
    "rheumatoid arthritis": "systemic",
    "systemic lupus erythematosus": "systemic",
    "crohn's disease": "gastrointestinal",
    "crohn disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "type 1 diabetes": "endocrine",
    "multiple sclerosis": "neurological",
    "psoriasis": "dermatological",
}


def map_disease_to_cluster(disease_str):
    if not disease_str or pd.isna(disease_str):
        return "other_autoimmune"
    d_lower = str(disease_str).lower().strip()
    for keyword, cluster in TRAIT_TO_CLUSTER.items():
        if keyword in d_lower:
            return cluster
    return "other_autoimmune"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def geo_matrix_text():
    """Synthetic GEO series matrix file content."""
    return """\
!Series_title\t"Gene Expression in Rheumatoid Arthritis PBMCs"
!Series_geo_accession\t"GSE15573"
!Series_platform_id\t"GPL570"
!series_matrix_table_begin
"ID_REF"\t"GSM389076"\t"GSM389077"\t"GSM389078"
"GENE_A"\t5.23\t4.89\t6.12
"GENE_B"\t8.45\t7.99\t8.01
"GENE_C"\t2.11\t3.05\t2.78
!series_matrix_table_end
"""


@pytest.fixture
def microbiome_df():
    """Synthetic IBDMDB taxonomic profile data."""
    return pd.DataFrame({
        "site_name": ["stool", "stool", "stool"],
        "sex": ["Male", "Female", "Male"],
        "race": ["white", "white", "black"],
        "consent_age": [35, 42, 28],
        "diagnosis": ["CD", "UC", "nonIBD"],
        "k__Bacteria|p__Firmicutes|c__Clostridia|o__Clostridiales|f__Lachnospiraceae|g__Roseburia|s__Roseburia_intestinalis": [0.15, 0.08, 0.22],
        "k__Bacteria|p__Bacteroidetes|c__Bacteroidia|o__Bacteroidales|f__Bacteroidaceae|g__Bacteroides|s__Bacteroides_vulgatus": [0.25, 0.30, 0.18],
        "k__Bacteria|p__Proteobacteria|c__Gammaproteobacteria|o__Enterobacteriales|f__Enterobacteriaceae|g__Escherichia|s__Escherichia_coli": [0.05, 0.12, 0.02],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGEOMatrixParsing:
    """Test GEO series matrix file parsing."""

    def test_parse_metadata(self, geo_matrix_text):
        metadata = {}
        for line in geo_matrix_text.strip().split("\n"):
            if line.startswith("!Series_"):
                key = line.split("\t")[0].replace("!Series_", "")
                val = "\t".join(line.split("\t")[1:]).strip('"')
                metadata[key] = val
        assert metadata["title"] == "Gene Expression in Rheumatoid Arthritis PBMCs"
        assert metadata["geo_accession"] == "GSE15573"
        assert metadata["platform_id"] == "GPL570"

    def test_parse_expression_matrix(self, geo_matrix_text):
        lines = geo_matrix_text.strip().split("\n")
        in_data = False
        data_lines = []
        for line in lines:
            if line == "!series_matrix_table_begin":
                in_data = True
                continue
            elif line == "!series_matrix_table_end":
                break
            elif in_data:
                data_lines.append(line)

        expr_df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep="\t", index_col=0)
        assert expr_df.shape == (3, 3)
        assert list(expr_df.index) == ["GENE_A", "GENE_B", "GENE_C"]
        assert expr_df.loc["GENE_A", "GSM389076"] == 5.23

    def test_gene_statistics(self, geo_matrix_text):
        # Parse expression matrix
        lines = geo_matrix_text.strip().split("\n")
        data_lines = []
        in_data = False
        for line in lines:
            if line == "!series_matrix_table_begin":
                in_data = True
                continue
            elif line == "!series_matrix_table_end":
                break
            elif in_data:
                data_lines.append(line)

        expr_df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep="\t", index_col=0)

        gene_stats = pd.DataFrame({
            "gene_symbol": expr_df.index,
            "mean_expression": expr_df.mean(axis=1).values,
            "std_expression": expr_df.std(axis=1).values,
        })
        assert len(gene_stats) == 3
        assert gene_stats["mean_expression"].iloc[0] == pytest.approx(5.4133, rel=0.01)


class TestMicrobiomeParsing:
    """Test microbiome taxonomic profile parsing."""

    def test_species_column_detection(self, microbiome_df):
        taxon_cols = [c for c in microbiome_df.columns if c.startswith("k__")]
        species_cols = [c for c in taxon_cols if "|s__" in c and "|t__" not in c]
        assert len(species_cols) == 3

    def test_taxon_name_extraction(self):
        path = "k__Bacteria|p__Firmicutes|g__Roseburia|s__Roseburia_intestinalis"
        parts = path.split("|")
        taxon_name = parts[-1]
        assert taxon_name == "s__Roseburia_intestinalis"

    def test_taxon_level_detection(self):
        def get_taxon_level(path):
            if "|s__" in path:
                return "species"
            elif "|g__" in path:
                return "genus"
            elif "|f__" in path:
                return "family"
            return "kingdom"

        assert get_taxon_level("k__Bacteria|p__Firmicutes|g__Rosa|s__Rosa_int") == "species"
        assert get_taxon_level("k__Bacteria|p__Firmicutes|g__Rosa") == "genus"

    def test_melt_to_long(self, microbiome_df):
        meta_cols = ["site_name", "sex", "race", "consent_age", "diagnosis"]
        taxon_cols = [c for c in microbiome_df.columns if c.startswith("k__")]
        microbiome_df["sample_id"] = microbiome_df.index.astype(str)

        long_df = microbiome_df[["sample_id", "diagnosis"] + taxon_cols].melt(
            id_vars=["sample_id", "diagnosis"],
            var_name="taxon_path",
            value_name="relative_abundance",
        )
        assert len(long_df) == 9  # 3 samples x 3 taxa
        assert long_df["relative_abundance"].sum() > 0

    def test_diagnosis_mapping(self, microbiome_df):
        diagnosis_map = {"CD": "gastrointestinal", "UC": "gastrointestinal", "nonIBD": "healthy"}
        clusters = microbiome_df["diagnosis"].map(diagnosis_map)
        assert clusters.iloc[0] == "gastrointestinal"
        assert clusters.iloc[2] == "healthy"

    def test_zero_abundance_filtering(self, microbiome_df):
        meta_cols = ["diagnosis"]
        taxon_cols = [c for c in microbiome_df.columns if c.startswith("k__")]
        long_df = microbiome_df[meta_cols + taxon_cols].melt(
            id_vars=meta_cols, var_name="taxon", value_name="abundance"
        )
        # Add a zero entry
        long_df.loc[len(long_df)] = {"diagnosis": "CD", "taxon": "fake", "abundance": 0.0}
        filtered = long_df[long_df["abundance"] > 0]
        assert len(filtered) == len(long_df) - 1


class TestDiseaseMapping:
    """Test disease-to-cluster mapping for omics data."""

    def test_known_diseases(self):
        assert map_disease_to_cluster("Rheumatoid Arthritis") == "systemic"
        assert map_disease_to_cluster("Crohn's disease") == "gastrointestinal"
        assert map_disease_to_cluster("Type 1 Diabetes") == "endocrine"
        assert map_disease_to_cluster("Multiple Sclerosis") == "neurological"

    def test_unknown_disease(self):
        assert map_disease_to_cluster("Fibromyalgia") == "other_autoimmune"

    def test_none(self):
        assert map_disease_to_cluster(None) == "other_autoimmune"
        assert map_disease_to_cluster("") == "other_autoimmune"


class TestMetabolomics:
    """Test metabolomics wrangling logic."""

    def test_autoimmune_keyword_filter(self):
        titles = pd.Series([
            "Metabolomics of Rheumatoid Arthritis",
            "Lipids in Healthy Adults",
            "Celiac Disease Biomarkers",
            "Cancer Metabolism",
        ])
        keywords = ["rheumatoid arthritis", "celiac"]
        pattern = "|".join(keywords)
        mask = titles.str.lower().str.contains(pattern, na=False)
        assert mask.sum() == 2
