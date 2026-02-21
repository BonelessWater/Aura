from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.config import Settings, get_settings
from backend.session import get_or_create_session
from backend.utils.file_handling import save_uploads

router = APIRouter()


@router.post("/interview")
async def interview(
    patient_id: Annotated[str, Form()],
    symptom_text: Annotated[str, Form()],
    images: Annotated[list[UploadFile], File()] = [],
    videos: Annotated[list[UploadFile], File()] = [],
    settings: Settings = Depends(get_settings),
):
    """
    Extract symptom entities from free-text narrative and optional images/video.
    Result is stored in the patient session.
    """
    if not symptom_text.strip():
        raise HTTPException(status_code=400, detail="symptom_text must not be empty.")

    from nlp.interviewer.pipeline import run_interviewer

    session = get_or_create_session(patient_id)

    async with save_uploads(images, patient_id) as image_paths:
        async with save_uploads(videos, patient_id) as video_paths:
            try:
                interview_result = await asyncio.to_thread(
                    run_interviewer,
                    patient_id,
                    symptom_text,
                    [str(p) for p in image_paths],
                    [str(p) for p in video_paths],
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Interviewer failed: {exc}",
                ) from exc

    session.interview_result = interview_result
    return {
        "patient_id": patient_id,
        "interview_result": interview_result.model_dump(mode="json"),
    }
