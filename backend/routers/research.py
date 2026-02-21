from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import databricks_available
from backend.session import get_or_create_session, push_event
from backend.utils.background import create_job, get_job

router = APIRouter()


class ResearchRequest(BaseModel):
    patient_id: str
    cluster_hint: Optional[str] = None


@router.post("/research")
async def research(body: ResearchRequest):
    """
    Run RAG retrieval against the PubMed vector store.
    Requires a live Databricks Vector Search index; returns 503 if unavailable.
    Returns a job_id immediately; poll GET /jobs/{job_id} for the result.
    """
    if not databricks_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Databricks Vector Search is not configured. "
                "Set the DATABRICKS_HOST environment variable."
            ),
        )

    session = get_or_create_session(body.patient_id)
    job = create_job(body.patient_id)

    asyncio.create_task(
        _run_research(
            job.job_id,
            body.patient_id,
            body.cluster_hint,
        )
    )

    return {"patient_id": body.patient_id, "job_id": job.job_id, "status": "queued"}


async def _run_research(job_id: str, patient_id: str, cluster_hint: Optional[str]):
    from backend.utils.background import get_job
    from nlp.researcher.pipeline import run_researcher

    job = get_job(job_id)
    job.status = "running"

    session = get_or_create_session(patient_id)

    try:
        research_result = await asyncio.to_thread(
            run_researcher,
            patient_id,
            session.lab_report,
            session.interview_result,
            cluster_hint,
        )
        session.research_result = research_result
        job.result = research_result.model_dump(mode="json")
        job.status = "done"
        push_event(patient_id, {"type": "done", "phase": "research", "job_id": job_id})
    except Exception as exc:
        job.error = str(exc)
        job.status = "error"
        push_event(
            patient_id,
            {"type": "error", "phase": "research", "job_id": job_id, "detail": str(exc)},
        )
