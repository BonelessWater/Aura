"""
Hierarchical Dual-Scorer for Aura.

Combines Category Classifier (Stage 1) and Disease Classifiers (Stage 2)
into a unified prediction pipeline.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import joblib
from pathlib import Path

from .category_classifier import CategoryClassifier
from .disease_classifier import DiseaseClassifier


@dataclass
class DualScoreResult:
    """Result from dual-scorer prediction."""

    # Stage 1 outputs
    category: str
    category_confidence: float
    category_probabilities: Dict[str, float]

    # Stage 2 outputs (optional - may not have disease-level model)
    disease: Optional[str] = None
    disease_confidence: Optional[float] = None
    disease_probabilities: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "category_confidence": self.category_confidence,
            "category_probabilities": self.category_probabilities,
            "disease": self.disease,
            "disease_confidence": self.disease_confidence,
            "disease_probabilities": self.disease_probabilities,
        }

    def __str__(self) -> str:
        result = f"Category: {self.category} ({self.category_confidence:.1%} confidence)"
        if self.disease:
            result += f"\nDisease: {self.disease} ({self.disease_confidence:.1%} confidence)"
        return result

    def to_clinical_summary(self) -> str:
        """Format as clinical summary."""
        lines = [
            f"AURA Risk Assessment",
            f"=" * 40,
            f"Primary Classification: {self.category.upper()}",
            f"Confidence: {self.category_confidence:.1%}",
            f"",
            f"Category Probabilities:",
        ]
        for cat, prob in sorted(
            self.category_probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  - {cat}: {prob:.1%}")

        if self.disease:
            lines.extend([
                f"",
                f"Suspected Condition: {self.disease}",
                f"Disease Confidence: {self.disease_confidence:.1%}",
            ])

        return "\n".join(lines)


class DualScorer:
    """
    Hierarchical dual-scoring pipeline.

    Stage 1: Predict disease category (Healthy/Systemic/GI/Endocrine)
    Stage 2: (Future) Predict specific disease within predicted category
    """

    PRIORITY_CATEGORIES = ["healthy", "systemic", "gastrointestinal", "endocrine"]

    def __init__(
        self,
        category_classifier: Optional[CategoryClassifier] = None,
        categories: List[str] = None,
    ):
        """
        Args:
            category_classifier: Pre-trained category classifier
            categories: List of category labels
        """
        self.categories = categories or self.PRIORITY_CATEGORIES
        self.category_classifier = category_classifier
        self.feature_names: Optional[List[str]] = None
        self.disease_classifiers: Dict[str, DiseaseClassifier] = {}

    def fit(
        self,
        X: pd.DataFrame,
        y_category: pd.Series,
        y_disease: Optional[pd.Series] = None,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs
    ) -> "DualScorer":
        """
        Train the dual-scorer.

        Args:
            X: Feature matrix
            y_category: Category labels
            y_disease: Optional disease labels for stage-2 training
            X_val, y_val: Optional validation data
        """
        self.feature_names = list(X.columns)

        # Train category classifier
        self.category_classifier = CategoryClassifier(categories=self.categories)

        if X_val is not None and y_val is not None:
            self.category_classifier.fit(
                X, y_category,
                eval_set=(X_val, y_val),
                **kwargs
            )
        else:
            self.category_classifier.fit(X, y_category, **kwargs)

        if y_disease is not None:
            self._train_disease_classifiers(X, y_category, y_disease)

        return self

    def predict(self, X: pd.DataFrame) -> List[DualScoreResult]:
        """
        Generate dual-score predictions for all samples.

        Returns:
            List of DualScoreResult for each sample
        """
        if self.category_classifier is None:
            raise ValueError("Model not trained. Call fit() first.")

        # Stage 1: Category prediction
        category_probs = self.category_classifier.predict_proba(X)
        categories, confidences = self.category_classifier.get_category_confidence(X)

        # LabelEncoder sorts classes alphabetically — use its order to map
        # probability columns to the correct category names.
        clf_classes = list(self.category_classifier.label_encoder.classes_)

        results = []
        for i in range(len(X)):
            prob_dict = {
                clf_classes[j]: float(category_probs[i, j])
                for j in range(len(clf_classes))
            }

            result = DualScoreResult(
                category=categories[i],
                category_confidence=float(confidences[i]),
                category_probabilities=prob_dict,
            )
            results.append(result)

        if self.disease_classifiers:
            for cluster, clf in self.disease_classifiers.items():
                if not clf.trained:
                    continue
                idxs = [i for i, cat in enumerate(categories) if cat == cluster]
                if not idxs:
                    continue
                X_sub = X.iloc[idxs]
                probs = clf.predict_proba(X_sub)
                pred_idx = probs.argmax(axis=1)
                disease_labels = clf.label_encoder.inverse_transform(pred_idx)
                confidences = probs.max(axis=1)

                for j, i in enumerate(idxs):
                    results[i].disease = disease_labels[j]
                    results[i].disease_confidence = float(confidences[j])
                    results[i].disease_probabilities = {
                        disease: float(probs[j, k])
                        for k, disease in enumerate(clf.diseases)
                    }

        return results

    def predict_single(self, x: pd.Series) -> DualScoreResult:
        """Predict for a single patient."""
        X = pd.DataFrame([x])
        return self.predict(X)[0]

    def get_category_predictions(
        self,
        X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get category predictions with probabilities.

        Returns:
            (predicted_categories, confidence_scores, probability_matrix)
        """
        categories, confidences = self.category_classifier.get_category_confidence(X)
        probs = self.category_classifier.predict_proba(X)
        return categories, confidences, probs

    def evaluate(
        self,
        X: pd.DataFrame,
        y_true: pd.Series
    ) -> Dict[str, Any]:
        """Evaluate the dual-scorer."""
        return self.category_classifier.evaluate(X, y_true)

    def evaluate_disease(
        self,
        X: pd.DataFrame,
        y_category: pd.Series,
        y_disease: pd.Series
    ) -> Dict[str, Any]:
        """Evaluate disease classifiers by cluster."""
        results: Dict[str, Any] = {}
        if not self.disease_classifiers:
            return results

        for cluster, clf in self.disease_classifiers.items():
            if not clf.trained:
                continue
            mask = y_category.isin([cluster, "healthy"])
            if not mask.any():
                continue

            y_d = y_disease.loc[mask].copy()
            y_cat = y_category.loc[mask]
            y_d.loc[(y_cat == "healthy") & (y_d.isna())] = "Control"
            y_d = y_d.dropna()
            if y_d.nunique() < 2:
                continue

            X_sub = X.loc[y_d.index]
            results[cluster] = clf.evaluate(X_sub, y_d)

        return results

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from category classifier."""
        return self.category_classifier.get_feature_importance()

    def save(self, path: str) -> None:
        """Save the dual-scorer to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self.category_classifier.save(str(path / "category_classifier.joblib"))

        disease_meta: Dict[str, str] = {}
        if self.disease_classifiers:
            disease_dir = path / "disease_classifiers"
            disease_dir.mkdir(parents=True, exist_ok=True)
            for cluster, clf in self.disease_classifiers.items():
                if not clf.trained:
                    continue
                filename = f"{cluster}_disease_classifier.joblib"
                clf.save(str(disease_dir / filename))
                disease_meta[cluster] = filename

        joblib.dump({
            "categories": self.categories,
            "feature_names": self.feature_names,
            "disease_models": disease_meta,
        }, path / "dual_scorer_meta.joblib")

    @classmethod
    def load(cls, path: str) -> "DualScorer":
        """Load the dual-scorer from disk."""
        path = Path(path)

        meta = joblib.load(path / "dual_scorer_meta.joblib")
        category_clf = CategoryClassifier.load(str(path / "category_classifier.joblib"))

        instance = cls(
            category_classifier=category_clf,
            categories=meta["categories"]
        )
        instance.feature_names = meta["feature_names"]
        instance.disease_classifiers = {}

        disease_meta = meta.get("disease_models", {})
        if disease_meta:
            disease_dir = path / "disease_classifiers"
            for cluster, filename in disease_meta.items():
                clf = DiseaseClassifier.load(str(disease_dir / filename))
                if clf.trained:
                    instance.disease_classifiers[cluster] = clf

        return instance

    @staticmethod
    def _order_disease_labels(labels: List[str]) -> List[str]:
        labels = [label for label in labels if label]
        control = [label for label in labels if label == "Control"]
        others = sorted([label for label in labels if label != "Control"])
        return others + control

    def _train_disease_classifiers(
        self,
        X: pd.DataFrame,
        y_category: pd.Series,
        y_disease: pd.Series,
    ) -> None:
        self.disease_classifiers = {}
        for cluster in [c for c in self.categories if c != "healthy"]:
            mask = y_category.isin([cluster, "healthy"])
            if not mask.any():
                continue

            y_d = y_disease.loc[mask].copy()
            y_cat = y_category.loc[mask]
            y_d.loc[(y_cat == "healthy") & (y_d.isna())] = "Control"
            y_d = y_d.dropna()
            if y_d.nunique() < 2:
                continue

            X_sub = X.loc[y_d.index]
            diseases = self._order_disease_labels(sorted(y_d.unique().tolist()))
            clf = DiseaseClassifier(cluster=cluster, diseases=diseases)
            clf.fit(X_sub, y_d)

            if clf.trained:
                self.disease_classifiers[cluster] = clf


