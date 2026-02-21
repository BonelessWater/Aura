from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.session import get_or_create_session

router = APIRouter()


class TranslateRequest(BaseModel):
    patient_id: str


@router.post("/translate")
async def translate(body: TranslateRequest):
    """
    Generate SOAP note + Layman's Compass from all prior phase results.
    Uses fallback templates if vLLM is not available.
    Pulls all results from the patient session.
    """
    from nlp.translator.pipeline import run_translator

    session = get_or_create_session(body.patient_id)

    if session.router_output is None:
        raise HTTPException(
            status_code=400,
            detail="No router output found for this patient. Run /route first.",
        )

    try:
        translator_output = await asyncio.to_thread(
            run_translator,
            body.patient_id,
            session.lab_report,
            session.interview_result,
            session.research_result,
            session.router_output,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translator failed: {exc}") from exc

    session.translator_output = translator_output
    return {
        "patient_id": body.patient_id,
        "translator_output": translator_output.model_dump(mode="json"),
    }
