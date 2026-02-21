"""
NHANES Normalizer — The Extractor, Step 3 (Part B).

Computes age/sex-stratified z-scores for patient marker values
using population norms from aura.reference.nhanes_norms.

NHANES column mapping:
  LBXWBCSI  = WBC          LBXNEPCT  = Neutrophil%    LBXLYPCT = Lymphocyte%
  LBXMOPCT  = Monocyte%    LBXRDW    = RDW             LBXMPSI  = MPV
  LBXHSCRP  = hs-CRP       LBXSAL    = Albumin         LBDSBUSI = BUN
  LBXSATSI  = ALT           LBXSASSI  = AST
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Map: canonical display_name → NHANES column
NHANES_COL: dict[str, str] = {
    "WBC":          "LBXWBCSI",
    "Neutrophils%": "LBXNEPCT",
    "Lymphocytes%": "LBXLYPCT",
    "Monocytes%":   "LBXMOPCT",
    "RDW":          "LBXRDW",
    "MPV":          "LBXMPSI",
    "hs-CRP":       "LBXHSCRP",
    "CRP":          "LBXHSCRP",   # Use hs-CRP column for CRP approximation
    "Albumin":      "LBXSAL",
    "BUN":          "LBDSBUSI",
    "ALT":          "LBXSATSI",
    "AST":          "LBXSASSI",
}

# Age brackets used for stratification
AGE_BRACKETS = [(0, 17), (18, 39), (40, 59), (60, 120)]


def _age_bracket(age: int) -> tuple[int, int]:
    for low, high in AGE_BRACKETS:
        if low <= age <= high:
            return low, high
    return AGE_BRACKETS[-1]


class NhanesNormalizer:
    """
    Loads NHANES population statistics from Databricks once,
    then provides fast z-score lookup.
    """

    def __init__(self) -> None:
        # {(nhanes_col, age_low, sex_code): (mean, std)}
        # sex_code: 1 = Male, 2 = Female (NHANES coding)
        self._stats: dict[tuple, tuple[float, float]] = {}
        self._loaded = False

    def load(self) -> None:
        """Compute per-stratum statistics from aura.reference.nhanes_norms."""
        if self._loaded:
            return
        try:
            from nlp.shared.databricks_client import get_client
            client = get_client()

            # Fetch relevant columns
            cols = ", ".join(["SEQN", "RIAGENDR", "RIDAGEYR"] + list(set(NHANES_COL.values())))
            rows = client.run_sql(f"SELECT {cols} FROM aura.reference.nhanes_norms")

            # Column header from the SQL result
            header = ["SEQN", "RIAGENDR", "RIDAGEYR"] + list(set(NHANES_COL.values()))
            df = pd.DataFrame(rows, columns=header)
            df["RIAGENDR"] = pd.to_numeric(df["RIAGENDR"], errors="coerce")
            df["RIDAGEYR"] = pd.to_numeric(df["RIDAGEYR"], errors="coerce")

            for nhanes_col in set(NHANES_COL.values()):
                if nhanes_col not in df.columns:
                    continue
                df[nhanes_col] = pd.to_numeric(df[nhanes_col], errors="coerce")
                for (age_low, age_high) in AGE_BRACKETS:
                    for sex_code in (1, 2):
                        mask = (
                            (df["RIDAGEYR"] >= age_low) &
                            (df["RIDAGEYR"] <= age_high) &
                            (df["RIAGENDR"] == sex_code)
                        )
                        subset = df.loc[mask, nhanes_col].dropna()
                        if len(subset) < 10:
                            continue
                        self._stats[(nhanes_col, age_low, sex_code)] = (
                            float(subset.mean()),
                            float(subset.std()),
                        )

            logger.info(f"Loaded {len(self._stats)} NHANES strata for z-score normalisation")
            self._loaded = True

        except Exception as e:
            logger.warning(f"Could not load NHANES norms: {e}")
            self._loaded = True

    def compute_zscore(
        self,
        display_name: str,
        value: float,
        age: int,
        sex: str,          # "M" or "F"
    ) -> Optional[float]:
        """
        Return the z-score of value relative to the NHANES stratum
        matching age/sex. Returns None if no norm available.
        """
        nhanes_col = NHANES_COL.get(display_name)
        if not nhanes_col:
            return None

        sex_code = 1 if sex.upper() in ("M", "MALE", "1") else 2
        age_low, _ = _age_bracket(age)
        key = (nhanes_col, age_low, sex_code)

        stats = self._stats.get(key)
        if not stats:
            # Try opposite sex as fallback
            alt_key = (nhanes_col, age_low, 3 - sex_code)
            stats = self._stats.get(alt_key)
        if not stats:
            return None

        mean, std = stats
        if std == 0:
            return None
        return round((value - mean) / std, 3)


# Module-level singleton
_normalizer: Optional[NhanesNormalizer] = None


def get_normalizer() -> NhanesNormalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = NhanesNormalizer()
        _normalizer.load()
    return _normalizer
