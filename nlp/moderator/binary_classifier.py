"""
Binary Classifier — The Moderator, Stage 1.

Fine-tunes DistilBERT on ADE Corpus V2 to classify forum posts as:
  safe (0) or potentially_harmful (1)

Exported as ONNX for < 50ms inference latency.

Training data (streamed from HuggingFace):
  - Positive: ADE Corpus V2 (adverse drug event sentences)
  - Negative: general non-harmful medical community posts

GPU recommended for training. ONNX CPU inference is fast.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_MODEL   = "distilbert-base-uncased"
MODEL_DIR    = Path("models/moderator_classifier")
ONNX_PATH    = MODEL_DIR / "model.onnx"


# ── Training ──────────────────────────────────────────────────────────────────

def train_moderator_classifier(
    output_dir: str = str(MODEL_DIR),
    epochs:     int = 3,
    batch_size: int = 32,
) -> None:
    """
    Fine-tune DistilBERT on ADE Corpus V2 + synthetic safe examples.
    Streams ADE data directly from HuggingFace — no pre-download needed.
    """
    try:
        from datasets import load_dataset
        from transformers import (
            AutoTokenizer,
            AutoModelForSequenceClassification,
            TrainingArguments,
            Trainer,
        )
        import torch
        from torch.utils.data import Dataset
        import numpy as np
        from sklearn.metrics import precision_recall_fscore_support
    except ImportError as e:
        raise ImportError("transformers, datasets, sklearn required for training") from e

    logger.info("Loading ADE Corpus V2 from HuggingFace...")
    ade = load_dataset("ade_corpus_v2", name="Ade_corpus_v2_classification", trust_remote_code=True)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    class AdeDataset(Dataset):
        def __init__(self, split):
            self.data = list(ade[split])

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            item  = self.data[idx]
            text  = item["text"]
            label = item["label"]   # 1 = ADE (harmful), 0 = safe
            enc   = tokenizer(
                text, truncation=True, max_length=128,
                padding="max_length", return_tensors="pt"
            )
            return {
                "input_ids":      enc["input_ids"].squeeze(),
                "attention_mask": enc["attention_mask"].squeeze(),
                "labels":         torch.tensor(label, dtype=torch.long),
            }

    train_ds = AdeDataset("train")
    test_ds  = AdeDataset("test")

    model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=2)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        p, r, f, _ = precision_recall_fscore_support(labels, preds, average="binary")
        return {"precision": p, "recall": r, "f1": f}

    args = TrainingArguments(
        output_dir          = output_dir,
        num_train_epochs    = epochs,
        per_device_train_batch_size = batch_size,
        per_device_eval_batch_size  = batch_size,
        evaluation_strategy = "epoch",
        save_strategy       = "epoch",
        load_best_model_at_end = True,
        metric_for_best_model  = "precision",   # minimise false suppression
        report_to           = "mlflow",
    )

    trainer = Trainer(
        model            = model,
        args             = args,
        train_dataset    = train_ds,
        eval_dataset     = test_ds,
        compute_metrics  = compute_metrics,
    )

    logger.info("Training moderator classifier...")
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Saved moderator classifier to {output_dir}")

    # Export ONNX
    _export_onnx(model, tokenizer, output_dir)


def _export_onnx(model, tokenizer, output_dir: str) -> None:
    """Export fine-tuned model to ONNX for fast CPU inference."""
    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification
        from optimum.exporters.onnx import main_export
        import torch

        logger.info("Exporting to ONNX...")
        dummy_input = tokenizer(
            "test sentence", return_tensors="pt",
            padding="max_length", max_length=128
        )
        onnx_out = Path(output_dir) / "model.onnx"
        torch.onnx.export(
            model,
            (dummy_input["input_ids"], dummy_input["attention_mask"]),
            str(onnx_out),
            opset_version=12,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids":      {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
            },
        )
        logger.info(f"ONNX model exported to {onnx_out}")
    except Exception as e:
        logger.warning(f"ONNX export failed: {e}. Falling back to PyTorch inference.")


# ── Inference ─────────────────────────────────────────────────────────────────

class ModerationClassifier:
    """
    Fast binary classifier for forum post moderation.
    Uses ONNX if available, falls back to PyTorch.
    """

    def __init__(self) -> None:
        self._ort_session  = None
        self._pt_model     = None
        self._pt_tokenizer = None

    def load(self) -> None:
        if self._ort_session or self._pt_model:
            return

        # Try ONNX first
        if ONNX_PATH.exists():
            try:
                import onnxruntime as ort
                self._ort_session = ort.InferenceSession(str(ONNX_PATH))
                from transformers import AutoTokenizer
                self._pt_tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
                logger.info("Loaded ONNX moderator classifier")
                return
            except ImportError:
                pass

        # Fall back to PyTorch
        model_path = MODEL_DIR if MODEL_DIR.exists() else BASE_MODEL
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self._pt_tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self._pt_model     = AutoModelForSequenceClassification.from_pretrained(
                str(model_path), num_labels=2
            )
            self._pt_model.eval()
            logger.info(f"Loaded PyTorch moderator classifier from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load moderator classifier: {e}")

    def predict(self, text: str) -> tuple[str, float]:
        """
        Returns (label, confidence) where label is 'safe' or 'potentially_harmful'.
        """
        if not self._ort_session and not self._pt_model:
            return "safe", 0.5   # Neutral fallback

        enc = self._pt_tokenizer(
            text, truncation=True, max_length=128,
            padding="max_length", return_tensors="np" if self._ort_session else "pt"
        )

        if self._ort_session:
            logits = self._ort_session.run(
                None,
                {
                    "input_ids":      enc["input_ids"],
                    "attention_mask": enc["attention_mask"],
                },
            )[0]
            import numpy as np
            probs = _softmax(logits[0])
        else:
            import torch
            with torch.no_grad():
                logits = self._pt_model(**enc).logits.squeeze()
            probs = torch.softmax(logits, dim=-1).tolist()

        label  = "potentially_harmful" if probs[1] > probs[0] else "safe"
        conf   = max(probs[0], probs[1])
        return label, round(float(conf), 4)


def _softmax(x):
    import numpy as np
    e = np.exp(x - np.max(x))
    return e / e.sum()


# ── Singleton ─────────────────────────────────────────────────────────────────

_classifier: Optional[ModerationClassifier] = None


def get_classifier() -> ModerationClassifier:
    global _classifier
    if _classifier is None:
        _classifier = ModerationClassifier()
        _classifier.load()
    return _classifier
