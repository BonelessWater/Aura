"""
Faithfulness Checker — The Translator, Step 5.4.

Runs NLI sentence-level factuality verification on generated text.
Uses the same cross-encoder/nli-deberta-v3-base as the Router.

A sentence passes if its entailment score against its cited passage >= 0.7.
If > 10% of sentences fail, regeneration is triggered.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from nlp.shared.schemas import RetrievedPassage
from nlp.router.disease_scorer import _get_scorer

logger = logging.getLogger(__name__)

FAITHFULNESS_THRESHOLD = 0.70


def split_sentences(text: str) -> list[str]:
    """Split output text into sentences."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]


def check_faithfulness(
    output_text: str,
    passages:    list[RetrievedPassage],
    threshold:   float = FAITHFULNESS_THRESHOLD,
) -> tuple[bool, list[str], float]:
    """
    Check each sentence of output_text for entailment against the passages.

    Args:
        output_text: generated SOAP note or Layman's Compass text
        passages:    retrieved evidence passages (source of truth)
        threshold:   minimum entailment score per sentence

    Returns:
        (passed: bool, flagged_sentences: list[str], mean_score: float)
    """
    scorer    = _get_scorer()
    sentences = split_sentences(output_text)

    if not sentences or not passages:
        return True, [], 1.0

    # Concatenate passage texts as the knowledge source
    evidence = " ".join(p.text[:300] for p in passages[:5])

    scores:   list[float] = []
    flagged:  list[str]   = []

    for sent in sentences:
        score = scorer.entailment_score(evidence, sent)
        scores.append(score)
        if score < threshold:
            flagged.append(sent)
            logger.debug(f"Low faithfulness ({score:.2f}): {sent[:80]}")

    mean_score   = sum(scores) / len(scores) if scores else 1.0
    fail_rate    = len(flagged) / len(sentences) if sentences else 0
    passed       = fail_rate <= 0.10   # pass if ≤ 10% sentences fail

    logger.info(
        f"Faithfulness check: {len(flagged)}/{len(sentences)} sentences flagged "
        f"(mean={mean_score:.2f}, passed={passed})"
    )
    return passed, flagged, round(mean_score, 4)
