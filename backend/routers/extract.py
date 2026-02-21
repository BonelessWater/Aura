from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.config import Settings, get_settings
from backend.session import get_or_create_session
from backend.utils.file_handling import save_uploads

router = APIRouter()


@router.post("/extract")
async def extract(
    patient_id: Annotated[str, Form()],
    patient_age: Annotated[int, Form()] = 40,
    patient_sex: Annotated[str, Form()] = "F",
    files: Annotated[list[UploadFile], File()] = [],
    settings: Settings = Depends(get_settings),
):
    """
    Upload lab report PDFs and extract biomarkers into a LabReport.
    Result is stored in the patient session for downstream phases.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    from nlp.extractor.pipeline import run_extractor

    session = get_or_create_session(patient_id)

    async with save_uploads(files, patient_id) as pdf_paths:
        try:
            lab_report = await asyncio.to_thread(
                run_extractor,
                patient_id,
                [str(p) for p in pdf_paths],
                patient_age,
                patient_sex,
                settings.write_to_databricks,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Extractor failed: {exc}",
            ) from exc

    session.lab_report = lab_report
    return {"patient_id": patient_id, "lab_report": lab_report.model_dump(mode="json")}
