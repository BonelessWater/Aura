"""
Moderator Pipeline — Forum Moderation Filter (Phase 7 orchestrator).

Two-stage pipeline:
  Stage 1: Fast DistilBERT binary classifier (< 50ms)
  Stage 2: NER-based evidence extraction (only on Stage 1 positives)

Returns SUPPRESS / FLAG / ALLOW / DISCLAIMER with reason.

Usage:
    from nlp.moderator.pipeline import run_moderator
    result = run_moderator(post_id="p123", text="Take 500mg of X daily for lupus")
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from nlp.shared.schemas import ModerationAction, ModerationResult
from nlp.shared.thought_stream import ThoughtStream
from nlp.moderator.binary_classifier import get_classifier
from nlp.moderator.ner_extractor import extract_moderation_entities, decide_action

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = "\n\n*Always consult a doctor before changing any medication or treatment.*"


def run_moderator(
    post_id:    str,
    text:       str,
    user_id:    Optional[str] = None,
    log_to_delta: bool = True,
) -> ModerationResult:
    """
    Run the two-stage moderation pipeline on a forum post.

    Stage 1 runs on every post (fast).
    Stage 2 only runs on posts classified as 'potentially_harmful'.

    Returns a ModerationResult with action, confidence, and reason.
    """
    # ── Stage 1: Binary classifier ────────────────────────────────────────────
    classifier = get_classifier()
    label, confidence = classifier.predict(text)

    if label == "safe":
        result = ModerationResult(
            post_id    = post_id,
            text       = text,
            action     = ModerationAction.ALLOW,
            confidence = confidence,
            reason     = "Stage 1: classified as safe",
        )
        if log_to_delta:
            _log_decision(result, user_id)
        return result

    # ── Stage 2: NER extraction (only on potentially_harmful) ─────────────────
    entities     = extract_moderation_entities(text)
    action_str, reason = decide_action(entities)
    action       = ModerationAction(action_str)

    # Apply disclaimer text to ALLOW+DISCLAIMER posts
    if action == ModerationAction.DISCLAIMER:
        text = text + DISCLAIMER_TEXT

    result = ModerationResult(
        post_id            = post_id,
        text               = text,
        action             = action,
        confidence         = confidence,
        extracted_drugs    = entities.drugs,
        extracted_dosages  = entities.dosages,
        reason             = reason,
    )

    ThoughtStream.emit(
        agent="The Moderator",
        step="moderation_decision",
        summary=(
            f"Post {post_id}: {action.value} (confidence={confidence:.2f}). "
            f"Drugs: {entities.drugs or 'none'}. "
            f"Dosages: {entities.dosages or 'none'}. "
            f"Reason: {reason}"
        ),
    )

    if log_to_delta:
        _log_decision(result, user_id)

    return result


def _log_decision(result: ModerationResult, user_id: Optional[str]) -> None:
    """Append moderation decision to aura.training.moderator_feedback."""
    try:
        from nlp.shared.databricks_client import get_client
        import pandas as pd
        import io

        client = get_client()
        client.run_sql("""
            CREATE TABLE IF NOT EXISTS aura.training.moderator_feedback (
                post_id          STRING,
                text             STRING,
                action           STRING,
                confidence       DOUBLE,
                extracted_drugs  STRING,
                extracted_dosages STRING,
                reason           STRING,
                user_id          STRING,
                logged_at        STRING
            ) USING DELTA
        """)

        row = {
            "post_id":           result.post_id,
            "text":              result.text[:1000],
            "action":            result.action.value,
            "confidence":        result.confidence,
            "extracted_drugs":   ",".join(result.extracted_drugs),
            "extracted_dosages": ",".join(result.extracted_dosages),
            "reason":            result.reason or "",
            "user_id":           user_id or "",
            "logged_at":         datetime.utcnow().isoformat(),
        }
        df  = pd.DataFrame([row])
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)

        vol_path = f"/Volumes/aura/training/raw_files/moderator_{result.post_id}.parquet"
        client.upload_bytes(buf, vol_path)
        client.run_sql(
            f"INSERT INTO aura.training.moderator_feedback "
            f"SELECT * FROM parquet.`{vol_path}`"
        )
    except Exception as e:
        logger.debug(f"Moderator Delta log failed: {e}")
