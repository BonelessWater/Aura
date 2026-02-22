"""
Data loaders for Aura autoimmune datasets.

Loads data from the three-tier architecture:
- Tier 1: core_matrix (unified patient features)
- Tier 2: autoantibody_panel, longitudinal_labs, genetic_risk_scores
- Tier 3: healthy_baselines, icd_cluster_map, drug_risk_index
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List

# Base path for data directory (relative to project root)
def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        # Prefer a root that contains the tier1 core matrix (authoritative).
        if (parent / "data" / "processed" / "tier1" / "core_matrix.parquet").exists():
            return parent
    for parent in [here] + list(here.parents):
        # Fallbacks if data isn't present yet.
        if (parent / "data" / "processed").exists() or (parent / ".git").exists():
            return parent
    # Fallback: original relative assumption
    return here.parent.parent.parent.parent


PROJECT_ROOT = _find_project_root()
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def load_core_matrix(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load the unified patient feature matrix (Tier 1).

    88,742 patients with CBC, inflammatory markers, demographics, diagnoses.
    Includes z-scores and missingness flags for all lab markers.

    Columns:
        - patient_id: Unique identifier ({source}_{n})
        - source: Data origin (harvard, kaggle_autoimmune, kaggle_gi, nhanes, mimic_demo)
        - age, sex, bmi: Demographics
        - diagnosis_raw, diagnosis_icd10, diagnosis_cluster: Disease labels
        - wbc, rbc, hemoglobin, hematocrit, platelet_count, mcv, mch, rdw: CBC
        - esr, crp: Inflammatory markers
        - {marker}_zscore: IQR-based z-scores vs healthy baseline
        - {marker}_missing: Missingness flags (0/1)
    """
    path = (data_dir or DATA_DIR) / "tier1" / "core_matrix.parquet"
    return pd.read_parquet(path)


