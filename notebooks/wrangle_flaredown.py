# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle Flaredown Patient-Reported Outcomes (Phase 2)
# MAGIC
# MAGIC Processes the Flaredown symptom tracker CSV into a Tier 1 patient-reported
# MAGIC outcomes table. This data has a fundamentally different grain than core_matrix:
# MAGIC daily symptom/treatment/trigger entries per patient.
# MAGIC
# MAGIC **Produces:**
# MAGIC - `patient_reported_outcomes` (Tier 1, ~8M rows from ~1,700 patients)
# MAGIC
# MAGIC **Raw data:** `/Volumes/workspace/aura/aura_data/raw/flaredown/export.csv`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_flaredown")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_FLAREDOWN = os.path.join(VOLUME_ROOT, "raw", "flaredown")

# Map Flaredown condition names to Aura diagnosis clusters
CONDITION_TO_CLUSTER = {
    # Systemic
    "rheumatoid arthritis": "systemic",
    "lupus": "systemic",
    "systemic lupus erythematosus": "systemic",
    "sle": "systemic",
    "sjogren's syndrome": "systemic",
    "sjogren syndrome": "systemic",
    "ankylosing spondylitis": "systemic",
    "psoriatic arthritis": "systemic",
    "scleroderma": "systemic",
    "vasculitis": "systemic",
    "dermatomyositis": "systemic",
    "polymyositis": "systemic",
    "mixed connective tissue disease": "systemic",
    "reactive arthritis": "systemic",
    "undifferentiated connective tissue disease": "systemic",
    "behcet's disease": "systemic",
    "polymyalgia rheumatica": "systemic",
    "fibromyalgia": "other_autoimmune",
    # Gastrointestinal
    "crohn's disease": "gastrointestinal",
    "crohn disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "inflammatory bowel disease": "gastrointestinal",
    "ibd": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "celiac": "gastrointestinal",
    "autoimmune hepatitis": "gastrointestinal",
    "primary biliary cholangitis": "gastrointestinal",
    # Endocrine
    "hashimoto's thyroiditis": "endocrine",
    "hashimoto's disease": "endocrine",
    "hashimotos": "endocrine",
    "graves' disease": "endocrine",
    "graves disease": "endocrine",
    "type 1 diabetes": "endocrine",
    "addison's disease": "endocrine",
    "hypothyroidism": "endocrine",
    "hyperthyroidism": "endocrine",
    # Neurological
    "multiple sclerosis": "neurological",
    "ms": "neurological",
    "myasthenia gravis": "neurological",
    # Dermatological
    "psoriasis": "dermatological",
    "vitiligo": "dermatological",
    "alopecia areata": "dermatological",
    "eczema": "dermatological",
    "dermatitis": "dermatological",
    "lichen planus": "dermatological",
    # Haematological
    "immune thrombocytopenia": "haematological",
    "itp": "haematological",
}


def map_condition_to_cluster(condition_name):
    """Map a Flaredown condition name to an Aura diagnosis cluster."""
    if not condition_name or pd.isna(condition_name):
        return None
    cond_lower = str(condition_name).lower().strip()

    # Direct match
    if cond_lower in CONDITION_TO_CLUSTER:
        return CONDITION_TO_CLUSTER[cond_lower]

    # Fuzzy keyword match
    for keyword, cluster in CONDITION_TO_CLUSTER.items():
        if keyword in cond_lower or cond_lower in keyword:
            return cluster

    return "other_autoimmune"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load and Parse Flaredown Data
# MAGIC
# MAGIC The CSV has columns: user_id, age, sex, country, checkin_date,
# MAGIC trackable_id, trackable_type, trackable_name, trackable_value.
# MAGIC
# MAGIC trackable_type values: Condition, Symptom, Treatment, Food, Tag, Weather, HBI

# COMMAND ----------

