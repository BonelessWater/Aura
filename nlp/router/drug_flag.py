"""
Drug-Induced Autoimmunity Flag — The Router, Step 4.4.

Uses the UCI Drug-Induced Autoimmunity dataset to flag whether
a patient's current medications are associated with drug-induced
autoimmune mimicry.

Dataset loaded at runtime via ucimlrepo (no pre-download needed).
Written to aura.reference.drug_autoimmunity on first run.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DRUG_SET: Optional[set[str]] = None


def _load_drug_set() -> set[str]:
    """Load drug names from UCI dataset, caching in memory."""
    global _DRUG_SET
    if _DRUG_SET is not None:
        return _DRUG_SET

    try:
        from ucimlrepo import fetch_ucirepo
        ds  = fetch_ucirepo(id=1104)
        df  = ds.data.features

        # Try to find a drug name column
        drug_col = None
        for col in df.columns:
            if "drug" in col.lower() or "name" in col.lower():
                drug_col = col
                break

        if drug_col:
            drugs = set(df[drug_col].dropna().str.lower().str.strip())
        else:
            # Fall back to index as drug names if no named column
            drugs = set(df.index.astype(str).str.lower())

        _DRUG_SET = drugs
        logger.info(f"Loaded {len(drugs)} drugs from UCI drug-induced autoimmunity dataset")

        # Write to Databricks on first load
        _write_to_delta(df)

    except Exception as e:
        logger.warning(f"Could not load UCI drug dataset: {e}. Using fallback list.")
        _DRUG_SET = _FALLBACK_DRUGS

    return _DRUG_SET


def _write_to_delta(df) -> None:
    """Write UCI dataset to aura.reference.drug_autoimmunity."""
    try:
        import re
        from nlp.shared.databricks_client import get_client
        import io

        client = get_client()
        client.run_sql("CREATE SCHEMA IF NOT EXISTS aura.reference")

        # Sanitize column names
        df = df.copy()
        df.columns = [re.sub(r"[ ,;{}()\n\t=]+", "_", c).strip("_") for c in df.columns]

        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)

        vol_path = "/Volumes/aura/reference/raw_files/drug_autoimmunity.parquet"
        client.upload_bytes(buf, vol_path)
        client.run_sql(
            f"CREATE OR REPLACE TABLE aura.reference.drug_autoimmunity AS "
            f"SELECT * FROM parquet.`{vol_path}`"
        )
        logger.info("Written UCI drug-induced dataset to aura.reference.drug_autoimmunity")
    except Exception as e:
        logger.warning(f"Delta write for drug dataset failed: {e}")


def check_drug_flag(medications: list[str]) -> tuple[bool, list[str]]:
    """
    Check whether any of the patient's medications are in the
    drug-induced autoimmunity dataset.

    Args:
        medications: list of drug name strings from patient record

    Returns:
        (flagged: bool, flagged_drugs: list[str])
    """
    drug_set = _load_drug_set()
    flagged  = []

    for med in medications:
        med_lower = med.lower().strip()
        # Exact match
        if med_lower in drug_set:
            flagged.append(med)
            continue
        # Partial match (drug name may include dosage)
        for drug in drug_set:
            if drug in med_lower or med_lower in drug:
                flagged.append(med)
                break

    return bool(flagged), flagged


# Known drugs associated with drug-induced lupus as fallback
_FALLBACK_DRUGS = {
    "hydralazine", "procainamide", "isoniazid", "minocycline",
    "d-penicillamine", "methyldopa", "quinidine", "chlorpromazine",
    "carbamazepine", "phenytoin", "etanercept", "infliximab",
    "adalimumab", "certolizumab", "golimumab",
    "interferon", "interferon-alpha", "interferon alpha",
    "terbinafine", "propylthiouracil",
}
