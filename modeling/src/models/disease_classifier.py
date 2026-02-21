"""
Stage 2: Disease Classifiers for Aura Dual-Scorer.

One classifier per disease cluster, trained on cluster-specific data.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report


class DiseaseClassifier:
    """
    XGBoost classifier for specific disease prediction within a cluster.
    """

    def __init__(self, cluster: str, diseases: List[str], params: Optional[Dict[str, Any]] = None):
        """
        Args:
            cluster: Cluster name ('systemic', 'gastrointestinal', 'endocrine')
            diseases: List of disease labels in this cluster
            params: XGBoost parameters
        """
        self.cluster = cluster
        self.diseases = diseases

        default_params = {
            'objective': 'multi:softprob',
            'num_class': len(diseases),
            'eval_metric': 'mlogloss',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'random_state': 42,
        }
        if params:
            default_params.update(params)

        self.params = default_params
        self.model: Optional[xgb.XGBClassifier] = None
        self.label_encoder = LabelEncoder()
        self.feature_names: Optional[List[str]] = None
        self.trained: bool = False

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs):
        """Train on cluster-specific data."""
        if X.empty:
            self.trained = False
            return self

        self.feature_names = list(X.columns)
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())

        y_series = pd.Series(y).astype(str)
        allowed = set(self.diseases)
        mask = y_series.isin(allowed)
        X_filled = X_filled.loc[mask]
        y_series = y_series.loc[mask]

        unique_labels = sorted(y_series.unique().tolist())
        if len(unique_labels) < 2:
            self.model = None
            self.trained = False
            return self

        self.label_encoder.fit(self.diseases)
        y_encoded = self.label_encoder.transform(y_series)

        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(X_filled, y_encoded, verbose=kwargs.get("verbose", False))
        self.trained = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict disease labels."""
        if not self.trained or self.model is None:
            raise ValueError("DiseaseClassifier is not trained.")
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        y_pred = self.model.predict(X_filled)
        return self.label_encoder.inverse_transform(y_pred)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict disease probabilities."""
        if not self.trained or self.model is None:
            raise ValueError("DiseaseClassifier is not trained.")
        X_filled = X[self.feature_names].fillna(X[self.feature_names].median())
        return self.model.predict_proba(X_filled)

    def get_disease_confidence(
        self,
        X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get predicted disease and confidence score.

        Returns:
            (predicted_diseases, confidence_scores)
        """
        probs = self.predict_proba(X)
        predicted_idx = probs.argmax(axis=1)
        confidence = probs.max(axis=1)
        predicted_diseases = self.label_encoder.inverse_transform(predicted_idx)
        return predicted_diseases, confidence

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, Any]:
        """
        Evaluate disease model performance.

        Returns:
            Dictionary with metrics
        """
        if not self.trained or self.model is None:
            return {"trained": False}

        y_series = pd.Series(y).astype(str)
        allowed = set(self.diseases)
        mask = y_series.isin(allowed)
        X_eval = X.loc[mask]
        y_series = y_series.loc[mask]

        if y_series.nunique() < 2:
            return {"trained": False}

        y_prob = self.predict_proba(X_eval)
        y_pred = self.predict(X_eval)
        y_true = self.label_encoder.transform(y_series)

        auc = roc_auc_score(y_true, y_prob, multi_class="ovr")
        report = classification_report(y_series, y_pred, output_dict=True)

        return {
            "trained": True,
            "auc": auc,
            "accuracy": report["accuracy"],
            "per_class": {
                label: report.get(label, {})
                for label in self.diseases
            }
        }

    def save(self, path: str) -> None:
        """Save model to file."""
        import joblib
        joblib.dump({
            "cluster": self.cluster,
            "diseases": self.diseases,
            "params": self.params,
            "model": self.model,
            "label_encoder": self.label_encoder,
            "feature_names": self.feature_names,
            "trained": self.trained,
        }, path)

    @classmethod
    def load(cls, path: str) -> "DiseaseClassifier":
        """Load model from file."""
        import joblib
        data = joblib.load(path)

        instance = cls(cluster=data["cluster"], diseases=data["diseases"], params=data["params"])
        instance.model = data["model"]
        instance.label_encoder = data["label_encoder"]
        instance.feature_names = data["feature_names"]
        instance.trained = data.get("trained", instance.model is not None)
        return instance


# Pre-configured classifiers for each cluster
class SystemicDiseaseClassifier(DiseaseClassifier):
    """Classifier for systemic autoimmune diseases."""

    DISEASES = ['SLE', 'RA', 'Sjogren', 'PsA', 'AS', 'Reactive_Arthritis', 'Control']

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__('systemic', self.DISEASES, params)


class GIDiseaseClassifier(DiseaseClassifier):
    """Classifier for gastrointestinal autoimmune diseases."""

    DISEASES = ['IBD', 'Celiac', 'Functional_GI', 'Control']

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__('gastrointestinal', self.DISEASES, params)


class EndocrineDiseaseClassifier(DiseaseClassifier):
    """Classifier for endocrine autoimmune diseases."""

    DISEASES = ['Hashimoto', 'Graves', 'T1D', 'Control']

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__('endocrine', self.DISEASES, params)
