"""
ThoughtStream — structured event emitter for the live UI feed.

Every agent emits ThoughtStreamEvent objects at each significant step.
Events are JSON-serialisable and written to stdout (captured by the
orchestration layer) and optionally persisted to Delta.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Optional

from nlp.shared.schemas import ThoughtStreamEvent


class ThoughtStream:
    """
    Singleton-style emitter. Call ThoughtStream.emit(...) from any agent.

    Example:
        ThoughtStream.emit(
            agent="The Extractor",
            step="bio_fingerprint",
            summary="Detected sustained CRP elevation (3 readings, 14 months)."
        )
    """

    _history: list[ThoughtStreamEvent] = []

    @classmethod
    def emit(
        cls,
        agent: str,
        step: str,
        summary: str,
        patient_id: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> ThoughtStreamEvent:
        event = ThoughtStreamEvent(
            agent=agent,
            step=step,
            summary=summary,
            timestamp=datetime.utcnow(),
        )
        cls._history.append(event)

        payload: dict = event.model_dump(mode="json")
        if patient_id:
            payload["patient_id"] = patient_id
        if extra:
            payload.update(extra)

        print(json.dumps(payload, default=str), flush=True)
        return event

    @classmethod
    def history(cls) -> list[ThoughtStreamEvent]:
        return list(cls._history)

    @classmethod
    def clear(cls) -> None:
        cls._history.clear()

    @classmethod
    def to_delta(cls, spark, table: str = "aura.patients.thought_stream") -> None:
        """Persist accumulated events to a Delta table (call from Databricks)."""
        import pandas as pd
        records = [e.model_dump(mode="json") for e in cls._history]
        if not records:
            return
        df = pd.DataFrame(records)
        sdf = spark.createDataFrame(df)
        sdf.write.format("delta").mode("append").saveAsTable(table)
