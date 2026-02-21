"""
Subgroup analysis for bias auditing.

Evaluates model performance across demographic subgroups to ensure fairness.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from sklearn.metrics import roc_auc_score, precision_score, recall_score


def create_age_groups(ages: pd.Series) -> pd.Series:
    """Create age group categories."""
    return pd.cut(
        ages,
        bins=[0, 30, 45, 60, 100],
        labels=["<30", "30-45", "45-60", "60+"]
    )


def evaluate_by_subgroup(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    demographics: pd.DataFrame,
    subgroup_columns: List[str] = None
) -> pd.DataFrame:
    """
    Evaluate model performance across demographic subgroups.

    Args:
        y_true: True labels (encoded)
        y_pred: Predicted labels
        y_prob: Prediction probabilities
        demographics: DataFrame with demographic columns
        subgroup_columns: Which columns to stratify by

    Returns:
        DataFrame with metrics per subgroup
    """
    if subgroup_columns is None:
        subgroup_columns = ["sex", "age_group"]

    results = []

    for col in subgroup_columns:
        if col not in demographics.columns:
            continue

        for value in demographics[col].dropna().unique():
            mask = demographics[col] == value
            n_samples = mask.sum()

            if n_samples < 50:  # Skip small groups
                continue

            # Calculate metrics
            try:
                if y_prob.ndim > 1:
                    auc = roc_auc_score(
                        y_true[mask],
                        y_prob[mask],
                        multi_class="ovr"
                    )
                else:
                    auc = roc_auc_score(y_true[mask], y_prob[mask])
            except ValueError:
                auc = np.nan

            # Accuracy
            accuracy = (y_pred[mask] == y_true[mask]).mean()

            results.append({
                "subgroup_type": col,
                "subgroup_value": value,
                "n_samples": n_samples,
                "auc": auc,
                "accuracy": accuracy,
            })

    return pd.DataFrame(results)


def compute_disparity_metrics(
    subgroup_results: pd.DataFrame,
    reference_groups: Dict[str, str] = None
) -> pd.DataFrame:
    """
    Compute fairness gap metrics relative to reference groups.

    Args:
        subgroup_results: Output from evaluate_by_subgroup
        reference_groups: Dict mapping subgroup_type to reference value

    Returns:
        DataFrame with disparity metrics
    """
    if reference_groups is None:
        reference_groups = {
            "sex": "M",
            "age_group": "30-45"
        }

    results = []

    for subgroup_type in subgroup_results["subgroup_type"].unique():
        subset = subgroup_results[
            subgroup_results["subgroup_type"] == subgroup_type
        ]

        ref_value = reference_groups.get(subgroup_type)
        if ref_value is None:
            continue

        ref_row = subset[subset["subgroup_value"] == ref_value]
        if len(ref_row) == 0:
            continue

        ref_auc = ref_row["auc"].values[0]
        ref_accuracy = ref_row["accuracy"].values[0]

        for _, row in subset.iterrows():
            if row["subgroup_value"] == ref_value:
                continue

            results.append({
                "subgroup_type": subgroup_type,
                "subgroup_value": row["subgroup_value"],
                "reference_value": ref_value,
                "n_samples": row["n_samples"],
                "auc": row["auc"],
                "auc_gap": row["auc"] - ref_auc,
                "accuracy": row["accuracy"],
                "accuracy_gap": row["accuracy"] - ref_accuracy,
            })

    return pd.DataFrame(results)


def generate_fairness_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    demographics: pd.DataFrame,
    subgroup_columns: List[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive fairness report.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_prob: Prediction probabilities
        demographics: DataFrame with demographic columns

    Returns:
        Dictionary with fairness metrics and analysis
    """
    # Add age groups if age is present
    if "age" in demographics.columns and "age_group" not in demographics.columns:
        demographics = demographics.copy()
        demographics["age_group"] = create_age_groups(demographics["age"])

    # Calculate subgroup metrics
    subgroup_metrics = evaluate_by_subgroup(
        y_true, y_pred, y_prob, demographics, subgroup_columns
    )

    # Calculate disparities
    disparities = compute_disparity_metrics(subgroup_metrics)

    # Overall metrics
    try:
        if y_prob.ndim > 1:
            overall_auc = roc_auc_score(y_true, y_prob, multi_class="ovr")
        else:
            overall_auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        overall_auc = np.nan

    overall_accuracy = (y_pred == y_true).mean()

    # Find maximum disparity
    if len(disparities) > 0:
        max_auc_gap = disparities["auc_gap"].abs().max()
        worst_group = disparities.loc[
            disparities["auc_gap"].abs().idxmax()
        ].to_dict() if not disparities.empty else None
    else:
        max_auc_gap = 0
        worst_group = None

    # Generate summary
    if max_auc_gap < 0.05:
        fairness_status = "PASS"
        fairness_message = "Model shows acceptable performance parity across subgroups."
    elif max_auc_gap < 0.10:
        fairness_status = "WARNING"
        fairness_message = "Model shows moderate disparity in some subgroups."
    else:
        fairness_status = "FAIL"
        fairness_message = "Model shows significant disparity requiring mitigation."

    return {
        "overall": {
            "auc": overall_auc,
            "accuracy": overall_accuracy,
            "n_samples": len(y_true),
        },
        "subgroup_metrics": subgroup_metrics,
        "disparities": disparities,
        "summary": {
            "fairness_status": fairness_status,
            "fairness_message": fairness_message,
            "max_auc_gap": max_auc_gap,
            "worst_performing_group": worst_group,
        }
    }


def format_fairness_report(report: Dict[str, Any]) -> str:
    """Format fairness report as readable string."""
    lines = [
        "=" * 60,
        "FAIRNESS AUDIT REPORT",
        "=" * 60,
        "",
        "OVERALL PERFORMANCE",
        f"  AUC: {report['overall']['auc']:.4f}",
        f"  Accuracy: {report['overall']['accuracy']:.4f}",
        f"  N: {report['overall']['n_samples']:,}",
        "",
        "FAIRNESS STATUS: " + report["summary"]["fairness_status"],
        report["summary"]["fairness_message"],
        "",
    ]

    if report["summary"]["max_auc_gap"] > 0:
        lines.append(f"Maximum AUC Gap: {report['summary']['max_auc_gap']:.4f}")

        if report["summary"]["worst_performing_group"]:
            wg = report["summary"]["worst_performing_group"]
            lines.append(
                f"Worst Gap: {wg['subgroup_type']}={wg['subgroup_value']} "
                f"(AUC gap: {wg['auc_gap']:+.4f})"
            )

    lines.extend([
        "",
        "SUBGROUP BREAKDOWN",
        "-" * 40,
    ])

    for _, row in report["subgroup_metrics"].iterrows():
        lines.append(
            f"  {row['subgroup_type']}={row['subgroup_value']}: "
            f"AUC={row['auc']:.4f}, N={row['n_samples']:,}"
        )

    return "\n".join(lines)
