from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.session import get_session

router = APIRouter()


@router.get("/stream/{patient_id}")
async def stream(patient_id: str):
    """
    Server-Sent Events stream of ThoughtStream events for a patient session.
    Holds the connection open until a 'done' or 'error' event is received,
    or the client disconnects.

    Events are JSON objects, e.g.:
        {"agent": "The Extractor", "step": "bio_fingerprint", "summary": "...", "patient_id": "P001"}
        {"type": "progress", "phase": "route", "detail": "Scoring cluster alignment"}
        {"type": "done", "job_id": "..."}
    """
    session = get_session(patient_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"No session found for patient_id '{patient_id}'.")

    async def event_generator():
        cursor = 0
        while True:
            new_events = session.events[cursor:]
            for event in new_events:
                cursor += 1
                yield {"data": json.dumps(event, default=str)}
                if event.get("type") in ("done", "error"):
                    return
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())
