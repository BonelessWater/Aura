"""
Retrieval Quality Gate -- CRAG-inspired confidence check on initial retrieval.

Evaluates retrieval quality using a three-tier threshold system inspired by
Corrective RAG (RAG_Techniques/crag.py) and Multi-Agent-Medical-Assistant
confidence routing (agents/agent_decision.py).

Thresholds:
  - HIGH   (>= 0.70): Use retrieved documents directly
  - MEDIUM (0.40-0.70): Supplement with additional sources
  - LOW    (< 0.40): Widen search (remove cluster filter, expand queries)

The confidence score is the mean of the top-3 passage scores, following
the Multi-Agent-Medical-Assistant pattern of averaging top-k combined_score
values for routing decisions.

Usage:
    from nlp.reportagent.retrieval_gate import assess_retrieval_quality
    quality = assess_retrieval_quality(research_result)
    # quality = {"confidence": 0.72, "tier": "high", "action": "proceed", ...}
"""

from __future__ import annotations

import logging

from nlp.shared.schemas import ResearchResult

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE = 0.70
MEDIUM_CONFIDENCE = 0.40
LOW_CONFIDENCE = 0.20


def assess_retrieval_quality(research_result: ResearchResult) -> dict:
    """
    Evaluate retrieval quality using CRAG-inspired three-tier thresholds.

    Computes confidence as the mean of the top-3 passage scores.
    Routes to one of three actions based on the confidence tier.

    Args:
        research_result: The output from the Researcher pipeline containing
            scored and reranked passages.

    Returns:
        dict with keys:
            confidence (float): Mean of top-3 passage scores.
            tier (str): "high", "medium", or "low".
            action (str): "proceed", "supplement", or "widen_search".
            passage_count (int): Total number of passages available.
    """
    if not research_result.passages:
        logger.info(
            "Retrieval quality gate: no passages available, tier=low action=widen_search"
        )
        return {
            "confidence": 0.0,
            "tier": "low",
            "action": "widen_search",
            "passage_count": 0,
        }

    # Average of top-3 passage scores (Multi-Agent-Medical-Assistant pattern)
    top_scores = [p.score for p in research_result.passages[:3]]
    confidence = sum(top_scores) / len(top_scores)

    if confidence >= HIGH_CONFIDENCE:
        tier, action = "high", "proceed"
    elif confidence >= MEDIUM_CONFIDENCE:
        tier, action = "medium", "supplement"
    else:
        tier, action = "low", "widen_search"

    logger.info(
        "Retrieval quality gate: confidence=%.3f tier=%s action=%s passages=%d",
        confidence, tier, action, len(research_result.passages),
    )

    return {
        "confidence": confidence,
        "tier": tier,
        "action": action,
        "passage_count": len(research_result.passages),
    }
