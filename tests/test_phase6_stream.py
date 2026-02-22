"""
Phase 6 backend tests: GET /stream/{patient_id} SSE endpoint.

All tests use ASGITransport (no live server, no mocks).
Events are pushed directly into the session store so we can control what the
SSE generator yields without running the real pipeline.
"""

import asyncio
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.session import get_or_create_session, push_event


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _read_sse_inline(raw: str) -> list[dict]:
    """Parse all data: lines from a raw SSE response string."""
    events = []
    for line in raw.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_requires_session(client):
    """GET /stream/{unknown_id} must return 404 when no session exists."""
    resp = await client.get("/stream/no-such-patient")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_receives_pushed_events(client):
    """Events pushed into the session before connecting are yielded by the SSE stream."""
    patient_id = "sse-push-patient"
    get_or_create_session(patient_id)

    push_event(patient_id, {"type": "progress", "phase": "extract", "detail": "Starting"})
    push_event(patient_id, {"type": "done", "job_id": "test-job-123"})

    # Short timeout — all events are already in the queue so the stream terminates fast
    raw = b""
    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        assert resp.status_code == 200
        async for chunk in resp.aiter_bytes():
            raw += chunk
            if b'"done"' in raw:
                break

    events = _read_sse_inline(raw.decode())
    assert any(e.get("phase") == "extract" for e in events)
    assert any(e.get("type") == "done" for e in events)


@pytest.mark.asyncio
async def test_stream_terminates_on_done(client):
    """SSE stream must stop yielding after the 'done' event."""
    patient_id = "sse-done-patient"
    get_or_create_session(patient_id)

    push_event(patient_id, {"type": "progress", "phase": "extract"})
    push_event(patient_id, {"type": "done", "job_id": "job-xyz"})

    raw = b""
    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        async for chunk in resp.aiter_bytes():
            raw += chunk
            if b'"done"' in raw:
                break

    events = _read_sse_inline(raw.decode())
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_stream_terminates_on_error(client):
    """SSE stream must stop yielding after the 'error' event."""
    patient_id = "sse-error-patient"
    get_or_create_session(patient_id)

    push_event(patient_id, {"type": "error", "detail": "LLM timed out"})

    raw = b""
    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        async for chunk in resp.aiter_bytes():
            raw += chunk
            if b'"error"' in raw:
                break

    events = _read_sse_inline(raw.decode())
    assert any(e.get("type") == "error" for e in events)


@pytest.mark.asyncio
async def test_stream_event_format_progress(client):
    """Progress events must have 'type: progress' and a 'phase' field."""
    patient_id = "sse-format-patient"
    get_or_create_session(patient_id)

    push_event(patient_id, {"type": "progress", "phase": "route", "detail": "Scoring alignment"})
    push_event(patient_id, {"type": "done", "job_id": "j1"})

    raw = b""
    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        async for chunk in resp.aiter_bytes():
            raw += chunk
            if b'"done"' in raw:
                break

    events = _read_sse_inline(raw.decode())
    progress = next((e for e in events if e.get("type") == "progress"), None)
    assert progress is not None
    assert progress["phase"] == "route"
    assert "detail" in progress


@pytest.mark.asyncio
async def test_stream_event_format_thought(client):
    """ThoughtStream events must have an 'agent' field with 'The ' prefix."""
    patient_id = "sse-thought-patient"
    get_or_create_session(patient_id)

    push_event(patient_id, {
        "agent": "The Extractor",
        "step": "bio_fingerprint",
        "summary": "Identified haemoglobin and ferritin",
        "patient_id": patient_id,
    })
    push_event(patient_id, {"type": "done", "job_id": "j2"})

    raw = b""
    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        async for chunk in resp.aiter_bytes():
            raw += chunk
            if b'"done"' in raw:
                break

    events = _read_sse_inline(raw.decode())
    thought = next((e for e in events if "agent" in e), None)
    assert thought is not None
    assert thought["agent"].startswith("The ")


@pytest.mark.asyncio
async def test_stream_returns_event_source_content_type(client):
    """GET /stream/{patient_id} must return Content-Type: text/event-stream."""
    patient_id = "sse-ct-patient"
    get_or_create_session(patient_id)
    push_event(patient_id, {"type": "done", "job_id": "j3"})

    async with client.stream("GET", f"/stream/{patient_id}", timeout=5.0) as resp:
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct
