"""
Re-ranker — The Researcher, Step 4.

Uses MedCPT Cross-Encoder (NCBI) to re-rank the top-50 VS candidates
down to top-10 passages ordered by clinical relevance.

Model: ncbi/MedCPT-Cross-Encoder
  - Purpose-built for PubMed retrieval
  - Input: (query, passage) → relevance score
  - No fine-tuning required

GPU: beneficial but not required (runs on CPU, ~100ms per pair).
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import RetrievedPassage

logger = logging.getLogger(__name__)

RERANK_MODEL = "ncbi/MedCPT-Cross-Encoder"
TOP_K_FINAL  = 10


class MedCPTReranker:
    """Cross-encoder re-ranker using MedCPT."""

    def __init__(self) -> None:
        self._model     = None
        self._tokenizer = None

    def load(self) -> None:
        if self._model:
            return
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            self._tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL)
            self._model     = AutoModelForSequenceClassification.from_pretrained(RERANK_MODEL)
            self._model.eval()
            logger.info(f"Loaded reranker: {RERANK_MODEL}")
        except Exception as e:
            logger.warning(f"MedCPT reranker unavailable: {e}. Returning candidates by VS score.")

    def score(self, query: str, passages: list[str]) -> list[float]:
        """
        Score (query, passage) pairs. Returns list of relevance scores.
        Falls back to [0.0, ...] if model not available.
        """
        if not self._model:
            return [0.0] * len(passages)
        try:
            import torch
            pairs  = [[query, p[:512]] for p in passages]
            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = self._model(**inputs).logits.squeeze(-1)
            return logits.tolist()
        except Exception as e:
            logger.warning(f"Reranker inference failed: {e}")
            return [0.0] * len(passages)


def rerank(
    query:      str,
    candidates: list[RetrievedPassage],
    top_k:      int = TOP_K_FINAL,
) -> list[RetrievedPassage]:
    """
    Re-rank VS candidates using MedCPT cross-encoder.

    Args:
        query:      the primary patient query string
        candidates: top-50 passages from Vector Search
        top_k:      number of passages to return (default 10)

    Returns:
        top_k passages sorted by cross-encoder score (descending)
    """
    if not candidates:
        return []

    ranker = _get_reranker()
    texts  = [p.text for p in candidates]
    scores = ranker.score(query, texts)

    # Combine VS score (semantic) + cross-encoder score (relevance)
    for passage, ce_score in zip(candidates, scores):
        passage.score = 0.4 * passage.score + 0.6 * ce_score

    ranked = sorted(candidates, key=lambda p: p.score, reverse=True)
    return ranked[:top_k]


# ── Singleton ─────────────────────────────────────────────────────────────────

_reranker: Optional[MedCPTReranker] = None


def _get_reranker() -> MedCPTReranker:
    global _reranker
    if _reranker is None:
        _reranker = MedCPTReranker()
        _reranker.load()
    return _reranker
