from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.config import databricks_available
from backend.session import get_or_create_session, push_event
from backend.utils.background import create_job, get_job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/report/{person_id}")
async def generate_report_endpoint(person_id: str):
    """
    Generate a medical research report for a person_id.
    Returns a job_id for async polling via GET /jobs/{job_id}.
    Stream progress via GET /stream/{person_id}.
    """
    if not databricks_available():
        raise HTTPException(
            status_code=503,
            detail="Databricks is required for report generation.",
        )

    job = create_job(person_id)
    get_or_create_session(person_id)

    asyncio.create_task(_run_report(job.job_id, person_id))

    return {"person_id": person_id, "job_id": job.job_id, "status": "queued"}


async def _run_report(job_id: str, person_id: str):
    job = get_job(job_id)
    job.status = "running"

    try:
        from nlp.reportagent.pipeline import generate_report
        report = await generate_report(person_id)

        job.result = report.model_dump(mode="json")
        job.status = "done"
        push_event(person_id, {"type": "done", "job_id": job_id})

    except Exception as exc:
        logger.error(
            "Report generation failed for person_id=%s: %s",
            person_id, exc, exc_info=True,
        )
        job.error = str(exc)
        job.status = "error"
        push_event(
            person_id,
            {"type": "error", "job_id": job_id, "detail": str(exc)},
        )