def load_autoantibody_panel(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load autoantibody test results (Tier 2).

    12,085 rows from Harvard dataset. Join to core_matrix on patient_id.

    Columns:
        - patient_id: Join key
        - ana_status, anti_dsdna, hla_b27, anti_sm, anti_ro, anti_la: Binary (0/1)
        - rf_status, anti_ccp: Binary (0/1)
        - c3, c4: Complement levels (mg/dL)
    """
    path = (data_dir or DATA_DIR) / "tier2" / "autoantibody_panel.parquet"
    return pd.read_parquet(path)

def load_longitudinal_labs(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load time-series lab results (Tier 2).

    19,646 observations from MIMIC-IV Demo ICU patients.

    Columns:
        - patient_id: Join key
        - event_timestamp: When the lab was drawn
        - lab_item: Lab test name
        - lab_value: Measured value
        - lab_unit: Unit of measurement
    """
    path = (data_dir or DATA_DIR) / "tier2" / "longitudinal_labs.parquet"
    return pd.read_parquet(path)


def load_genetic_risk_scores(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load GWAS significant hits from FinnGen R12 (Tier 2).

    67,869 variants (p < 5e-8) associated with autoimmune phenotypes.

    Columns:
        - variant_id, gene, chrom, pos: Genomic location
        - pvalue, beta, se, af: Association statistics
        - finngen_endpoint: FinnGen phenotype code
        - diagnosis_cluster, diagnosis_icd10: Aura mappings
    """
    path = (data_dir or DATA_DIR) / "tier2" / "genetic_risk_scores.parquet"
    return pd.read_parquet(path)


def load_healthy_baselines(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load age/sex-stratified reference ranges (Tier 3).

    110 rows with percentiles for each lab marker by age bucket and sex.

    Columns:
        - marker: Lab marker name
        - age_bucket: 0-17, 18-30, 31-45, 46-60, 61+
        - sex: M or F
        - count: Number of subjects
        - p5, p25, p50, p75, p95: Percentiles
    """
    path = (data_dir or DATA_DIR) / "tier3" / "healthy_baselines.parquet"
    return pd.read_parquet(path)


def load_icd_cluster_map(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load ICD-10 to Aura cluster mapping (Tier 3).

    111 rows mapping ICD codes to disease clusters.

    Columns:
        - icd10_code: ICD-10 code
        - icd10_description: Human-readable name
        - aura_cluster: Aura cluster assignment
    """
    path = (data_dir or DATA_DIR) / "tier3" / "icd_cluster_map.parquet"
    return pd.read_parquet(path)


def load_drug_risk_index(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load drug autoimmunity risk data (Tier 3).

    597 drugs with molecular descriptors and autoimmunity risk labels.

    Columns:
        - Label: 0 = no risk, 1 = autoimmunity risk
        - SMILES: Molecular structure
        - 195 physicochemical descriptors
    """
    path = (data_dir or DATA_DIR) / "tier3" / "drug_risk_index.parquet"
    return pd.read_parquet(path)


# =============================================================================
# Convenience loaders for modeling
# =============================================================================

def load_modeling_data(
    include_autoantibodies: bool = True,
    data_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    Load core_matrix with optional enrichment from Tier 2 tables.

    Args:
        include_autoantibodies: Join autoantibody_panel (adds 10 columns)
        data_dir: Optional custom data directory

    Returns:
        Enriched DataFrame ready for modeling
    """
    df = load_core_matrix(data_dir)

    if include_autoantibodies:
        ab = load_autoantibody_panel(data_dir)
        df = df.merge(ab, on="patient_id", how="left")

    return df


def load_cluster_data(
    cluster: str,
    include_healthy: bool = True,
    data_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    Load data for a specific disease cluster.

    Args:
        cluster: One of 'systemic', 'gastrointestinal', 'endocrine', etc.
        include_healthy: Include healthy controls for binary classification
        data_dir: Optional custom data directory

    Returns:
        Filtered DataFrame for the specified cluster
    """
    df = load_modeling_data(data_dir=data_dir)

    if include_healthy:
        mask = (df["diagnosis_cluster"] == cluster) | (df["diagnosis_cluster"] == "healthy")
    else:
        mask = df["diagnosis_cluster"] == cluster

    return df[mask].copy()


def get_feature_columns() -> Dict[str, List[str]]:
    """
    Get standard feature column groupings.

    Returns:
        Dictionary with feature groups:
        - 'demographics': age, sex
        - 'cbc': wbc, rbc, hemoglobin, etc.
        - 'inflammatory': esr, crp
        - 'zscore': all z-score columns
        - 'missing': all missingness flag columns
        - 'autoantibody': ana_status, anti_dsdna, etc.
    """
    return {
        "demographics": ["age", "sex"],
        "cbc": [
            "wbc", "rbc", "hemoglobin", "hematocrit",
            "platelet_count", "mcv", "mch", "rdw",
            "neutrophil_pct", "lymphocyte_pct"
        ],
        "inflammatory": ["esr", "crp"],
        "zscore": [
            "wbc_zscore", "rbc_zscore", "hemoglobin_zscore",
            "hematocrit_zscore", "platelet_count_zscore",
            "mcv_zscore", "mch_zscore", "rdw_zscore",
            "esr_zscore", "crp_zscore"
        ],
        "missing": [
            "wbc_missing", "rbc_missing", "hemoglobin_missing",
            "hematocrit_missing", "platelet_count_missing",
            "mcv_missing", "mch_missing", "rdw_missing",
            "esr_missing", "crp_missing"
        ],
        "autoantibody": [
            "ana_status", "anti_dsdna", "hla_b27",
            "anti_sm", "anti_ro", "anti_la",
            "rf_status", "anti_ccp", "c3", "c4"
        ],
        # Derived features from feature_engineering.engineer_all_features()
        "engineered": [
            # Inflammatory ratios
            "crp_esr_ratio", "inflammatory_burden", "high_inflammation",
            # Anemia indicators
            "anemia_flag", "microcytic_flag", "macrocytic_flag",
            # CBC ratios
            "nlr", "high_nlr", "rdw_elevated", "plr",
            # Lab abnormality counts
            "lab_abnormality_count", "high_value_count", "low_value_count",
            # GI-specific
            "calprotectin_elevated", "calprotectin_high", "log_calprotectin",
            # Autoantibody scores (when panel is joined)
            "autoantibody_count", "lupus_panel_score", "ra_panel_score",
            "complement_consumption", "c3_c4_ratio",
        ],
        "gi": [
            "fecal_calprotectin",
        ],
    }


def get_cluster_labels() -> List[str]:
    """Get list of all disease cluster labels."""
    return [
        "healthy",
        "systemic",
        "gastrointestinal",
        "neurological",
        "dermatological",
        "endocrine",
        "haematological",
        "renal",
        "pulmonary",
        "ophthalmic",
        "other_autoimmune",
    ]
