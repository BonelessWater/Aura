"""
Bio-Fingerprint — The Extractor, Step 4.

Computes the "invisible relationships" — derived ratios that Aura uses
as its core differentiating signal. Operates on a list of MarkerTimeline
objects and returns a populated BioFingerprint.

Ratios computed:
  NLR  = Neutrophils / Lymphocytes          (flag if > 3.0)
  PLR  = Platelets / Lymphocytes             (flag if > 150)
  MLR  = Monocytes / Lymphocytes             (flag if > 0.3)
  SII  = Platelets × Neutrophils / Lymphocytes
  CRP_Albumin = CRP / Albumin                (flag if > 0.8)
  C3_C4       = C3 / C4                      (low in SLE — flag if < 2.0)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, date
from typing import Optional

from nlp.shared.schemas import (
    BioFingerprint,
    MarkerTimeline,
    MarkerValue,
    RatioTimepoint,
    Trend,
    MarkerFlag,
)

logger = logging.getLogger(__name__)

# Thresholds for ratio flags
THRESHOLDS = {
    "NLR":        ("ELEVATED", 3.0,   None),   # > 3 → ELEVATED
    "PLR":        ("ELEVATED", 150.0, None),
    "MLR":        ("ELEVATED", 0.3,   None),
    "CRP_Albumin":("ELEVATED", 0.8,   None),
    "C3_C4":      ("LOW",      None,  2.0),    # < 2 → LOW (SLE pattern)
}

# Minimum gap (months) to call "sustained abnormality"
SUSTAINED_MIN_MONTHS = 6
SUSTAINED_MIN_READINGS = 2


def compute_bio_fingerprint(
    timelines: list[MarkerTimeline],
    patient_age: int = 40,
    patient_sex: str = "F",
) -> BioFingerprint:
    """
    Given a list of MarkerTimeline objects (one per marker, multi-timepoint),
    compute all bio-fingerprint ratios and flags.
    """
    # Index timelines by display_name for quick lookup
    idx: dict[str, MarkerTimeline] = {t.display_name: t for t in timelines}

    fp = BioFingerprint()

    # ── Per-timepoint ratio computation ───────────────────────────────────────
    # Align dates across numerator and denominator markers
    _compute_ratio(fp.NLR,         idx, "Neutrophils", "Lymphocytes",  "NLR")
    _compute_ratio(fp.PLR,         idx, "Platelets",   "Lymphocytes",  "PLR")
    _compute_ratio(fp.MLR,         idx, "Monocytes",   "Lymphocytes",  "MLR")
    _compute_sii(fp.SII,           idx)
    _compute_ratio(fp.CRP_Albumin, idx, "CRP",         "Albumin",      "CRP_Albumin")
    _compute_ratio(fp.C3_C4,       idx, "C3",          "C4",           "C3_C4")

    # ── ANA titer trend ────────────────────────────────────────────────────────
    fp.ANA_titer_trend = _extract_trend(idx.get("ANA"))

    # ── Sustained abnormality flags ────────────────────────────────────────────
    for timeline in timelines:
        if _is_sustained_abnormal(timeline):
            fp.sustained_abnormalities.append(timeline.display_name)

    # ── Morphological shift flags ──────────────────────────────────────────────
    for timeline in timelines:
        if _has_morphological_shift(timeline):
            fp.morphological_shifts.append(timeline.display_name)

    return fp


def _get_values_by_date(
    idx: dict[str, MarkerTimeline],
    name: str,
) -> dict[str, float]:
    """Return {date_str: value} for a named marker."""
    tl = idx.get(name)
    if not tl:
        return {}
    return {v.date: v.value for v in tl.values}


def _compute_ratio(
    target: list[RatioTimepoint],
    idx: dict[str, MarkerTimeline],
    num_name: str,
    den_name: str,
    ratio_key: str,
) -> None:
    num_vals = _get_values_by_date(idx, num_name)
    den_vals = _get_values_by_date(idx, den_name)

    # Intersect on date
    common_dates = set(num_vals) & set(den_vals)
    if not common_dates and num_vals and den_vals:
        # If no exact date match, use the closest date pair
        common_dates = {_closest_date(num_vals, den_vals)}

    thresh_label, thresh_high, thresh_low = THRESHOLDS.get(ratio_key, (None, None, None))

    for d in sorted(common_dates):
        num = num_vals.get(d, 0)
        den = den_vals.get(d)
        if not den or den == 0:
            continue
        ratio = round(num / den, 3)
        flag = None
        if thresh_high is not None and ratio > thresh_high:
            flag = thresh_label
        if thresh_low is not None and ratio < thresh_low:
            flag = thresh_label
        target.append(RatioTimepoint(date=d, value=ratio, flag=flag))


def _compute_sii(
    target: list[RatioTimepoint],
    idx: dict[str, MarkerTimeline],
) -> None:
    """SII = Platelets × Neutrophils / Lymphocytes"""
    plt_vals  = _get_values_by_date(idx, "Platelets")
    neut_vals = _get_values_by_date(idx, "Neutrophils")
    lymp_vals = _get_values_by_date(idx, "Lymphocytes")

    common = set(plt_vals) & set(neut_vals) & set(lymp_vals)
    for d in sorted(common):
        lymp = lymp_vals.get(d, 0)
        if lymp == 0:
            continue
        sii = round((plt_vals[d] * neut_vals[d]) / lymp, 1)
        target.append(RatioTimepoint(date=d, value=sii))


def _extract_trend(timeline: Optional[MarkerTimeline]) -> Optional[Trend]:
    if not timeline or len(timeline.values) < 2:
        return None
    vals = sorted(timeline.values, key=lambda v: v.date)
    first, last = vals[0].value, vals[-1].value
    pct_change = (last - first) / first if first != 0 else 0
    if pct_change > 0.15:
        return Trend.ESCALATING
    if pct_change < -0.15:
        return Trend.RESOLVING
    return Trend.STABLE


def _is_sustained_abnormal(timeline: MarkerTimeline) -> bool:
    """True if ≥ SUSTAINED_MIN_READINGS readings are abnormal over ≥ SUSTAINED_MIN_MONTHS."""
    abnormal = [v for v in timeline.values if v.flag != MarkerFlag.NORMAL]
    if len(abnormal) < SUSTAINED_MIN_READINGS:
        return False
    dates = sorted(v.date for v in abnormal)
    try:
        d0 = datetime.strptime(dates[0],  "%Y-%m-%d")
        d1 = datetime.strptime(dates[-1], "%Y-%m-%d")
        months_span = (d1 - d0).days / 30.0
        return months_span >= SUSTAINED_MIN_MONTHS
    except ValueError:
        return False


def _has_morphological_shift(timeline: MarkerTimeline) -> bool:
    """True if marker crosses normal↔abnormal boundary at least once."""
    if len(timeline.values) < 2:
        return False
    vals = sorted(timeline.values, key=lambda v: v.date)
    prev_abnormal = vals[0].flag != MarkerFlag.NORMAL
    for v in vals[1:]:
        curr_abnormal = v.flag != MarkerFlag.NORMAL
        if curr_abnormal != prev_abnormal:
            return True
        prev_abnormal = curr_abnormal
    return False


def _closest_date(a: dict[str, float], b: dict[str, float]) -> str:
    """Return the date key from `a` whose string is closest to any key in `b`."""
    # Simple lexicographic proximity as a fallback
    a_dates = sorted(a.keys())
    b_dates = sorted(b.keys())
    if a_dates and b_dates:
        return a_dates[-1]  # Most recent
    return list(a.keys())[0]
