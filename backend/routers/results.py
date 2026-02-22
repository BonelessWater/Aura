from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.session import get_session
from nlp.shared.schemas import (
    LabReport,
    InterviewResult,
    ResearchResult,
    RouterOutput,
    TranslatorOutput,
)

router = APIRouter()


class ResultsResponse(BaseModel):
    patient_id: str
    lab_report: Optional[LabReport] = None
    interview_result: Optional[InterviewResult] = None
    research_result: Optional[ResearchResult] = None
    router_output: Optional[RouterOutput] = None
    translator_output: Optional[TranslatorOutput] = None


@router.get("/results/{patient_id}", response_model=ResultsResponse)
async def get_results(patient_id: str):
    """
    Return all pipeline outputs stored in the patient session.

    Returns 404 if no session exists for the given patient_id.
    Fields are null for pipeline phases that have not yet completed.
    """
    session = get_session(patient_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No session found for patient_id '{patient_id}'.",
        )

    return ResultsResponse(
        patient_id=patient_id,
        lab_report=session.lab_report,
        interview_result=session.interview_result,
        research_result=session.research_result,
        router_output=session.router_output,
        translator_output=session.translator_output,
    )
