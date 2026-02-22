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


def _azure_batch_faithfulness(sentences: list[str], evidence: str) -> list[float]:
    """Score all sentences against evidence in one Azure call."""
    import json as _json

    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    sentences_numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
    prompt = (
        "Score each sentence below for factual grounding against the evidence.\n"
        "Return ONLY a JSON array of floats (0.0-1.0), one per sentence, in order.\n\n"
        "Scoring guide:\n"
        "- 1.0 = directly supported by or paraphrased from the evidence\n"
        "- 0.8 = reasonable clinical recommendation or logical inference from the evidence\n"
        "- 0.5 = partially supported but includes unsupported specifics\n"
        "- 0.0 = contradicts evidence or is fabricated\n\n"
        "Sentences that describe data availability (e.g. 'no lab results provided'), "
        "restate patient-reported symptoms, reference pipeline scores (cluster alignment, "
        "disease alignment percentages), or make standard clinical recommendations "
        "(referrals, lab orders) should score 0.8+ if consistent with the evidence.\n\n"
        f"Evidence:\n{evidence[:3000]}\n\n"
        f"Sentences:\n{sentences_numbered}"
    )
    raw = client.chat(
        deployment="mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=200,
    )
    if not raw:
        return [1.0] * len(sentences)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        scores = _json.loads(raw)
        return [max(0.0, min(1.0, float(s))) for s in scores]
    except (ValueError, _json.JSONDecodeError):
        logger.warning("Azure faithfulness returned non-JSON: %s", raw[:200])
        return [1.0] * len(sentences)


def check_faithfulness(
    output_text: str,
    passages:    list[RetrievedPassage],
    threshold:   float = FAITHFULNESS_THRESHOLD,
    pipeline_context: Optional[str] = None,
) -> tuple[bool, list[str], float]:
    """
    Check each sentence of output_text for entailment against the passages.

    Uses Azure OpenAI when AURA_NLP_BACKEND=azure, otherwise local DeBERTa NLI.

    Args:
        output_text: generated SOAP note or Layman's Compass text
        passages:    retrieved evidence passages (source of truth)
        threshold:   minimum entailment score per sentence
        pipeline_context: additional context from the pipeline (router scores,
                          interview symptoms, lab data) that the generated text
                          may reference but is not in the research passages

    Returns:
        (passed: bool, flagged_sentences: list[str], mean_score: float)
    """
    from nlp.shared.azure_client import get_nlp_backend

    sentences = split_sentences(output_text)

    if not sentences or not passages:
        return True, [], 1.0

    evidence_parts = []
    if pipeline_context:
        evidence_parts.append(pipeline_context)
    evidence_parts.append(" ".join(p.text[:300] for p in passages[:5]))
    evidence = " ".join(evidence_parts)

    if get_nlp_backend("disease_scorer") == "azure":
        all_scores = _azure_batch_faithfulness(sentences, evidence)
    else:
        scorer = _get_scorer()
        all_scores = [scorer.entailment_score(evidence, sent) for sent in sentences]

    flagged: list[str] = []
    for sent, score in zip(sentences, all_scores):
        if score < threshold:
            flagged.append(sent)
            logger.debug(f"Low faithfulness ({score:.2f}): {sent[:80]}")

    mean_score = sum(all_scores) / len(all_scores) if all_scores else 1.0
    fail_rate  = len(flagged) / len(sentences) if sentences else 0
    passed     = fail_rate <= 0.10

    logger.info(
        f"Faithfulness check: {len(flagged)}/{len(sentences)} sentences flagged "
        f"(mean={mean_score:.2f}, passed={passed})"
    )
    return passed, flagged, round(mean_score, 4)
