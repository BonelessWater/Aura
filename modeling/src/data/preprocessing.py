"""
Preprocessing pipeline for Aura autoimmune data.

Note: Much preprocessing is already done in the data lake:
- Z-scores computed against healthy baselines
- Missingness flags added
- Units harmonized

This module adds modeling-specific transformations.
"""
import pandas as pd
import numpy as np
import re
from typing import Tuple, Dict, List, Optional
from sklearn.model_selection import train_test_split
from pathlib import Path

# Disease cluster mappings (for reference - data already has these)
CLUSTER_LABELS = [
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

# Priority clusters for hierarchical classification
PRIORITY_CLUSTERS = ["healthy", "systemic", "gastrointestinal", "endocrine"]

# Canonical disease labels for Stage-2 modeling
_DISEASE_LABEL_MAP = {
    "systemic": {
        "rheumatoid_arthritis": "RA",
        "reactive_arthritis": "Reactive_Arthritis",
        "ankylosing_spondylitis": "AS",
        "sjogrens_syndrome": "Sjogren",
        "sjogren_s_syndrome": "Sjogren",
        "sjogren_syndrome": "Sjogren",
        "systemic_lupus_erythematosus": "SLE",
        "lupus": "SLE",
        "sle": "SLE",
        "psoriatic_arthritis": "PsA",
    },
    "gastrointestinal": {
        "celiac_disease": "Celiac",
        "celiac": "Celiac",
        "crohn_s_disease": "IBD",
        "crohn_disease": "IBD",
        "ulcerative_colitis": "IBD",
        "ibd": "IBD",
        "functional_gi": "Functional_GI",
        "functional_gastrointestinal": "Functional_GI",
    },
    "endocrine": {
        "autoimmune_thyroiditis": "Hashimoto",
        "hashimoto_s": "Hashimoto",
        "hashimotos": "Hashimoto",
        "graves": "Graves",
        "graves_disease": "Graves",
        "type_1_diabetes": "T1D",
        "type_1_diabetes_mellitus": "T1D",
        "t1d": "T1D",
    },
}


def _normalize_diagnosis_label(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def map_diagnosis_to_disease_label(
    diagnosis_raw: Optional[str],
    cluster: Optional[str]
) -> Optional[str]:
    """
    Map raw diagnosis strings to canonical disease labels for Stage-2 modeling.

    Returns None when no mapping is available.
    """
    if cluster == "healthy":
        return "Control"
    if not diagnosis_raw or not cluster:
        return None
    normalized = _normalize_diagnosis_label(diagnosis_raw)
    return _DISEASE_LABEL_MAP.get(cluster, {}).get(normalized)


def add_disease_labels(
    df: pd.DataFrame,
    diagnosis_col: str = "diagnosis_raw",
    cluster_col: str = "diagnosis_cluster",
    output_col: str = "diagnosis_disease",
) -> pd.DataFrame:
    """
    Add canonical disease labels for Stage-2 disease modeling.
    """
    df = df.copy()
    df[output_col] = [
        map_diagnosis_to_disease_label(raw, cluster)
        for raw, cluster in zip(df[diagnosis_col], df[cluster_col])
    ]
    return df


def encode_sex(df: pd.DataFrame, column: str = "sex") -> pd.DataFrame:
    """
    Encode sex as binary (0=F, 1=M).

    Args:
        df: DataFrame with sex column
        column: Name of sex column

    Returns:
        DataFrame with sex_encoded column added
    """
    df = df.copy()
    df["sex_encoded"] = (df[column] == "M").astype(int)
    return df


def create_age_buckets(
    df: pd.DataFrame,
    column: str = "age",
    buckets: List[Tuple[int, int, str]] = None
) -> pd.DataFrame:
    """
    Create age bucket categories.

    Args:
        df: DataFrame with age column
        column: Name of age column
        buckets: List of (min, max, label) tuples

    Returns:
        DataFrame with age_bucket column added
    """
    df = df.copy()

    if buckets is None:
        buckets = [
            (0, 17, "0-17"),
            (18, 30, "18-30"),
            (31, 45, "31-45"),
            (46, 60, "46-60"),
            (61, 150, "61+"),
        ]

    conditions = [
        (df[column] >= low) & (df[column] <= high)
        for low, high, _ in buckets
    ]
    labels = [label for _, _, label in buckets]

    df["age_bucket"] = np.select(conditions, labels, default="unknown")
    return df


def encode_clusters(
    df: pd.DataFrame,
    column: str = "diagnosis_cluster",
    clusters: List[str] = None
) -> pd.DataFrame:
    """
    Encode cluster labels as integers.

    Args:
        df: DataFrame with cluster column
        column: Name of cluster column
        clusters: Ordered list of cluster labels

    Returns:
        DataFrame with cluster_encoded column added
    """
    df = df.copy()

    if clusters is None:
        clusters = CLUSTER_LABELS

    cluster_to_idx = {c: i for i, c in enumerate(clusters)}
    df["cluster_encoded"] = df[column].map(cluster_to_idx)

    return df


def create_binary_target(
    df: pd.DataFrame,
    positive_clusters: List[str] = None,
    column: str = "diagnosis_cluster"
) -> pd.DataFrame:
    """
    Create binary target (autoimmune vs healthy).

    Args:
        df: DataFrame with cluster column
        positive_clusters: Clusters to label as positive (default: all non-healthy)
        column: Name of cluster column

    Returns:
        DataFrame with target_binary column added
    """
    df = df.copy()

    if positive_clusters is None:
        df["target_binary"] = (df[column] != "healthy").astype(int)
    else:
        df["target_binary"] = df[column].isin(positive_clusters).astype(int)

    return df


def filter_priority_clusters(
    df: pd.DataFrame,
    clusters: List[str] = None,
    column: str = "diagnosis_cluster"
) -> pd.DataFrame:
    """
    Filter to priority clusters for hackathon scope.

    Args:
        df: DataFrame with cluster column
        clusters: List of clusters to keep
        column: Name of cluster column

    Returns:
        Filtered DataFrame
    """
    if clusters is None:
        clusters = PRIORITY_CLUSTERS

    return df[df[column].isin(clusters)].copy()


def prepare_features(
    df: pd.DataFrame,
    feature_groups: List[str] = None,
    drop_missing_threshold: float = 0.5
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Prepare feature matrix for modeling.

    Args:
        df: Raw DataFrame
        feature_groups: Which feature groups to include
            Options: 'demographics', 'cbc', 'inflammatory', 'zscore', 'missing', 'autoantibody', 'gi'
        drop_missing_threshold: Drop columns with more than this fraction missing

    Returns:
        (X DataFrame, list of feature names)
    """
    from .loaders import get_feature_columns

    if feature_groups is None:
        feature_groups = ["demographics", "cbc", "inflammatory", "zscore", "missing"]

    all_features = get_feature_columns()
    selected_features = []
    for group in feature_groups:
        if group in all_features:
            selected_features.extend(all_features[group])

    # Filter to columns that exist
    available = [f for f in selected_features if f in df.columns]

    X = df[available].copy()

    # Encode sex if present
    if "sex" in X.columns:
        X["sex"] = (X["sex"] == "M").astype(int)

    # Drop columns with too much missing
    missing_frac = X.isnull().mean()
    keep_cols = missing_frac[missing_frac <= drop_missing_threshold].index.tolist()
    X = X[keep_cols]

    # Fill remaining missing with median
    for col in X.columns:
        if X[col].isnull().any():
            X[col] = X[col].fillna(X[col].median())

    return X, list(X.columns)


def create_splits(
    df: pd.DataFrame,
    target_col: str = "diagnosis_cluster",
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42,
    stratify: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Create stratified train/val/test splits.

    Args:
        df: Full DataFrame
        target_col: Column to stratify on
        test_size: Fraction for test set
        val_size: Fraction for validation set (from remaining after test)
        random_state: Random seed for reproducibility
        stratify: Whether to stratify splits

    Returns:
        (train_df, val_df, test_df)
    """
    stratify_col = df[target_col] if stratify else None

    # First split: train+val vs test
    train_val, test = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_col
    )

    # Second split: train vs val
    val_frac = val_size / (1 - test_size)
    stratify_col = train_val[target_col] if stratify else None

    train, val = train_test_split(
        train_val,
        test_size=val_frac,
        random_state=random_state,
        stratify=stratify_col
    )

    return train, val, test


def save_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    output_dir: Path,
    prefix: str = ""
) -> None:
    """
    Save train/val/test splits to parquet files.

    Args:
        train, val, test: DataFrames
        output_dir: Directory to save to
        prefix: Optional prefix for filenames
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{prefix}_" if prefix else ""

    train.to_parquet(output_dir / f"{prefix}train.parquet", index=False)
    val.to_parquet(output_dir / f"{prefix}val.parquet", index=False)
    test.to_parquet(output_dir / f"{prefix}test.parquet", index=False)

    print(f"Saved splits to {output_dir}:")
    print(f"  {prefix}train.parquet: {len(train):,} rows")
    print(f"  {prefix}val.parquet: {len(val):,} rows")
    print(f"  {prefix}test.parquet: {len(test):,} rows")


def preprocess_for_modeling(
    df: pd.DataFrame,
    priority_only: bool = True,
    include_zscore: bool = True,
    include_missing: bool = True
) -> pd.DataFrame:
    """
    Full preprocessing pipeline for modeling.

    Args:
        df: Raw DataFrame from load_modeling_data()
        priority_only: Filter to priority clusters only
        include_zscore: Include z-score features
        include_missing: Include missingness flags

    Returns:
        Preprocessed DataFrame ready for modeling
    """
    df = df.copy()

    # Filter to priority clusters if requested
    if priority_only:
        df = filter_priority_clusters(df)

    # Add derived columns
    df = encode_sex(df)
    df = create_age_buckets(df)
    df = encode_clusters(df)
    df = create_binary_target(df)

    return df
