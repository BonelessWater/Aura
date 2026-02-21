"""
Feature engineering for Aura autoimmune prediction.

Creates derived features from raw lab values and clinical data.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple


def compute_inflammatory_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute inflammatory marker ratios.

    Features created:
    - crp_esr_ratio: CRP/ESR ratio (acute vs chronic inflammation)
    - inflammatory_burden: Combined inflammatory score
    """
    df = df.copy()

    # CRP/ESR ratio (handle division by zero)
    df["crp_esr_ratio"] = np.where(
        df["esr"] > 0,
        df["crp"] / df["esr"],
        np.nan
    )

    # Combined inflammatory burden (sum of z-scores)
    inflammatory_cols = ["crp_zscore", "esr_zscore"]
    available = [c for c in inflammatory_cols if c in df.columns]
    if available:
        df["inflammatory_burden"] = df[available].sum(axis=1)
    else:
        df["inflammatory_burden"] = np.nan

    # High inflammation flag (either z-score > 2)
    if "crp_zscore" in df.columns and "esr_zscore" in df.columns:
        df["high_inflammation"] = (
            (df["crp_zscore"] > 2) | (df["esr_zscore"] > 2)
        ).astype(int)
    else:
        df["high_inflammation"] = np.nan

    return df


def compute_anemia_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive anemia features from CBC values.

    Features created:
    - anemia_flag: Hemoglobin below normal threshold
    - anemia_severity: Severity based on hemoglobin level
    - microcytic_flag: MCV < 80 (suggests iron deficiency or thalassemia)
    - macrocytic_flag: MCV > 100 (suggests B12/folate deficiency)
    """
    df = df.copy()

    # Anemia flag (using z-score)
    if "hemoglobin_zscore" in df.columns:
        df["anemia_flag"] = (df["hemoglobin_zscore"] < -2).astype(int)

        # Severity categories
        df["anemia_severity"] = pd.cut(
            df["hemoglobin_zscore"],
            bins=[-np.inf, -3, -2, -1, np.inf],
            labels=["severe", "moderate", "mild", "normal"]
        )
    else:
        df["anemia_flag"] = np.nan
        df["anemia_severity"] = np.nan

    # MCV-based classification
    if "mcv" in df.columns:
        df["microcytic_flag"] = (df["mcv"] < 80).astype(int)
        df["macrocytic_flag"] = (df["mcv"] > 100).astype(int)
    else:
        df["microcytic_flag"] = np.nan
        df["macrocytic_flag"] = np.nan

    return df


def compute_autoantibody_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count positive autoantibodies and compute panel scores.

    Features created:
    - autoantibody_count: Number of positive autoantibodies
    - lupus_panel_score: Score for lupus-associated markers
    - ra_panel_score: Score for RA-associated markers
    - complement_consumption: Low C3/C4 indicator
    """
    df = df.copy()

    # Autoantibody columns (binary 0/1)
    ab_cols = ["ana_status", "anti_dsdna", "hla_b27", "anti_sm",
               "anti_ro", "anti_la", "rf_status", "anti_ccp"]
    available_ab = [c for c in ab_cols if c in df.columns]

    if available_ab:
        # Total positive count
        df["autoantibody_count"] = df[available_ab].sum(axis=1)

        # Lupus panel (ANA, anti-dsDNA, anti-Sm, anti-Ro, anti-La)
        lupus_markers = ["ana_status", "anti_dsdna", "anti_sm", "anti_ro", "anti_la"]
        lupus_avail = [c for c in lupus_markers if c in df.columns]
        df["lupus_panel_score"] = df[lupus_avail].sum(axis=1)

        # RA panel (RF, anti-CCP)
        ra_markers = ["rf_status", "anti_ccp"]
        ra_avail = [c for c in ra_markers if c in df.columns]
        df["ra_panel_score"] = df[ra_avail].sum(axis=1)
    else:
        df["autoantibody_count"] = np.nan
        df["lupus_panel_score"] = np.nan
        df["ra_panel_score"] = np.nan

    # Complement consumption (low C3 or C4)
    if "c3" in df.columns and "c4" in df.columns:
        # Normal ranges approximately: C3 90-180, C4 10-40 mg/dL
        df["low_c3"] = (df["c3"] < 90).astype(int)
        df["low_c4"] = (df["c4"] < 10).astype(int)
        df["complement_consumption"] = ((df["c3"] < 90) | (df["c4"] < 10)).astype(int)

        # C3/C4 ratio (elevated in certain conditions)
        df["c3_c4_ratio"] = np.where(
            df["c4"] > 0,
            df["c3"] / df["c4"],
            np.nan
        )
    else:
        df["low_c3"] = np.nan
        df["low_c4"] = np.nan
        df["complement_consumption"] = np.nan
        df["c3_c4_ratio"] = np.nan

    return df


