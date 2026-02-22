"""
Stage 1: Category Classifier for Aura Dual-Scorer.

Classifies patients into disease clusters:
- Systemic (SLE, RA, Sjögren's, etc.)
- Gastrointestinal (IBD, Celiac, etc.)
- Endocrine (Hashimoto's, Graves', etc.)
- Healthy (controls)
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report
import xgboost as xgb


class CategoryClassifier:
    """
    XGBoost classifier for autoimmune disease category prediction.

    Output: Probability distribution over disease clusters
    """

    def __init__(
        self,
        categories: List[str] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            categories: List of category labels (default: priority clusters)
            params: XGBoost parameters
        """
        self.categories = categories or [
            "healthy", "systemic", "gastrointestinal", "endocrine"
        ]

        default_params = {
            "objective": "multi:softprob",
            "num_class": len(self.categories),
            "eval_metric": "mlogloss",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "gamma": 0,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0,
        }
        if params:
            default_params.update(params)

        self.params = default_params
        self.model: Optional[xgb.XGBClassifier] = None
        self.label_encoder = LabelEncoder()
        self.feature_names: Optional[List[str]] = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        eval_set: Optional[Tuple[pd.DataFrame, pd.Series]] = None,
        early_stopping_rounds: int = 10,
        verbose: bool = False
    ) -> "CategoryClassifier":
        """
        Train the category classifier.

        Args:
            X: Feature matrix
            y: Category labels
            eval_set: Optional validation set for early stopping
            early_stopping_rounds: Rounds for early stopping
            verbose: Print training progress
        """
        self.feature_names = list(X.columns)

        # Prepare data
        X_filled = self._align(X)
        self.label_encoder.fit(self.categories)
        y_encoded = self.label_encoder.transform(y)

        # Create model
        self.model = xgb.XGBClassifier(**self.params)

        # Fit with optional early stopping
        if eval_set is not None:
            X_val, y_val = eval_set
            X_val_filled = self._align(X_val)
            y_val_encoded = self.label_encoder.transform(y_val)

            self.model.set_params(early_stopping_rounds=early_stopping_rounds)
            self.model.fit(
                X_filled, y_encoded,
                eval_set=[(X_val_filled, y_val_encoded)],
                verbose=verbose
            )
        else:
            self.model.fit(X_filled, y_encoded, verbose=verbose)

        return self

    def _align(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Reindex X to exactly self.feature_names, filling any missing columns
        with NaN, then impute with per-column median. This handles the case
        where prepare_features drops different columns from train vs val/test
        due to per-split missingness thresholds.
        """
        X_aligned = X.reindex(columns=self.feature_names)
        return X_aligned.fillna(X_aligned.median())

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict category labels."""
        y_pred = self.model.predict(self._align(X))
        return self.label_encoder.inverse_transform(y_pred)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict category probabilities.

        Returns:
            Array of shape (n_samples, n_categories)
        """
        return self.model.predict_proba(self._align(X))

    def get_category_confidence(
        self,
        X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get predicted category and confidence score.

        Returns:
            (predicted_categories, confidence_scores)
        """
        probs = self.predict_proba(X)
        predicted_idx = probs.argmax(axis=1)
        confidence = probs.max(axis=1)
        predicted_categories = self.label_encoder.inverse_transform(predicted_idx)

        return predicted_categories, confidence

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, Any]:
        """
        Evaluate model performance.

        Returns:
            Dictionary with metrics
        """
        y_prob = self.predict_proba(X)
        y_pred = self.predict(X)
        y_true = self.label_encoder.transform(y)

        # Multi-class AUC
        auc = roc_auc_score(y_true, y_prob, multi_class="ovr")

        # Per-class metrics
        report = classification_report(y, y_pred, output_dict=True)

        return {
            "auc": auc,
            "accuracy": report["accuracy"],
            "per_class": {
                cat: report.get(cat, {})
                for cat in self.categories
            }
        }

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from XGBoost."""
        importance = self.model.feature_importances_
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance
        }).sort_values("importance", ascending=False)

    def save(self, path: str) -> None:
        """Save model to file."""
        import joblib
        joblib.dump({
            "model": self.model,
            "label_encoder": self.label_encoder,
            "feature_names": self.feature_names,
            "categories": self.categories,
            "params": self.params,
        }, path)

    @classmethod
    def load(cls, path: str) -> "CategoryClassifier":
        """Load model from file."""
        import joblib
        data = joblib.load(path)

        instance = cls(categories=data["categories"], params=data["params"])
        instance.model = data["model"]
        instance.label_encoder = data["label_encoder"]
        instance.feature_names = data["feature_names"]

        return instance


def train_category_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: Optional[Dict[str, Any]] = None
) -> Tuple[CategoryClassifier, Dict[str, Any]]:
    """
    Train a category classifier with validation.

    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        params: Optional XGBoost parameters

    Returns:
        (trained model, evaluation results)
    """
    model = CategoryClassifier(params=params)
    model.fit(
        X_train, y_train,
        eval_set=(X_val, y_val),
        early_stopping_rounds=10,
        verbose=False
    )

    train_metrics = model.evaluate(X_train, y_train)
    val_metrics = model.evaluate(X_val, y_val)

    results = {
        "train_auc": train_metrics["auc"],
        "val_auc": val_metrics["auc"],
        "train_accuracy": train_metrics["accuracy"],
        "val_accuracy": val_metrics["accuracy"],
        "per_class_val": val_metrics["per_class"],
    }

    return model, results
