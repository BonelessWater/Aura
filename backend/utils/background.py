from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Job:
    job_id: str
    patient_id: str
    status: str = "queued"  # queued | running | done | error
    result: Optional[Any] = None
    error: Optional[str] = None


_jobs: dict[str, Job] = {}


def create_job(patient_id: str) -> Job:
    job = Job(job_id=str(uuid.uuid4()), patient_id=patient_id)
    _jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)
