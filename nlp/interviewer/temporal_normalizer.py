"""
Temporal Normalizer — The Interviewer, Step 4.

Parses duration and date expressions from patient narratives
and normalises them to ISO 8601 dates and integer month durations.

Examples:
  "for 3 months"   → duration_months=3
  "since 2022"     → duration_months=(months from 2022-01 to now)
  "since January"  → duration_months=(months from Jan of current year to now)
  "last 6 weeks"   → duration_months=1 (approx)
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


_WORD_TO_NUM: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "several": 3, "few": 3, "many": 6,
}

_UNIT_TO_MONTHS: dict[str, float] = {
    "day": 1/30, "days": 1/30,
    "week": 0.25, "weeks": 0.25,
    "month": 1.0, "months": 1.0,
    "year": 12.0, "years": 12.0,
}

_MONTH_NAMES: dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2,
    "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6,
    "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def normalize_duration(text: str) -> Optional[int]:
    """
    Extract a duration from text and return the number of months.
    Returns None if no duration is found.
    """
    text_lower = text.lower().strip()
    now = datetime.utcnow()

    # "for N (unit)" pattern
    m = re.search(
        r"for\s+(\d+|" + "|".join(_WORD_TO_NUM) + r")\s+"
        r"(days?|weeks?|months?|years?)",
        text_lower,
    )
    if m:
        qty  = _parse_quantity(m.group(1))
        unit = m.group(2)
        return max(1, round(qty * _UNIT_TO_MONTHS[unit]))

    # "past/last N (unit)" pattern
    m = re.search(
        r"(?:past|last|over(?: the)?(?: past| last)?)\s+"
        r"(\d+|" + "|".join(_WORD_TO_NUM) + r")\s+"
        r"(days?|weeks?|months?|years?)",
        text_lower,
    )
    if m:
        qty  = _parse_quantity(m.group(1))
        unit = m.group(2)
        return max(1, round(qty * _UNIT_TO_MONTHS[unit]))

    # "since YYYY" pattern
    m = re.search(r"since\s+(\d{4})", text_lower)
    if m:
        year = int(m.group(1))
        delta_months = (now.year - year) * 12 + now.month
        return max(1, delta_months)

    # "since [Month]" or "since [Month YYYY]"
    month_pattern = "|".join(_MONTH_NAMES.keys())
    m = re.search(rf"since\s+({month_pattern})\s*(\d{{4}})?", text_lower)
    if m:
        month_num = _MONTH_NAMES[m.group(1)]
        year      = int(m.group(2)) if m.group(2) else now.year
        start     = datetime(year, month_num, 1)
        delta     = now - start
        return max(1, round(delta.days / 30))

    return None


def normalize_date(text: str) -> Optional[str]:
    """
    Parse a date expression and return ISO 8601 string (YYYY-MM or YYYY-MM-DD).
    Returns None if no date found.
    """
    try:
        import dateparser
        result = dateparser.parse(
            text,
            settings={
                "PREFER_DAY_OF_MONTH": "first",
                "RETURN_AS_TIMEZONE_AWARE": False,
                "DATE_ORDER": "YMD",
            },
        )
        if result:
            return result.strftime("%Y-%m-%d")
    except ImportError:
        pass

    # Fallback: simple year extraction
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return f"{m.group(1)}-01-01"

    return None


def _parse_quantity(s: str) -> float:
    if s.isdigit():
        return float(s)
    return float(_WORD_TO_NUM.get(s, 1))
