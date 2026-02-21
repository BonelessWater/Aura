"""
Feature importance analysis.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import matplotlib.pyplot as plt


def get_model_feature_importance(
    model,
    feature_names: List[str],
    importance_type: str = 'gain'
) -> pd.DataFrame:
    """
    Extract feature importance from trained model.

    Args:
        model: Trained XGBoost/LightGBM model
        feature_names: List of feature names
        importance_type: 'gain', 'weight', or 'cover'
    """
    raise NotImplementedError()


def plot_feature_importance(
    importance_df: pd.DataFrame,
    top_n: int = 20,
    save_path: Optional[str] = None
):
    """Plot horizontal bar chart of feature importance."""
    raise NotImplementedError()


def compare_feature_importance(
    models: Dict[str, any],
    feature_names: List[str]
) -> pd.DataFrame:
    """Compare feature importance across multiple models."""
    raise NotImplementedError()
