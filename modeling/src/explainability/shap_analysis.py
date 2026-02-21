"""
SHAP-based model explanations for Aura.
"""
import numpy as np
import pandas as pd
import shap
from typing import Optional, Dict, Any, List, Tuple
import matplotlib.pyplot as plt
from pathlib import Path


def compute_shap_values(
    model,
    X: pd.DataFrame,
    background_samples: int = 100
) -> shap.Explanation:
    """
    Compute SHAP values for model predictions.

    Args:
        model: Trained XGBoost model (or model with predict_proba)
        X: Feature matrix to explain
        background_samples: Number of background samples for TreeExplainer

    Returns:
        SHAP Explanation object
    """
    # For XGBoost, use TreeExplainer
    if hasattr(model, "get_booster"):
        explainer = shap.TreeExplainer(model)
    else:
        # Fall back to sampling explainer
        background = shap.sample(X, min(background_samples, len(X)))
        explainer = shap.KernelExplainer(model.predict_proba, background)

    shap_values = explainer(X)
    return shap_values


def compute_shap_for_dual_scorer(
    scorer,
    X: pd.DataFrame,
    background_samples: int = 100
) -> shap.Explanation:
    """
    Compute SHAP values for a DualScorer's category classifier.

    Args:
        scorer: Trained DualScorer
        X: Feature matrix
        background_samples: Number of background samples

    Returns:
        SHAP Explanation object
    """
    model = scorer.category_classifier.model
    X_filled = X[scorer.feature_names].fillna(X[scorer.feature_names].median())

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_filled)

    return shap_values


def plot_summary(
    shap_values: shap.Explanation,
    X: pd.DataFrame = None,
    max_features: int = 20,
    class_idx: int = None,
    save_path: Optional[str] = None,
    title: str = "SHAP Feature Importance"
) -> None:
    """
    Plot SHAP summary (global feature importance).

    Args:
        shap_values: SHAP Explanation object
        X: Original feature matrix (for feature names)
        max_features: Maximum features to show
        class_idx: Which class to show (for multi-class)
        save_path: Path to save figure
        title: Plot title
    """
    plt.figure(figsize=(10, 8))

    if class_idx is not None and len(shap_values.shape) > 2:
        # Multi-class: select specific class
        shap.summary_plot(
            shap_values[:, :, class_idx],
            X,
            max_display=max_features,
            show=False
        )
    else:
        shap.summary_plot(
            shap_values,
            X,
            max_display=max_features,
            show=False
        )

    plt.title(title)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    plt.show()


def plot_waterfall(
    shap_values: shap.Explanation,
    sample_idx: int,
    class_idx: int = None,
    save_path: Optional[str] = None,
    max_features: int = 15
) -> None:
    """
    Plot SHAP waterfall for single prediction.

    Args:
        shap_values: SHAP Explanation object
        sample_idx: Index of sample to explain
        class_idx: Which class to show (for multi-class)
        save_path: Path to save figure
        max_features: Maximum features to show
    """
    plt.figure(figsize=(10, 8))

    if class_idx is not None and len(shap_values.shape) > 2:
        shap.waterfall_plot(
            shap_values[sample_idx, :, class_idx],
            max_display=max_features,
            show=False
        )
    else:
        shap.waterfall_plot(
            shap_values[sample_idx],
            max_display=max_features,
            show=False
        )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    plt.show()


def plot_bar(
    shap_values: shap.Explanation,
    max_features: int = 20,
    save_path: Optional[str] = None,
    title: str = "Mean |SHAP Value|"
) -> None:
    """
    Plot bar chart of mean absolute SHAP values.

    Args:
        shap_values: SHAP Explanation object
        max_features: Maximum features to show
        save_path: Path to save figure
        title: Plot title
    """
    plt.figure(figsize=(10, 8))
    shap.plots.bar(shap_values, max_display=max_features, show=False)
    plt.title(title)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    plt.show()


def get_top_features(
    shap_values: shap.Explanation,
    n: int = 10,
    class_idx: int = None
) -> pd.DataFrame:
    """
    Get top N features by mean absolute SHAP value.

    Args:
        shap_values: SHAP Explanation object
        n: Number of top features
        class_idx: Which class (for multi-class)

    Returns:
        DataFrame with feature names and importance
    """
    if class_idx is not None and len(shap_values.shape) > 2:
        vals = np.abs(shap_values.values[:, :, class_idx]).mean(axis=0)
    else:
        if len(shap_values.shape) > 2:
            vals = np.abs(shap_values.values).mean(axis=(0, 2))
        else:
            vals = np.abs(shap_values.values).mean(axis=0)

    feature_names = shap_values.feature_names

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": vals
    }).sort_values("mean_abs_shap", ascending=False)

    return importance_df.head(n)


def get_sample_explanation(
    shap_values: shap.Explanation,
    sample_idx: int,
    feature_values: pd.Series,
    class_idx: int = None,
    n_features: int = 5
) -> Dict[str, Any]:
    """
    Get detailed explanation for a single sample.

    Args:
        shap_values: SHAP Explanation object
        sample_idx: Index of sample
        feature_values: Feature values for this sample
        class_idx: Which class (for multi-class)
        n_features: Number of top features to include

    Returns:
        Dictionary with explanation details
    """
    if class_idx is not None and len(shap_values.shape) > 2:
        sample_shap = shap_values.values[sample_idx, :, class_idx]
        base_value = shap_values.base_values[sample_idx, class_idx]
    else:
        sample_shap = shap_values.values[sample_idx]
        base_value = shap_values.base_values[sample_idx]
        if isinstance(base_value, np.ndarray):
            base_value = base_value[0]

    feature_names = shap_values.feature_names

    # Sort by absolute SHAP value
    sorted_idx = np.argsort(np.abs(sample_shap))[::-1]

    top_positive = []
    top_negative = []

    for i in sorted_idx[:n_features * 2]:
        entry = {
            "feature": feature_names[i],
            "value": feature_values.iloc[i] if hasattr(feature_values, 'iloc') else feature_values[i],
            "shap_value": float(sample_shap[i])
        }
        if sample_shap[i] > 0:
            if len(top_positive) < n_features:
                top_positive.append(entry)
        else:
            if len(top_negative) < n_features:
                top_negative.append(entry)

    return {
        "base_value": float(base_value),
        "top_positive_features": top_positive,
        "top_negative_features": top_negative,
        "prediction_contribution": float(np.sum(sample_shap)),
    }
