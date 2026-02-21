"""
Biomarker Extractor — The Extractor, Step 2.

Extracts structured lab values from raw PDF text using regex patterns.
Covers 40+ markers across Inflammatory, CBC, Metabolic, and GI groups.
Normalises units to SI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class RawMarker:
    display_name: str
    value:        float
    unit:         str
    ref_low:      Optional[float]
    ref_high:     Optional[float]
    flag:         str   # "H", "L", or ""
    date_str:     Optional[str]


# ── Synonym → canonical name mapping ─────────────────────────────────────────

MARKER_SYNONYMS: dict[str, str] = {
    # Inflammatory
    "esr": "ESR", "erythrocyte sedimentation rate": "ESR", "sed rate": "ESR",
    "crp": "CRP", "c-reactive protein": "CRP", "c reactive protein": "CRP",
    "hscrp": "hs-CRP", "high sensitivity crp": "hs-CRP", "hs-crp": "hs-CRP",
    "c3": "C3", "complement c3": "C3",
    "c4": "C4", "complement c4": "C4",
    "rf": "RF", "rheumatoid factor": "RF",
    "anti-ccp": "Anti-CCP", "anti ccp": "Anti-CCP", "ccp": "Anti-CCP",
    "ana": "ANA", "antinuclear antibody": "ANA", "antinuclear ab": "ANA",
    "anti-dsdna": "anti-dsDNA", "anti dsdna": "anti-dsDNA", "ds-dna": "anti-dsDNA",
    "hla-b27": "HLA-B27", "hla b27": "HLA-B27",
    "anti-sm": "anti-SM", "anti sm": "anti-SM",
    "anti-ro": "anti-Ro", "anti ro": "anti-Ro", "ssa": "anti-Ro", "anti-ssa": "anti-Ro",
    "anti-la": "anti-La", "anti la": "anti-La", "ssb": "anti-La", "anti-ssb": "anti-La",
    # CBC
    "wbc": "WBC", "white blood cell": "WBC", "white blood cells": "WBC", "white cell count": "WBC",
    "neutrophils": "Neutrophils", "neut": "Neutrophils", "neutrophil %": "Neutrophils%",
    "lymphocytes": "Lymphocytes", "lymphs": "Lymphocytes", "lymphocyte %": "Lymphocytes%",
    "monocytes": "Monocytes", "mono": "Monocytes", "monocyte %": "Monocytes%",
    "eosinophils": "Eosinophils", "eos": "Eosinophils",
    "basophils": "Basophils", "baso": "Basophils",
    "rdw": "RDW", "red cell distribution width": "RDW",
    "mpv": "MPV", "mean platelet volume": "MPV",
    "hemoglobin": "Hemoglobin", "hgb": "Hemoglobin", "hb": "Hemoglobin",
    "hematocrit": "Hematocrit", "hct": "Hematocrit",
    "mcv": "MCV", "mean corpuscular volume": "MCV",
    "mch": "MCH",
    "rbc": "RBC", "red blood cell": "RBC", "red blood cells": "RBC",
    "platelets": "Platelets", "plt": "Platelets", "platelet count": "Platelets",
    # Metabolic / CMP
    "bun": "BUN", "blood urea nitrogen": "BUN",
    "creatinine": "Creatinine", "creat": "Creatinine",
    "egfr": "eGFR", "estimated gfr": "eGFR",
    "alt": "ALT", "alanine aminotransferase": "ALT", "sgpt": "ALT",
    "ast": "AST", "aspartate aminotransferase": "AST", "sgot": "AST",
    "alp": "ALP", "alkaline phosphatase": "ALP",
    "bilirubin": "Bilirubin", "total bilirubin": "Bilirubin", "tbili": "Bilirubin",
    "albumin": "Albumin", "alb": "Albumin",
    "glucose": "Glucose", "glu": "Glucose", "fasting glucose": "Glucose",
    "sodium": "Sodium", "na": "Sodium",
    "potassium": "Potassium", "k": "Potassium",
    "co2": "CO2", "bicarbonate": "CO2",
    "magnesium": "Magnesium", "mg": "Magnesium",
    "calcium": "Calcium", "ca": "Calcium",
    "phosphorus": "Phosphorus", "phos": "Phosphorus",
    # GI
    "fecal calprotectin": "Fecal Calprotectin", "calprotectin": "Fecal Calprotectin",
    "bmi": "BMI", "body mass index": "BMI",
}

# ── SI unit conversion factors ────────────────────────────────────────────────
# (source_unit_lower, canonical_unit): multiplier to get canonical
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    # CRP / general proteins: mg/dL → mg/L
    ("mg/dl", "mg/L"): 10.0,
    # Creatinine: mg/dL → µmol/L
    ("mg/dl_creat", "µmol/L"): 88.4,
    # Glucose: mg/dL → mmol/L
    ("mg/dl_glucose", "mmol/L"): 0.0555,
    # Calcium: mg/dL → mmol/L
    ("mg/dl_calcium", "mmol/L"): 0.2495,
    # BUN: mg/dL → mmol/L
    ("mg/dl_bun", "mmol/L"): 0.357,
    # Cholesterol / Bilirubin: mg/dL → µmol/L
    ("mg/dl_bili", "µmol/L"): 17.1,
    # Albumin: g/dL → g/L
    ("g/dl", "g/L"): 10.0,
}

# ── Reference ranges (approximate; LOINC/NHANES used at inference time) ──────
REFERENCE_RANGES: dict[str, tuple[float, float]] = {
    "ESR":          (0, 20),
    "CRP":          (0, 10),
    "hs-CRP":       (0, 3),
    "C3":           (90, 180),
    "C4":           (16, 47),
    "RF":           (0, 14),
    "Anti-CCP":     (0, 17),
    "WBC":          (4.5, 11.0),
    "Neutrophils":  (1.8, 7.7),
    "Neutrophils%": (40, 70),
    "Lymphocytes":  (1.0, 4.8),
    "Lymphocytes%": (20, 40),
    "Monocytes":    (0.2, 0.95),
    "Monocytes%":   (2, 10),
    "Eosinophils":  (0.0, 0.45),
    "Basophils":    (0.0, 0.1),
    "RDW":          (11.5, 14.5),
    "MPV":          (7.5, 12.5),
    "Hemoglobin":   (12.0, 17.5),
    "Hematocrit":   (36.0, 52.0),
    "MCV":          (80, 100),
    "Platelets":    (150, 400),
    "BUN":          (7, 20),
    "Creatinine":   (0.6, 1.2),
    "ALT":          (7, 56),
    "AST":          (10, 40),
    "ALP":          (44, 147),
    "Albumin":      (3.5, 5.0),
    "Glucose":      (70, 100),
    "Sodium":       (136, 145),
    "Potassium":    (3.5, 5.1),
    "Fecal Calprotectin": (0, 50),
}


# ── Date extraction ───────────────────────────────────────────────────────────

_DATE_PATTERN = re.compile(
    r"(?:collection|collected|date|drawn|report)[\s:]*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

def _extract_date(text: str) -> Optional[str]:
    m = _DATE_PATTERN.search(text)
    if m:
        raw = m.group(1)
        # Normalise to YYYY-MM-DD best-effort
        for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%Y-%m-%d",
                    "%m/%d/%y", "%d/%m/%y"):
            try:
                from datetime import datetime
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


# ── Core regex ────────────────────────────────────────────────────────────────

# Matches: "CRP   14.2  mg/L  [0-10]  H"
_LAB_LINE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 /\-\.%]+?)"
    r"\s{1,6}"
    r"(?P<value>\d+\.?\d*)"
    r"\s*"
    r"(?P<unit>[a-zA-Zµ/%*]{1,15}(?:/[a-zA-ZµL]+)?)?"
    r"(?:\s+[<([\[]*\s*"
    r"(?P<ref_low>\d+\.?\d*)\s*[-–]\s*(?P<ref_high>\d+\.?\d*)"
    r"[)\]>]*)?"
    r"(?:\s+(?P<flag>[HhLlAa*]+))?",
)


def extract_markers(text: str, report_date: Optional[str] = None) -> list[RawMarker]:
    """
    Extract all recognisable lab markers from concatenated PDF text.
    Returns a list of RawMarker objects.
    """
    if not report_date:
        report_date = _extract_date(text)

    markers: list[RawMarker] = []
    seen: set[str] = set()

    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 3:
            continue

        m = _LAB_LINE.match(line)
        if not m:
            continue

        raw_name = m.group("name").strip().lower()
        canonical = MARKER_SYNONYMS.get(raw_name)
        if not canonical:
            # Try partial match
            for synonym, canon in MARKER_SYNONYMS.items():
                if synonym in raw_name or raw_name in synonym:
                    canonical = canon
                    break
        if not canonical:
            continue

        # Avoid duplicates (take first occurrence)
        if canonical in seen:
            continue
        seen.add(canonical)

        try:
            value = float(m.group("value"))
        except (TypeError, ValueError):
            continue

        unit     = (m.group("unit") or "").strip()
        ref_low  = float(m.group("ref_low"))  if m.group("ref_low")  else None
        ref_high = float(m.group("ref_high")) if m.group("ref_high") else None
        flag_raw = (m.group("flag") or "").strip().upper()
        flag     = "H" if flag_raw.startswith("H") else ("L" if flag_raw.startswith("L") else "")

        # Fill reference range from defaults if absent
        if ref_low is None and canonical in REFERENCE_RANGES:
            ref_low, ref_high = REFERENCE_RANGES[canonical]

        # Auto-derive flag if missing
        if not flag and ref_low is not None and ref_high is not None:
            if value > ref_high:
                flag = "H"
            elif value < ref_low:
                flag = "L"

        # Unit normalisation
        value, unit = _normalise_unit(canonical, value, unit)

        markers.append(RawMarker(
            display_name=canonical,
            value=value,
            unit=unit,
            ref_low=ref_low,
            ref_high=ref_high,
            flag=flag,
            date_str=report_date,
        ))

    return markers


def extract_from_tables(
    tables: list[list[list[str]]],
    report_date: Optional[str] = None,
) -> list[RawMarker]:
    """
    Extract markers from pdfplumber table cells (more reliable than raw text).
    Each table row is expected to be: [name, value, unit, ref_range, flag].
    """
    markers: list[RawMarker] = []
    seen: set[str] = set()

    for table in tables:
        for row in table:
            if len(row) < 2:
                continue
            raw_name = row[0].strip().lower()
            canonical = MARKER_SYNONYMS.get(raw_name)
            if not canonical:
                continue
            if canonical in seen:
                continue
            seen.add(canonical)

            try:
                value = float(re.sub(r"[^\d.]", "", row[1]))
            except (ValueError, IndexError):
                continue

            unit     = row[2].strip() if len(row) > 2 else ""
            ref_str  = row[3].strip() if len(row) > 3 else ""
            flag_raw = (row[4].strip().upper() if len(row) > 4 else "")

            ref_low, ref_high = _parse_ref_range(ref_str)
            if ref_low is None and canonical in REFERENCE_RANGES:
                ref_low, ref_high = REFERENCE_RANGES[canonical]

            flag = "H" if "H" in flag_raw else ("L" if "L" in flag_raw else "")
            if not flag and ref_low is not None and ref_high is not None:
                flag = "H" if value > ref_high else ("L" if value < ref_low else "")

            value, unit = _normalise_unit(canonical, value, unit)

            markers.append(RawMarker(
                display_name=canonical,
                value=value,
                unit=unit,
                ref_low=ref_low,
                ref_high=ref_high,
                flag=flag,
                date_str=report_date,
            ))

    return markers


def _parse_ref_range(s: str) -> tuple[Optional[float], Optional[float]]:
    m = re.search(r"(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def _normalise_unit(name: str, value: float, unit: str) -> tuple[float, str]:
    """Convert common non-SI units to SI. Returns (value, unit)."""
    u = unit.lower().strip()
    # CRP / inflammatory proteins: mg/dL → mg/L
    if name in ("CRP", "hs-CRP", "ESR") and u in ("mg/dl", "mg/dl"):
        return value * 10.0, "mg/L"
    # Albumin: g/dL → g/L
    if name == "Albumin" and u == "g/dl":
        return value * 10.0, "g/L"
    # Glucose: mg/dL → mmol/L
    if name == "Glucose" and u == "mg/dl":
        return round(value * 0.0555, 3), "mmol/L"
    return value, unit
