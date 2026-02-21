from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.utils.background import get_job

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Poll for the result of a background task (research, full pipeline).

    status values:
      - queued   — task is waiting to start
      - running  — task is in progress
      - done     — task completed; result is populated
      - error    — task failed; error message is populated
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return {
        "job_id": job.job_id,
        "patient_id": job.patient_id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }
