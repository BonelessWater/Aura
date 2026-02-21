from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ModerateRequest(BaseModel):
    post_id: str
    text: str
    user_id: Optional[str] = None


@router.post("/moderate")
async def moderate(body: ModerateRequest):
    """
    Two-stage content moderation for forum posts.
    Stage 1: DistilBERT binary classifier (fast).
    Stage 2: Drug/dosage NER + decision logic (only on Stage 1 positives).
    Stateless — no session required.
    """
    from nlp.moderator.pipeline import run_moderator

    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")

    try:
        result = await asyncio.to_thread(
            run_moderator,
            body.post_id,
            body.text,
            body.user_id,
            False,  # log_to_delta — off by default, no Databricks required
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Moderator failed: {exc}") from exc

    return result.model_dump(mode="json")
