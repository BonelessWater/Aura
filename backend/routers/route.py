from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.session import get_or_create_session

router = APIRouter()


class RouteRequest(BaseModel):
    patient_id: str
    medications: list[str] = []
    patient_age: int = 40
    patient_sex: str = "F"


@router.post("/route")
async def route(body: RouteRequest):
    """
    Score cluster alignment and disease candidates.
    Pulls lab_report, interview_result, and research_result from the session.
    Runs in heuristic mode (no GPU required).
    """
    from nlp.router.pipeline import run_router

    session = get_or_create_session(body.patient_id)

    if session.lab_report is None and session.interview_result is None:
        raise HTTPException(
            status_code=400,
            detail="No lab or interview data found for this patient. Run /extract or /interview first.",
        )

    try:
        router_output = await asyncio.to_thread(
            run_router,
            body.patient_id,
            session.lab_report,
            session.interview_result,
            session.research_result,
            body.medications,
            body.patient_age,
            body.patient_sex,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Router failed: {exc}") from exc

    session.router_output = router_output
    return {
        "patient_id": body.patient_id,
        "router_output": router_output.model_dump(mode="json"),
    }
