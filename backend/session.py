from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from nlp.shared.schemas import (
    InterviewResult,
    LabReport,
    ResearchResult,
    RouterOutput,
    TranslatorOutput,
)


@dataclass
class PatientSession:
    patient_id: str
    lab_report: Optional[LabReport] = None
    interview_result: Optional[InterviewResult] = None
    research_result: Optional[ResearchResult] = None
    router_output: Optional[RouterOutput] = None
    translator_output: Optional[TranslatorOutput] = None
    # Append-only event log; SSE endpoint polls with a local cursor.
    # list.append is GIL-safe so background threads can push without a lock.
    events: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)


_sessions: dict[str, PatientSession] = {}


def get_or_create_session(patient_id: str) -> PatientSession:
    if patient_id not in _sessions:
        _sessions[patient_id] = PatientSession(patient_id=patient_id)
    session = _sessions[patient_id]
    session.last_accessed = datetime.utcnow()
    return session


def get_session(patient_id: str) -> Optional[PatientSession]:
    return _sessions.get(patient_id)


def push_event(patient_id: str, event: dict) -> None:
    """Thread-safe append to the patient's event log."""
    session = get_session(patient_id)
    if session:
        session.events.append(event)


def evict_stale_sessions(ttl_seconds: int) -> None:
    now = datetime.utcnow()
    stale = [
        pid
        for pid, s in _sessions.items()
        if (now - s.last_accessed).total_seconds() > ttl_seconds
    ]
    for pid in stale:
        del _sessions[pid]


def active_count() -> int:
    return len(_sessions)
