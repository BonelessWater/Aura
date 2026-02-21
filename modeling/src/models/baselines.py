"""
Baseline interpretable models for Aura.

These establish a performance floor and provide interpretable coefficients.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report, accuracy_score
from typing import Dict, Any, Optional, List, Tuple


class LogisticRegressionBaseline:
    """
    Interpretable logistic regression baseline.

    Used for:
    - Establishing performance floor
    - Coefficient-based feature importance
    - Clinical interpretability
    """

    def __init__(
        self,
        C: float = 1.0,
        max_iter: int = 1000,
        class_weight: str = "balanced",
        random_state: int = 42,
        **kwargs
    ):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.model = LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight=class_weight,
            random_state=random_state,
            solver="lbfgs",
            **kwargs
        )
        self.feature_names: Optional[List[str]] = None
        self.classes_: Optional[np.ndarray] = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LogisticRegressionBaseline":
        """
        Fit the model.

        Args:
            X: Feature matrix (numeric columns only)
            y: Target labels
        """
        self.feature_names = list(X.columns)

        # Handle missing values
        X_filled = X.fillna(X.median())

        # Scale features
        X_scaled = self.scaler.fit_transform(X_filled)

        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        self.classes_ = self.label_encoder.classes_

        # Fit model
        self.model.fit(X_scaled, y_encoded)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class labels."""
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        X_scaled = self.scaler.transform(X_filled)
        y_pred = self.model.predict(X_scaled)
        return self.label_encoder.inverse_transform(y_pred)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities."""
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        X_scaled = self.scaler.transform(X_filled)
        return self.model.predict_proba(X_scaled)

    def get_coefficients(self) -> pd.DataFrame:
        """
        Get feature coefficients for interpretability.

        Returns:
            DataFrame with coefficients for each class
        """
        if self.model.coef_.ndim == 1:
            # Binary classification
            coef_df = pd.DataFrame({
                "feature": self.feature_names,
                "coefficient": self.model.coef_[0]
            })
        else:
            # Multi-class
            coef_df = pd.DataFrame(
                self.model.coef_.T,
                index=self.feature_names,
                columns=self.classes_
            )
            coef_df["abs_mean"] = np.abs(coef_df).mean(axis=1)
            coef_df = coef_df.sort_values("abs_mean", ascending=False)

        return coef_df

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance as mean absolute coefficient magnitude.

        Returns:
            DataFrame with 'feature' and 'importance' columns, sorted descending.
        """
        if self.model.coef_.ndim == 1:
            importances = np.abs(self.model.coef_[0])
        else:
            importances = np.abs(self.model.coef_).mean(axis=0)

        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importances,
        }).sort_values("importance", ascending=False).reset_index(drop=True)

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate model performance.

        Returns:
            Dictionary with AUC and other metrics
        """
        y_prob = self.predict_proba(X)
        y_pred = self.predict(X)

        # Encode true labels
        y_true = self.label_encoder.transform(y)

        # Calculate AUC
        if len(self.classes_) == 2:
            auc = roc_auc_score(y_true, y_prob[:, 1])
        else:
            auc = roc_auc_score(y_true, y_prob, multi_class="ovr")

        accuracy = accuracy_score(y_true, self.label_encoder.transform(y_pred))

        return {
            "auc": auc,
            "accuracy": accuracy,
            "n_samples": len(y),
            "n_features": len(self.feature_names),
        }


class DecisionTreeBaseline:
    """
    Decision tree for feature importance visualization.
    """

    def __init__(
        self,
        max_depth: int = 5,
        class_weight: str = "balanced",
        random_state: int = 42,
        **kwargs
    ):
        self.model = DecisionTreeClassifier(
            max_depth=max_depth,
            class_weight=class_weight,
            random_state=random_state,
            **kwargs
        )
        self.label_encoder = LabelEncoder()
        self.feature_names: Optional[List[str]] = None
        self.classes_: Optional[np.ndarray] = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "DecisionTreeBaseline":
        """Fit the decision tree."""
        self.feature_names = list(X.columns)

        X_filled = X.fillna(X.median())
        y_encoded = self.label_encoder.fit_transform(y)
        self.classes_ = self.label_encoder.classes_

        self.model.fit(X_filled, y_encoded)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class labels."""
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        y_pred = self.model.predict(X_filled)
        return self.label_encoder.inverse_transform(y_pred)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities."""
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        return self.model.predict_proba(X_filled)

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from the tree."""
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False)

        return importance_df


def train_baseline_category_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series
) -> Tuple[LogisticRegressionBaseline, Dict[str, float]]:
    """
    Train a baseline category classifier.

    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data

    Returns:
        (trained model, evaluation metrics)
    """
    model = LogisticRegressionBaseline()
    model.fit(X_train, y_train)

    train_metrics = model.evaluate(X_train, y_train)
    val_metrics = model.evaluate(X_val, y_val)

    results = {
        "train_auc": train_metrics["auc"],
        "val_auc": val_metrics["auc"],
        "n_features": train_metrics["n_features"],
    }

    return model, results