def wrangle_flaredown():
    """Load and wrangle Flaredown patient-reported outcomes."""
    dest = os.path.join(VOLUME_ROOT, "tier1_patient_reported_outcomes.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    csv_path = os.path.join(RAW_FLAREDOWN, "export.csv")
    if not os.path.exists(csv_path):
        logger.error("Flaredown CSV not found: %s", csv_path)
        return None

    logger.info("Loading Flaredown CSV (this may take a moment for ~8M rows)...")
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as e:
        logger.error("Failed to read Flaredown CSV: %s", e)
        return None

    logger.info("Flaredown raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Columns: %s", list(df.columns))
    logger.info("  Trackable types: %s", df["trackable_type"].value_counts().to_dict())

    # Filter to clinically relevant types (exclude Weather, Tag)
    relevant_types = ["Condition", "Symptom", "Treatment", "Food", "HBI"]
    df = df[df["trackable_type"].isin(relevant_types)].copy()
    logger.info("After filtering to relevant types: %d rows", len(df))

    # Generate patient_id
    df["patient_id"] = "flaredown_" + df["user_id"].astype(str)

    # Parse date
    df["date"] = pd.to_datetime(df["checkin_date"], errors="coerce")
    pre_date = len(df)
    df = df.dropna(subset=["date"])
    if pre_date > len(df):
        logger.info("Dropped %d rows with invalid dates", pre_date - len(df))

    # Build condition lookup per patient (from Condition rows)
    condition_rows = df[df["trackable_type"] == "Condition"]
    patient_conditions = (
        condition_rows.groupby("patient_id")["trackable_name"]
        .first()
        .to_dict()
    )
    logger.info("Patients with conditions: %d", len(patient_conditions))

    # Map conditions to clusters
    patient_clusters = {
        pid: map_condition_to_cluster(cond)
        for pid, cond in patient_conditions.items()
    }

    # Build output table
    # Pivot trackable_type into separate columns
    result_rows = []

    # Process Symptom rows
    symptoms = df[df["trackable_type"] == "Symptom"]
    if not symptoms.empty:
        sym_df = pd.DataFrame({
            "patient_id": symptoms["patient_id"].values,
            "source": "flaredown",
            "date": symptoms["date"].values,
            "condition": symptoms["patient_id"].map(patient_conditions).values,
            "diagnosis_cluster": symptoms["patient_id"].map(patient_clusters).values,
            "symptom": symptoms["trackable_name"].values,
            "symptom_severity": pd.to_numeric(symptoms["trackable_value"], errors="coerce").values,
            "treatment": None,
            "treatment_dose": None,
            "trigger": None,
            "country": symptoms["country"].values,
            "age": pd.to_numeric(symptoms["age"], errors="coerce").values,
            "sex": symptoms["sex"].values,
        })
        result_rows.append(sym_df)
        logger.info("Symptom rows: %d", len(sym_df))

    # Process Treatment rows
    treatments = df[df["trackable_type"] == "Treatment"]
    if not treatments.empty:
        treat_df = pd.DataFrame({
            "patient_id": treatments["patient_id"].values,
            "source": "flaredown",
            "date": treatments["date"].values,
            "condition": treatments["patient_id"].map(patient_conditions).values,
            "diagnosis_cluster": treatments["patient_id"].map(patient_clusters).values,
            "symptom": None,
            "symptom_severity": None,
            "treatment": treatments["trackable_name"].values,
            "treatment_dose": treatments["trackable_value"].values,
            "trigger": None,
            "country": treatments["country"].values,
            "age": pd.to_numeric(treatments["age"], errors="coerce").values,
            "sex": treatments["sex"].values,
        })
        result_rows.append(treat_df)
        logger.info("Treatment rows: %d", len(treat_df))

    # Process Food rows (as triggers)
    foods = df[df["trackable_type"] == "Food"]
    if not foods.empty:
        food_df = pd.DataFrame({
            "patient_id": foods["patient_id"].values,
            "source": "flaredown",
            "date": foods["date"].values,
            "condition": foods["patient_id"].map(patient_conditions).values,
            "diagnosis_cluster": foods["patient_id"].map(patient_clusters).values,
            "symptom": None,
            "symptom_severity": None,
            "treatment": None,
            "treatment_dose": None,
            "trigger": foods["trackable_name"].values,
            "country": foods["country"].values,
            "age": pd.to_numeric(foods["age"], errors="coerce").values,
            "sex": foods["sex"].values,
        })
        result_rows.append(food_df)
        logger.info("Food/trigger rows: %d", len(food_df))

    if not result_rows:
        logger.warning("No relevant rows found in Flaredown data.")
        return None

    result = pd.concat(result_rows, ignore_index=True)

    # Summary
    logger.info("Patient-reported outcomes: %d rows, %d unique patients",
                len(result), result["patient_id"].nunique())
    logger.info("  Cluster distribution: %s",
                result["diagnosis_cluster"].value_counts(dropna=False).to_dict())
    logger.info("  Date range: %s to %s",
                result["date"].min(), result["date"].max())

    # Convert timestamps to microsecond precision for Delta Lake compatibility
    for col in result.select_dtypes(include=["datetime64[ns]"]).columns:
        result[col] = result[col].dt.floor("us")

    result.to_parquet(dest, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
    logger.info("Saved patient_reported_outcomes: %d rows -> %s", len(result), dest)
    return result


flaredown_df = wrangle_flaredown()
if flaredown_df is not None:
    print(f"Flaredown: {len(flaredown_df)} rows, {flaredown_df['patient_id'].nunique()} patients")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Register Table

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.patient_reported_outcomes
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier1_patient_reported_outcomes.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT diagnosis_cluster, COUNT(*) as rows, COUNT(DISTINCT patient_id) as patients
# MAGIC FROM workspace.aura.patient_reported_outcomes
# MAGIC GROUP BY diagnosis_cluster
# MAGIC ORDER BY rows DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `patient_reported_outcomes` | 1 | Flaredown | Daily symptom/treatment/trigger tracking (~8M rows, ~1,700 patients) |
# MAGIC
# MAGIC **Join strategy:** Not joinable to core_matrix by patient_id (different patients).
# MAGIC Joinable by `diagnosis_cluster` for disease-level aggregation.
# MAGIC Primary use: learning symptom-treatment-trigger temporal patterns per condition.