def compute_cbc_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CBC-derived ratios.

    Features created:
    - nlr: Neutrophil-to-lymphocyte ratio (inflammation marker)
    - rbc_indices_score: Combined RBC index abnormality
    - rdw_elevated: RDW > 14.5% flag
    """
    df = df.copy()

    # Neutrophil-to-lymphocyte ratio
    if "neutrophil_pct" in df.columns and "lymphocyte_pct" in df.columns:
        df["nlr"] = np.where(
            df["lymphocyte_pct"] > 0,
            df["neutrophil_pct"] / df["lymphocyte_pct"],
            np.nan
        )
        # High NLR flag (>3 suggests inflammation)
        df["high_nlr"] = (df["nlr"] > 3).astype(int)
    else:
        df["nlr"] = np.nan
        df["high_nlr"] = np.nan

    # RDW elevated flag
    if "rdw" in df.columns:
        df["rdw_elevated"] = (df["rdw"] > 14.5).astype(int)
    else:
        df["rdw_elevated"] = np.nan

    # Platelet-to-lymphocyte ratio (PLR)
    if "platelet_count" in df.columns and "lymphocyte_pct" in df.columns:
        # Approximate lymphocyte count from percentage and WBC
        if "wbc" in df.columns:
            df["lymphocyte_count"] = df["wbc"] * df["lymphocyte_pct"] / 100
            df["plr"] = np.where(
                df["lymphocyte_count"] > 0,
                df["platelet_count"] / df["lymphocyte_count"],
                np.nan
            )
        else:
            df["plr"] = np.nan
    else:
        df["plr"] = np.nan

    return df


def compute_lab_abnormality_count(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count number of abnormal lab values.

    Features created:
    - lab_abnormality_count: Number of z-scores > 2 or < -2
    - high_value_count: Number of z-scores > 2
    - low_value_count: Number of z-scores < -2
    """
    df = df.copy()

    zscore_cols = [c for c in df.columns if c.endswith("_zscore")]

    if zscore_cols:
        zscore_data = df[zscore_cols]

        # Count abnormal (|z| > 2)
        df["lab_abnormality_count"] = (zscore_data.abs() > 2).sum(axis=1)

        # Count high vs low
        df["high_value_count"] = (zscore_data > 2).sum(axis=1)
        df["low_value_count"] = (zscore_data < -2).sum(axis=1)
    else:
        df["lab_abnormality_count"] = np.nan
        df["high_value_count"] = np.nan
        df["low_value_count"] = np.nan

    return df


def compute_gi_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute GI-specific features.

    Features created:
    - calprotectin_elevated: Fecal calprotectin > 50 (suggests inflammation)
    - calprotectin_high: Fecal calprotectin > 200 (likely active IBD)
    """
    df = df.copy()

    if "fecal_calprotectin" in df.columns:
        df["calprotectin_elevated"] = (df["fecal_calprotectin"] > 50).astype(int)
        df["calprotectin_high"] = (df["fecal_calprotectin"] > 200).astype(int)

        # Log transform for modeling
        df["log_calprotectin"] = np.log1p(df["fecal_calprotectin"])
    else:
        df["calprotectin_elevated"] = np.nan
        df["calprotectin_high"] = np.nan
        df["log_calprotectin"] = np.nan

    return df


def engineer_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature engineering transformations.

    Args:
        df: DataFrame from load_modeling_data()

    Returns:
        DataFrame with all engineered features added
    """
    df = compute_inflammatory_ratio(df)
    df = compute_anemia_indicators(df)
    df = compute_autoantibody_score(df)
    df = compute_cbc_ratios(df)
    df = compute_lab_abnormality_count(df)
    df = compute_gi_features(df)

    return df


def get_engineered_feature_names() -> List[str]:
    """Get list of all engineered feature names."""
    return [
        # Inflammatory
        "crp_esr_ratio",
        "inflammatory_burden",
        "high_inflammation",
        # Anemia
        "anemia_flag",
        "microcytic_flag",
        "macrocytic_flag",
        # Autoantibody
        "autoantibody_count",
        "lupus_panel_score",
        "ra_panel_score",
        "low_c3",
        "low_c4",
        "complement_consumption",
        "c3_c4_ratio",
        # CBC ratios
        "nlr",
        "high_nlr",
        "rdw_elevated",
        "plr",
        # Lab counts
        "lab_abnormality_count",
        "high_value_count",
        "low_value_count",
        # GI
        "calprotectin_elevated",
        "calprotectin_high",
        "log_calprotectin",
    ]


def select_features_for_cluster(
    cluster: str,
    include_engineered: bool = True
) -> List[str]:
    """
    Get recommended features for a specific cluster classifier.

    Args:
        cluster: 'systemic', 'gastrointestinal', or 'endocrine'
        include_engineered: Whether to include engineered features

    Returns:
        List of feature column names
    """
    from .loaders import get_feature_columns

    base_features = get_feature_columns()

    # Base features for all clusters
    features = (
        base_features["demographics"] +
        base_features["cbc"] +
        base_features["inflammatory"] +
        base_features["zscore"] +
        base_features["missing"]
    )

    # Cluster-specific additions
    if cluster == "systemic":
        features.extend(base_features["autoantibody"])
        if include_engineered:
            features.extend([
                "autoantibody_count", "lupus_panel_score", "ra_panel_score",
                "complement_consumption", "c3_c4_ratio",
                "inflammatory_burden", "high_inflammation",
                "anemia_flag", "lab_abnormality_count"
            ])

    elif cluster == "gastrointestinal":
        features.extend(base_features["gi"])
        if include_engineered:
            features.extend([
                "calprotectin_elevated", "calprotectin_high", "log_calprotectin",
                "inflammatory_burden", "high_inflammation",
                "anemia_flag", "lab_abnormality_count"
            ])

    elif cluster == "endocrine":
        if include_engineered:
            features.extend([
                "inflammatory_burden", "anemia_flag",
                "lab_abnormality_count"
            ])

    return features
