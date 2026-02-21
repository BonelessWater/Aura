"""
LOINC Mapper — The Extractor, Step 3 (Part A).

Loads aura.reference.loinc from Databricks once, then provides fast
fuzzy-match lookup from raw marker display names to LOINC codes.

Uses rapidfuzz for sub-millisecond matching.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum fuzzy score (0–100) to accept a match
MATCH_THRESHOLD = 85

# Hard-coded priority map for the most common markers
# (avoids fuzzy match ambiguity for critical biomarkers)
PRIORITY_MAP: dict[str, str] = {
    "ESR":              "4537-7",
    "CRP":              "1988-5",
    "hs-CRP":           "30522-7",
    "C3":               "4498-2",
    "C4":               "4499-0",
    "RF":               "11572-5",
    "Anti-CCP":         "14052-3",
    "ANA":              "5049-7",
    "anti-dsDNA":       "5221-2",
    "HLA-B27":          "13288-5",
    "anti-Ro":          "20996-8",
    "anti-La":          "5253-5",
    "anti-SM":          "5234-5",
    "WBC":              "6690-2",
    "Neutrophils":      "751-8",
    "Neutrophils%":     "770-8",
    "Lymphocytes":      "731-0",
    "Lymphocytes%":     "736-9",
    "Monocytes":        "742-7",
    "Monocytes%":       "5905-5",
    "Eosinophils":      "711-2",
    "Basophils":        "704-7",
    "Platelets":        "777-3",
    "RDW":              "788-0",
    "MPV":              "32623-1",
    "Hemoglobin":       "718-7",
    "Hematocrit":       "4544-3",
    "MCV":              "787-2",
    "MCH":              "785-6",
    "RBC":              "789-8",
    "BUN":              "3094-0",
    "Creatinine":       "2160-0",
    "eGFR":             "33914-3",
    "ALT":              "1742-6",
    "AST":              "1920-8",
    "ALP":              "6768-6",
    "Bilirubin":        "1975-2",
    "Albumin":          "1751-7",
    "Glucose":          "2345-7",
    "Sodium":           "2951-2",
    "Potassium":        "2823-3",
    "CO2":              "2028-9",
    "Magnesium":        "2601-3",
    "Calcium":          "17861-6",
    "Phosphorus":       "2777-1",
    "Fecal Calprotectin": "45179-7",
}


class LoincMapper:
    """
    Loads LOINC data from Databricks and provides fast lookup.

    Usage:
        mapper = LoincMapper()
        code, name = mapper.lookup("c-reactive protein")
    """

    def __init__(self) -> None:
        self._loinc_dict: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> None:
        """Load LOINC table from Databricks into memory."""
        if self._loaded:
            return
        try:
            from nlp.shared.databricks_client import get_client
            client = get_client()
            rows = client.run_sql(
                "SELECT LOINC_NUM, SHORTNAME, LONG_COMMON_NAME, EXAMPLE_UNITS "
                "FROM aura.reference.loinc"
            )
            for row in rows:
                loinc_num, shortname, long_name, example_units = row
                self._loinc_dict[str(loinc_num)] = {
                    "shortname":     shortname or "",
                    "long_name":     long_name or "",
                    "example_units": example_units or "",
                }
            logger.info(f"Loaded {len(self._loinc_dict):,} LOINC codes")
            self._loaded = True
        except Exception as e:
            logger.warning(f"Could not load LOINC from Databricks: {e}. Using priority map only.")
            self._loaded = True  # Don't retry on every call

    def lookup(self, display_name: str) -> tuple[Optional[str], Optional[str]]:
        """
        Map a display name string to (loinc_code, canonical_display_name).
        Returns (None, None) if no confident match found.
        """
        # 1. Priority map first (fast, deterministic)
        if display_name in PRIORITY_MAP:
            code = PRIORITY_MAP[display_name]
            info = self._loinc_dict.get(code, {})
            return code, info.get("shortname", display_name)

        # 2. Fuzzy match against loaded LOINC names
        if not self._loinc_dict:
            return None, None

        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            return None, None

        # Build candidate list (shortname + long_name)
        candidates = {}
        for code, info in self._loinc_dict.items():
            for key in ("shortname", "long_name"):
                name = info.get(key, "")
                if name:
                    candidates[name] = code

        result = process.extractOne(
            display_name,
            candidates.keys(),
            scorer=fuzz.token_set_ratio,
            score_cutoff=MATCH_THRESHOLD,
        )
        if result:
            matched_name, score, _ = result
            code = candidates[matched_name]
            return code, matched_name

        logger.debug(f"No LOINC match for '{display_name}' (threshold {MATCH_THRESHOLD})")
        return None, None


# Module-level singleton
_mapper: Optional[LoincMapper] = None


def get_mapper() -> LoincMapper:
    global _mapper
    if _mapper is None:
        _mapper = LoincMapper()
        _mapper.load()
    return _mapper
