"""
Extractor Pipeline — The Extractor (Phase 1 orchestrator).

Given one or more lab PDF paths for a patient, runs the full
extraction pipeline and writes results to:
  - aura.patients.lab_timeseries  (Delta table)
  - aura.features.bio_fingerprint (Databricks Feature Store)

Usage:
    from nlp.extractor.pipeline import run_extractor
    lab_report = run_extractor(
        patient_id="P001",
        pdf_paths=["/path/to/labwork_2024.pdf"],
        patient_age=45,
        patient_sex="F",
    )
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from nlp.shared.schemas import (
    BioFingerprint,
    LabReport,
    MarkerFlag,
    MarkerTimeline,
    MarkerValue,
    ThoughtStreamEvent,
    Trend,
)
from nlp.shared.thought_stream import ThoughtStream
from nlp.extractor.pdf_parser import (
    parse_pdf,
    stitch_pages,
    extract_all_tables,
    has_handwriting_hint,
)
from nlp.extractor.biomarker_extractor import (
    extract_markers,
    extract_from_tables,
    RawMarker,
)
from nlp.extractor.loinc_mapper import get_mapper
from nlp.extractor.nhanes_normalizer import get_normalizer
from nlp.extractor.bio_fingerprint import compute_bio_fingerprint

logger = logging.getLogger(__name__)


def run_extractor(
    patient_id: str,
    pdf_paths: list[str | Path],
    patient_age: int = 40,
    patient_sex: str = "F",   # "M" or "F"
    write_to_databricks: bool = True,
) -> LabReport:
    """
    Full extraction pipeline. Returns a LabReport.

    Steps:
      1. Parse each PDF
      2. Extract raw markers (table-first, text fallback)
      3. Map to LOINC codes
      4. Compute NHANES z-scores
      5. Compute bio-fingerprint ratios + flags
      6. (Optional) Write to Delta + Feature Store
    """
    ThoughtStream.emit(
        agent="The Extractor",
        step="start",
        summary=f"Starting extraction for patient {patient_id} — {len(pdf_paths)} PDF(s)",
        patient_id=patient_id,
    )

    # ── Step 1-2: Parse all PDFs, collect raw markers per date ────────────────
    all_raw: list[RawMarker] = []
    loinc_mapper   = get_mapper()
    nhanes_norm    = get_normalizer()

    for pdf_path in pdf_paths:
        pdf_path = Path(pdf_path)
        try:
            pages = parse_pdf(pdf_path)
        except Exception as e:
            logger.error(f"Failed to parse {pdf_path}: {e}")
            continue

        if has_handwriting_hint(pages):
            ThoughtStream.emit(
                agent="The Extractor",
                step="handwriting_flag",
                summary=f"Possible handwriting in {pdf_path.name} — flagged for manual review",
                patient_id=patient_id,
            )

        # Table extraction (preferred — more structured)
        tables = extract_all_tables(pages)
        text   = stitch_pages(pages)
        raw    = extract_from_tables(tables) if tables else []
        if not raw:
            raw = extract_markers(text)

        all_raw.extend(raw)
        logger.info(f"  {pdf_path.name}: extracted {len(raw)} markers")

    # ── Step 3-4: Group by marker, map LOINC, compute z-scores ───────────────
    # Aggregate multiple PDFs: group by (display_name, date)
    from collections import defaultdict
    grouped: dict[str, list[MarkerValue]] = defaultdict(list)

    for rm in all_raw:
        loinc_code, mapped_name = loinc_mapper.lookup(rm.display_name)
        display = mapped_name or rm.display_name

        z = nhanes_norm.compute_zscore(
            display, rm.value, patient_age, patient_sex
        )

        flag_enum = MarkerFlag.NORMAL
        if rm.flag == "H":
            flag_enum = MarkerFlag.HIGH
        elif rm.flag == "L":
            flag_enum = MarkerFlag.LOW

        mv = MarkerValue(
            loinc_code     = loinc_code,
            display_name   = display,
            date           = rm.date_str or datetime.utcnow().strftime("%Y-%m-%d"),
            value          = rm.value,
            unit           = rm.unit,
            ref_range_low  = rm.ref_low,
            ref_range_high = rm.ref_high,
            flag           = flag_enum,
            z_score_nhanes = z,
        )
        grouped[display].append(mv)

    # ── Build MarkerTimeline objects ──────────────────────────────────────────
    timelines: list[MarkerTimeline] = []
    for display_name, values in grouped.items():
        values_sorted = sorted(values, key=lambda v: v.date)
        trend = _compute_trend(values_sorted)
        loinc = values_sorted[0].loinc_code if values_sorted else None
        timelines.append(MarkerTimeline(
            loinc_code   = loinc,
            display_name = display_name,
            values       = values_sorted,
            trend        = trend,
        ))

    ThoughtStream.emit(
        agent="The Extractor",
        step="markers_extracted",
        summary=f"Extracted {len(timelines)} distinct markers across {len(pdf_paths)} PDF(s)",
        patient_id=patient_id,
    )

    # ── Step 5: Bio-fingerprint ───────────────────────────────────────────────
    bio_fp = compute_bio_fingerprint(timelines, patient_age, patient_sex)

    sustained = bio_fp.sustained_abnormalities
    shifts    = bio_fp.morphological_shifts
    nlr_vals  = [r.value for r in bio_fp.NLR]
    nlr_str   = f"NLR values: {[round(v, 2) for v in nlr_vals]}" if nlr_vals else "NLR: insufficient data"

    ThoughtStream.emit(
        agent="The Extractor",
        step="bio_fingerprint",
        summary=(
            f"{nlr_str}. "
            f"Sustained abnormalities: {sustained or 'none'}. "
            f"Morphological shifts: {shifts or 'none'}."
        ),
        patient_id=patient_id,
    )

    # ── Assemble LabReport ────────────────────────────────────────────────────
    report = LabReport(
        patient_id   = patient_id,
        markers      = timelines,
        bio_fingerprint = bio_fp,
    )

    # ── Step 6: Write to Databricks (optional) ────────────────────────────────
    if write_to_databricks:
        try:
            _write_to_delta(report)
            _write_to_feature_store(report, patient_age, patient_sex)
        except Exception as e:
            logger.error(f"Databricks write failed: {e}")

    return report


def _compute_trend(values: list[MarkerValue]) -> Optional[Trend]:
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


def _write_to_delta(report: LabReport) -> None:
    """Append marker values to aura.patients.lab_timeseries."""
    from nlp.shared.databricks_client import get_client
    import io, pandas as pd

    client = get_client()

    # Ensure schema + table exist
    client.run_sql("CREATE SCHEMA IF NOT EXISTS aura.patients")
    client.run_sql("""
        CREATE TABLE IF NOT EXISTS aura.patients.lab_timeseries (
            patient_id     STRING,
            loinc_code     STRING,
            display_name   STRING,
            date           STRING,
            value          DOUBLE,
            unit           STRING,
            ref_range_low  DOUBLE,
            ref_range_high DOUBLE,
            flag           STRING,
            z_score_nhanes DOUBLE
        ) USING DELTA
    """)

    rows = []
    for timeline in report.markers:
        for mv in timeline.values:
            rows.append({
                "patient_id":     report.patient_id,
                "loinc_code":     mv.loinc_code,
                "display_name":   mv.display_name,
                "date":           mv.date,
                "value":          mv.value,
                "unit":           mv.unit,
                "ref_range_low":  mv.ref_range_low,
                "ref_range_high": mv.ref_range_high,
                "flag":           mv.flag.value,
                "z_score_nhanes": mv.z_score_nhanes,
            })

    if not rows:
        return

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    vol_path = f"/Volumes/aura/patients/raw/{report.patient_id}_labs.parquet"
    client.run_sql("CREATE SCHEMA IF NOT EXISTS aura.patients")
    client.run_sql("CREATE VOLUME IF NOT EXISTS aura.patients.raw")
    client.upload_bytes(buf, vol_path)
    client.run_sql(
        f"INSERT INTO aura.patients.lab_timeseries "
        f"SELECT * FROM parquet.`{vol_path}`"
    )
    logger.info(f"Wrote {len(rows)} lab rows to aura.patients.lab_timeseries")


def _write_to_feature_store(
    report: LabReport,
    age: int,
    sex: str,
) -> None:
    """Write bio-fingerprint features to aura.features.bio_fingerprint."""
    from nlp.shared.databricks_client import get_client
    import pandas as pd

    client = get_client()
    client.run_sql("CREATE SCHEMA IF NOT EXISTS aura.features")

    fp = report.bio_fingerprint

    def latest(ratios) -> Optional[float]:
        return ratios[-1].value if ratios else None

    def latest_flag(ratios) -> Optional[str]:
        if not ratios:
            return None
        return ratios[-1].flag

    row = {
        "patient_id":             report.patient_id,
        "NLR":                    latest(fp.NLR),
        "PLR":                    latest(fp.PLR),
        "MLR":                    latest(fp.MLR),
        "SII":                    latest(fp.SII),
        "CRP_Albumin":            latest(fp.CRP_Albumin),
        "C3_C4":                  latest(fp.C3_C4),
        "NLR_flag":               latest_flag(fp.NLR),
        "ANA_titer_trend":        fp.ANA_titer_trend.value if fp.ANA_titer_trend else None,
        "sustained_abnormalities": ",".join(fp.sustained_abnormalities),
        "morphological_shifts":    ",".join(fp.morphological_shifts),
        "patient_age":            age,
        "patient_sex":            sex,
        "updated_at":             datetime.utcnow().isoformat(),
    }

    df = pd.DataFrame([row])
    import io
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)

    vol_path = f"/Volumes/aura/features/raw/{report.patient_id}_features.parquet"
    client.run_sql("CREATE VOLUME IF NOT EXISTS aura.features.raw")
    client.upload_bytes(buf, vol_path)

    # Merge into feature table (upsert on patient_id)
    client.run_sql("""
        CREATE TABLE IF NOT EXISTS aura.features.bio_fingerprint (
            patient_id             STRING,
            NLR                    DOUBLE,
            PLR                    DOUBLE,
            MLR                    DOUBLE,
            SII                    DOUBLE,
            CRP_Albumin            DOUBLE,
            C3_C4                  DOUBLE,
            NLR_flag               STRING,
            ANA_titer_trend        STRING,
            sustained_abnormalities STRING,
            morphological_shifts   STRING,
            patient_age            INT,
            patient_sex            STRING,
            updated_at             STRING
        ) USING DELTA
    """)
    client.run_sql(f"""
        MERGE INTO aura.features.bio_fingerprint AS target
        USING parquet.`{vol_path}` AS source
        ON target.patient_id = source.patient_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    logger.info(f"Upserted bio-fingerprint features for {report.patient_id}")
