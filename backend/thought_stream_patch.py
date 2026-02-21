"""
Monkey-patch ThoughtStream.emit so events are also pushed to the patient's
in-memory event log (used by the SSE /stream/{patient_id} endpoint).

Call apply_patch() once at application startup, before any routers import
the NLP modules.
"""

from __future__ import annotations

from nlp.shared.thought_stream import ThoughtStream

from .session import push_event


def apply_patch() -> None:
    _orig = ThoughtStream.emit  # bound classmethod before patching

    @classmethod  # type: ignore[misc]
    def patched(
        cls,
        agent: str,
        step: str,
        summary: str,
        patient_id: str | None = None,
        extra: dict | None = None,
    ):
        event = _orig(
            agent=agent,
            step=step,
            summary=summary,
            patient_id=patient_id,
            extra=extra,
        )
        if patient_id:
            payload = event.model_dump(mode="json")
            payload["patient_id"] = patient_id
            if extra:
                payload.update(extra)
            push_event(patient_id, payload)
        return event

    ThoughtStream.emit = patched
