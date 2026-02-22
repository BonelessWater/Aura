"""
Data Hydrator -- builds a PatientBundle from a person_id by querying Databricks.

No PDF upload needed. Pulls directly from:
  - aura.patients.lab_timeseries   -> MarkerTimeline list
  - aura.features.bio_fingerprint  -> BioFingerprint
  - core_matrix                    -> demographics (age, sex)

Usage:
    from nlp.reportagent.data_hydrator import hydrate_patient
    bundle = hydrate_patient("harvard_08670")
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Optional

from nlp.shared.schemas import (
    BioFingerprint,
    LabReport,
    MarkerFlag,
    MarkerTimeline,
    MarkerValue,
    PatientBundle,
    RatioTimepoint,
    Trend,
)

logger = logging.getLogger(__name__)

# Regex for person_id validation: alphanumeric + underscores only
_VALID_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


def hydrate_patient(person_id: str) -> PatientBundle:
    """
    Query Databricks to build a full PatientBundle for report generation.

    Tables queried:
      - aura.patients.lab_timeseries   -> MarkerTimeline list
      - aura.features.bio_fingerprint  -> BioFingerprint
      - core_matrix (aura.patients.core_matrix) -> demographics

    Raises:
        ValueError: If person_id format is invalid (SQL injection prevention).
        RuntimeError: If person_id not found in any table.
    """
    _validate_person_id(person_id)

    from nlp.shared.databricks_client import get_client
    db = get_client()

    # Step 1: Query lab_timeseries for all rows
    lab_rows = _query_lab_timeseries(db, person_id)

    # Step 2: Query Feature Store for bio_fingerprint
    fp_row = _query_bio_fingerprint(db, person_id)

    # Step 3: Build MarkerTimeline objects from lab rows
    timelines = _build_timelines(lab_rows)

    # Step 4: Build BioFingerprint from Feature Store (or compute from markers)
    bio_fp = _build_bio_fingerprint(fp_row, timelines)

    # Step 5: Build LabReport
    lab_report = LabReport(
        patient_id=person_id,
        markers=timelines,
        bio_fingerprint=bio_fp,
    )

    # Step 6: Query demographics from core_matrix (best-effort)
    demographics = _query_demographics(db, person_id)

    logger.info(
        "Hydrated patient %s: %d timelines, bio_fingerprint=%s, demographics=%s",
        person_id,
        len(timelines),
        "present" if fp_row else "computed",
        "present" if demographics else "missing",
    )

    bundle = PatientBundle(
        patient_id=person_id,
        lab_report=lab_report,
    )

    return bundle


def _validate_person_id(person_id: str) -> None:
    """Validate person_id format to prevent SQL injection."""
    if not person_id or not _VALID_ID_RE.match(person_id):
        raise ValueError(
            f"Invalid person_id format: '{person_id}'. "
            "Must be alphanumeric with underscores only."
        )


def _query_lab_timeseries(db, person_id: str) -> list[list]:
    """Query all lab rows for a patient. Raises RuntimeError if none found."""
    sql = (
        "SELECT loinc_code, display_name, date, value, unit, "
        "ref_range_low, ref_range_high, flag, z_score_nhanes "
        f"FROM aura.patients.lab_timeseries "
        f"WHERE patient_id = '{person_id}' "
        "ORDER BY display_name, date"
    )
    rows = db.run_sql(sql, desc=f"lab_timeseries for {person_id}")
    if not rows:
        raise RuntimeError(
            f"No lab data found for person_id='{person_id}' "
            "in aura.patients.lab_timeseries"
        )
    return rows


def _query_bio_fingerprint(db, person_id: str) -> Optional[dict]:
    """Query Feature Store for bio_fingerprint. Returns None if not found."""
    sql = (
        "SELECT NLR, PLR, MLR, SII, CRP_Albumin, C3_C4, "
        "NLR_flag, ANA_titer_trend, sustained_abnormalities, "
        "morphological_shifts, patient_age, patient_sex "
        f"FROM aura.features.bio_fingerprint "
        f"WHERE patient_id = '{person_id}' "
        "LIMIT 1"
    )
    try:
        rows = db.run_sql(sql, desc=f"bio_fingerprint for {person_id}")
    except Exception as e:
        logger.warning(
            "Failed to query bio_fingerprint for %s: %s", person_id, e
        )
        return None

    if not rows:
        return None

    cols = [
        "NLR", "PLR", "MLR", "SII", "CRP_Albumin", "C3_C4",
        "NLR_flag", "ANA_titer_trend", "sustained_abnormalities",
        "morphological_shifts", "patient_age", "patient_sex",
    ]
    return dict(zip(cols, rows[0]))


def _query_demographics(db, person_id: str) -> Optional[dict]:
    """Query core_matrix for demographics. Returns None if not found."""
    sql = (
        "SELECT patient_age, patient_sex, diagnosis_cluster "
        f"FROM aura.patients.core_matrix "
        f"WHERE patient_id = '{person_id}' "
        "LIMIT 1"
    )
    try:
        rows = db.run_sql(sql, desc=f"core_matrix for {person_id}")
    except Exception as e:
        logger.warning(
            "Failed to query core_matrix for %s: %s", person_id, e
        )
        return None

    if not rows:
        return None

    cols = ["patient_age", "patient_sex", "diagnosis_cluster"]
    return dict(zip(cols, rows[0]))


def _build_timelines(lab_rows: list[list]) -> list[MarkerTimeline]:
    """Group lab rows by display_name into MarkerTimeline objects."""
    grouped: dict[str, list[MarkerValue]] = defaultdict(list)

    for row in lab_rows:
        # Columns: loinc_code, display_name, date, value, unit,
        #          ref_range_low, ref_range_high, flag, z_score_nhanes
        (
            loinc_code, display_name, date_str, value, unit,
            ref_low, ref_high, flag_str, z_score,
        ) = (row + [None] * 9)[:9]

        flag_enum = MarkerFlag.NORMAL
        if flag_str == "HIGH":
            flag_enum = MarkerFlag.HIGH
        elif flag_str == "LOW":
            flag_enum = MarkerFlag.LOW

        mv = MarkerValue(
            loinc_code=loinc_code,
            display_name=display_name or "",
            date=date_str or "",
            value=float(value) if value is not None else 0.0,
            unit=unit or "",
            ref_range_low=float(ref_low) if ref_low is not None else None,
            ref_range_high=float(ref_high) if ref_high is not None else None,
            flag=flag_enum,
            z_score_nhanes=float(z_score) if z_score is not None else None,
        )
        grouped[display_name or ""].append(mv)

    timelines: list[MarkerTimeline] = []
    for display_name, values in grouped.items():
        values_sorted = sorted(values, key=lambda v: v.date)
        trend = _compute_trend(values_sorted)
        loinc = values_sorted[0].loinc_code if values_sorted else None
        timelines.append(MarkerTimeline(
            loinc_code=loinc,
            display_name=display_name,
            values=values_sorted,
            trend=trend,
        ))

    return timelines


def _compute_trend(values: list[MarkerValue]) -> Optional[Trend]:
    """Compute trend from a sorted list of MarkerValue objects."""
    if len(values) < 2:
        return None
    first, last = values[0].value, values[-1].value
    if first == 0:
        return None
    pct = (last - first) / first
    if pct > 0.15:
        return Trend.ESCALATING
    if pct < -0.15:
        return Trend.RESOLVING
    return Trend.STABLE


def _build_bio_fingerprint(
    fp_row: Optional[dict],
    timelines: list[MarkerTimeline],
) -> BioFingerprint:
    """
    Build BioFingerprint from Feature Store row.
    Falls back to computing from raw markers if Feature Store entry is missing.
    """
    if fp_row:
        return _bio_fingerprint_from_feature_store(fp_row)

    # Fallback: compute from raw marker timelines
    logger.info("No Feature Store entry found, computing bio_fingerprint from markers")
    from nlp.extractor.bio_fingerprint import compute_bio_fingerprint
    return compute_bio_fingerprint(timelines)


def _bio_fingerprint_from_feature_store(fp_row: dict) -> BioFingerprint:
    """Reconstruct BioFingerprint from a Feature Store row."""
    fp = BioFingerprint()

    # Rebuild ratio timepoints from latest values stored in Feature Store
    # Feature Store only stores the latest value, so we create a single timepoint
    for ratio_name in ["NLR", "PLR", "MLR", "SII", "CRP_Albumin", "C3_C4"]:
        val = fp_row.get(ratio_name)
        if val is not None:
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue
            flag = fp_row.get(f"{ratio_name}_flag")
            getattr(fp, ratio_name).append(
                RatioTimepoint(date="latest", value=val, flag=flag)
            )

    # ANA titer trend
    ana_trend = fp_row.get("ANA_titer_trend")
    if ana_trend:
        try:
            fp.ANA_titer_trend = Trend(ana_trend)
        except ValueError:
            pass

    # Sustained abnormalities and morphological shifts (stored as CSV)
    sustained = fp_row.get("sustained_abnormalities", "")
    if sustained:
        fp.sustained_abnormalities = [
            s.strip() for s in sustained.split(",") if s.strip()
        ]

    shifts = fp_row.get("morphological_shifts", "")
    if shifts:
        fp.morphological_shifts = [
            s.strip() for s in shifts.split(",") if s.strip()
        ]

    return fp
