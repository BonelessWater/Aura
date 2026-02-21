# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle PMC-Patients Clinical Case Reports (Phase 5)
# MAGIC
# MAGIC Registers the PMC-Patients dataset (250K patient case summaries from PubMed
# MAGIC Central) as a Tier 1 table with minimal cleanup: gender standardization and
# MAGIC timestamp precision fix for Delta Lake compatibility.
# MAGIC
# MAGIC **Produces:**
# MAGIC - `pmc_patients` (Tier 1, 250K clinical case reports)
# MAGIC
# MAGIC **Raw data:** `/Volumes/workspace/aura/aura_data/raw/pmc_patients/pmc_patients_v2.parquet`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_pmc_patients")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_PMC = os.path.join(VOLUME_ROOT, "raw", "pmc_patients")


def standardize_gender(gender_val):
    """Standardize gender values to male/female/unknown."""
    if not gender_val or pd.isna(gender_val):
        return "unknown"
    g = str(gender_val).strip().lower()
    if g in ("m", "male", "man", "boy"):
        return "male"
    if g in ("f", "female", "woman", "girl"):
        return "female"
    return "unknown"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load, Clean, and Save

# COMMAND ----------

def wrangle_pmc_patients():
    """Load raw PMC-Patients parquet, standardize gender, fix timestamps."""
    dest = os.path.join(VOLUME_ROOT, "tier1_pmc_patients.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    parquet_path = os.path.join(RAW_PMC, "pmc_patients_v2.parquet")
    if not os.path.exists(parquet_path):
        logger.error("PMC-Patients parquet not found: %s", parquet_path)
        return None

    logger.info("Loading PMC-Patients parquet...")
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        logger.error("Failed to read PMC-Patients parquet: %s", e)
        return None

    logger.info("PMC-Patients raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Columns: %s", list(df.columns))

    # Standardize gender -> sex
    df["sex"] = df["gender"].apply(standardize_gender)
    logger.info("Sex distribution: %s", df["sex"].value_counts().to_dict())

    # Validate age
    if "age_years" in df.columns:
        df["age_years"] = pd.to_numeric(df["age_years"], errors="coerce")
        invalid_age = (df["age_years"] < 0) | (df["age_years"] > 120)
        n_invalid = invalid_age.sum()
        if n_invalid > 0:
            logger.info("Setting %d invalid ages (outside 0-120) to null", n_invalid)
            df.loc[invalid_age, "age_years"] = None

    # Parse pub_date
    if "pub_date" in df.columns:
        df["pub_date"] = pd.to_datetime(df["pub_date"], errors="coerce")

    # Select output columns (drop raw gender in favor of standardized sex, drop age_raw)
    output_cols = [
        "patient_id", "patient_uid", "pmid", "title",
        "patient_summary", "age_years", "sex", "pub_date",
    ]
    output_cols = [c for c in output_cols if c in df.columns]
    result = df[output_cols].copy()

    # Summary
    logger.info("PMC-Patients: %d rows, %d unique PMIDs",
                len(result), result["pmid"].nunique() if "pmid" in result.columns else 0)

    # Convert timestamps to microsecond precision for Delta Lake compatibility
    for col in result.select_dtypes(include=["datetime64[ns]"]).columns:
        result[col] = result[col].dt.floor("us")

    result.to_parquet(dest, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
    logger.info("Saved: %d rows -> %s", len(result), dest)
    return result


pmc_df = wrangle_pmc_patients()
if pmc_df is not None:
    logger.info("PMC-Patients: %d case reports ready", len(pmc_df))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Register Table

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.pmc_patients
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier1_pmc_patients.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT sex, COUNT(*) as cases, ROUND(AVG(age_years), 1) as avg_age,
# MAGIC        MIN(pub_date) as earliest, MAX(pub_date) as latest
# MAGIC FROM workspace.aura.pmc_patients
# MAGIC GROUP BY sex
# MAGIC ORDER BY cases DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `pmc_patients` | 1 | PMC-Patients v2 (HuggingFace) | 250K clinical case reports from PubMed Central |
# MAGIC
# MAGIC **Join strategy:** Not directly joinable to core_matrix by patient_id (different patients).
# MAGIC Primary use: clinical narrative mining, phenotype extraction, few-shot examples for LLM prompts.