def train_dual_scorer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    y_disease_train: Optional[pd.Series] = None,
    y_disease_val: Optional[pd.Series] = None,
    y_disease_test: Optional[pd.Series] = None,
) -> Tuple[DualScorer, Dict[str, Any]]:
    """
    Train and evaluate a full dual-scorer pipeline.

    Args:
        X_train, y_train: Training data
        y_disease_train: Optional disease labels for training
        X_val, y_val: Validation data
        y_disease_val: Optional disease labels for validation
        X_test, y_test: Test data
        y_disease_test: Optional disease labels for testing

    Returns:
        (trained DualScorer, comprehensive results)
    """
    # Train
    scorer = DualScorer()
    scorer.fit(
        X_train, y_train,
        y_disease=y_disease_train,
        X_val=X_val,
        y_val=y_val,
        verbose=False
    )

    # Evaluate on all splits
    train_metrics = scorer.evaluate(X_train, y_train)
    val_metrics = scorer.evaluate(X_val, y_val)
    test_metrics = scorer.evaluate(X_test, y_test)

    results = {
        "train": train_metrics,
        "val": val_metrics,
        "test": test_metrics,
        "feature_importance": scorer.get_feature_importance(),
    }

    if y_disease_train is not None and y_disease_val is not None and y_disease_test is not None:
        results["disease"] = {
            "train": scorer.evaluate_disease(X_train, y_train, y_disease_train),
            "val": scorer.evaluate_disease(X_val, y_val, y_disease_val),
            "test": scorer.evaluate_disease(X_test, y_test, y_disease_test),
        }

    return scorer, results
