"""
Demo Router -- serves autoimmune patient cases from Databricks for the
live inference demo page.

Caches cases in memory after first fetch to avoid repeated Databricks queries.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo")

# Autoimmune disease patterns for SQL LIKE matching
AUTOIMMUNE_PATTERNS = [
    "%lupus%",
    "%rheumatoid arthritis%",
    "%sarcoidosis%",
    "%multiple sclerosis%",
    "%dermatomyositis%",
    "%myasthenia gravis%",
    "%sjogren%",
    "%hashimoto%",
    "%graves disease%",
    "%psoriatic%",
    "%ankylosing%",
    "%scleroderma%",
    "%systemic sclerosis%",
    "%vasculitis%",
    "%polymyositis%",
]

TABLE = "workspace.aura.pmc_patients_classified"

_cached_cases: list[dict] | None = None


class DemoCase(BaseModel):
    case_id: str
    clinical_text: str
    age: Optional[int] = None
    sex: Optional[str] = None
    ground_truth: str


class DemoCasesResponse(BaseModel):
    cases: list[DemoCase]
    total: int


def _fetch_cases() -> list[dict]:
    """Fetch autoimmune cases from Databricks (called once, then cached)."""
    from nlp.shared.databricks_client import get_client

    db = get_client()
    like_clauses = " OR ".join(
        f"LOWER(diagnosis) LIKE '{p}'" for p in AUTOIMMUNE_PATTERNS
    )
    sql = f"""
        SELECT patient_id, preliminary_text, diagnosis, age_years, sex
        FROM {TABLE}
        WHERE ({like_clauses})
          AND preliminary_text IS NOT NULL
          AND LENGTH(preliminary_text) > 100
        LIMIT 300
    """
    rows = db.run_sql(sql, desc="fetch autoimmune demo cases")

    cases = []
    for row in rows:
        cases.append({
            "case_id": str(row[0]),
            "clinical_text": str(row[1]),
            "ground_truth": str(row[2]).strip().lower(),
            "age": int(row[3]) if row[3] else None,
            "sex": str(row[4]) if row[4] else None,
        })

    logger.info("Fetched %d autoimmune demo cases from Databricks", len(cases))
    return cases


@router.get("/cases", response_model=DemoCasesResponse)
async def get_demo_cases(limit: int = 20, seed: int = 42):
    """Return a random selection of autoimmune patient cases for the demo."""
    global _cached_cases

    if _cached_cases is None:
        try:
            _cached_cases = _fetch_cases()
        except Exception as e:
            logger.error("Failed to fetch demo cases: %s", e)
            raise HTTPException(
                status_code=503, detail=f"Databricks unavailable: {e}"
            )

    if not _cached_cases:
        raise HTTPException(status_code=404, detail="No autoimmune cases found")

    rng = random.Random(seed)
    selected = rng.sample(_cached_cases, min(limit, len(_cached_cases)))

    return DemoCasesResponse(
        cases=[DemoCase(**c) for c in selected],
        total=len(_cached_cases),
    )


@router.delete("/cache")
async def clear_cache():
    """Clear the cached cases (forces re-fetch from Databricks)."""
    global _cached_cases
    _cached_cases = None
    return {"status": "cache_cleared"}
