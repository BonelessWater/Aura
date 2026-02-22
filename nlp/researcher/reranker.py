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
        from nlp.shared.azure_client import get_nlp_backend
        if get_nlp_backend("reranker") == "azure":
            logger.info("Reranker using Azure backend, skipping local model load")
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


def _azure_rerank_scores(query: str, passages: list[str]) -> list[float]:
    """Score query-passage relevance using Azure OpenAI instead of MedCPT."""
    import json as _json

    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    passages_numbered = "\n".join(f"{i+1}. {p[:300]}" for i, p in enumerate(passages))
    prompt = (
        f"Score the relevance of each passage to the query on a scale of 0.0 to 10.0.\n"
        f"Return ONLY a JSON array of floats, one per passage, in the same order.\n\n"
        f"Query: {query}\n\n"
        f"Passages:\n{passages_numbered}"
    )
    raw = client.chat(
        deployment="nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=200,
    )
    if not raw:
        return [0.0] * len(passages)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        scores = _json.loads(raw)
        # Normalize 0-10 scale to roughly match cross-encoder logit range
        return [float(s) - 5.0 for s in scores]
    except (ValueError, _json.JSONDecodeError):
        logger.warning("Azure reranker returned non-JSON: %s", raw[:200])
        return [0.0] * len(passages)


def rerank(
    query:      str,
    candidates: list[RetrievedPassage],
    top_k:      int = TOP_K_FINAL,
) -> list[RetrievedPassage]:
    """
    Re-rank VS candidates using MedCPT cross-encoder or Azure OpenAI.

    Uses Azure OpenAI when AURA_NLP_BACKEND=azure, otherwise local MedCPT.

    Args:
        query:      the primary patient query string
        candidates: top-50 passages from Vector Search
        top_k:      number of passages to return (default 10)

    Returns:
        top_k passages sorted by cross-encoder score (descending)
    """
    if not candidates:
        return []

    from nlp.shared.azure_client import get_nlp_backend

    texts = [p.text for p in candidates]

    if get_nlp_backend("reranker") == "azure":
        scores = _azure_rerank_scores(query, texts)
    else:
        ranker = _get_reranker()
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
