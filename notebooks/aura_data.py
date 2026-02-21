# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Data Access Layer
# MAGIC
# MAGIC Run this notebook once to create reusable SQL views and Python helpers
# MAGIC for working with the `workspace.aura` data lake.
# MAGIC
# MAGIC **What this creates:**
# MAGIC - `v_catalog` -- inventory of all tables with row counts
# MAGIC - `v_core_with_autoantibodies` -- core_matrix LEFT JOIN autoantibody_panel
# MAGIC - `v_training_binary` -- binary classification dataset (autoimmune vs healthy)
# MAGIC - `v_training_multiclass` -- multiclass cluster classification dataset
# MAGIC - `v_patient_abnormal_flags` -- flags lab values outside healthy reference ranges
# MAGIC - `v_cluster_summary` -- per-cluster lab averages and patient counts
# MAGIC - `v_genetic_top_genes` -- top GWAS genes per diagnosis cluster
# MAGIC
# MAGIC **Python helpers** (available after running the Setup cell):
# MAGIC - `aura(table_name)` -- load any table as a Spark DataFrame
# MAGIC - `filter_core(source, cluster, age_min, age_max, sex)` -- filtered core_matrix
# MAGIC - `disease_to_cluster(name)` -- disease name to Aura cluster lookup
# MAGIC - `reference_range(age, sex)` -- healthy reference ranges for a given patient
# MAGIC - `flag_abnormal(patient_id)` -- compare a patient's labs against baselines
# MAGIC - `catalog()` -- print what's available

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_data")

SCHEMA = "workspace.aura"

TABLES = {
    "core_matrix":          {"tier": 1, "desc": "Patient-level labs + diagnoses (48K rows)"},
    "autoantibody_panel":   {"tier": 2, "desc": "Harvard autoantibody binary flags (12K rows)"},
    "longitudinal_labs":    {"tier": 2, "desc": "MIMIC time-series lab events (20K rows)"},
    "genetic_risk_scores":  {"tier": 2, "desc": "FinnGen + HugeAmp GWAS hits (70K rows)"},
    "healthy_baselines":    {"tier": 3, "desc": "NHANES age/sex reference ranges (110 rows)"},
    "icd_cluster_map":      {"tier": 3, "desc": "ICD-10 to Aura cluster lookup (111 rows)"},
    "drug_risk_index":      {"tier": 3, "desc": "UCI drug molecular descriptors (597 rows)"},
}

AURA_CLUSTERS = [
    "healthy", "systemic", "endocrine", "gastrointestinal",
    "neurological", "dermatological", "ophthalmic",
    "other_autoimmune", "haematological", "renal", "pulmonary",
]

LAB_MARKERS = [
    "wbc", "rbc", "hemoglobin", "hematocrit", "platelet_count",
    "mcv", "mch", "rdw", "esr", "crp", "lymphocyte_pct", "neutrophil_pct",
]

# Disease name to cluster mapping (subset of the full DISEASE_TO_ICD10 dictionary,
# focused on the conditions actually present in the data lake)
DISEASE_CLUSTER_MAP = {
    "rheumatoid arthritis":     "systemic",
    "systemic lupus erythematosus": "systemic",
    "sle":                      "systemic",
    "lupus":                    "systemic",
    "sjogren's syndrome":       "systemic",
    "sjogrens":                 "systemic",
    "psoriatic arthritis":      "systemic",
    "reactive arthritis":       "systemic",
    "ankylosing spondylitis":   "other_autoimmune",
    "scleroderma":              "systemic",
    "systemic sclerosis":       "systemic",
    "mixed connective tissue disease": "systemic",
    "dermatomyositis":          "systemic",
    "polymyositis":             "systemic",
    "hashimoto's thyroiditis":  "endocrine",
    "autoimmune thyroiditis":   "endocrine",
    "graves' disease":          "endocrine",
    "graves":                   "endocrine",
    "type 1 diabetes":          "endocrine",
    "t1d":                      "endocrine",
    "addison's disease":        "endocrine",
    "crohn's disease":          "gastrointestinal",
    "crohns":                   "gastrointestinal",
    "ulcerative colitis":       "gastrointestinal",
    "celiac disease":           "gastrointestinal",
    "celiac":                   "gastrointestinal",
    "ibd":                      "gastrointestinal",
    "inflammatory bowel disease": "gastrointestinal",
    "multiple sclerosis":       "neurological",
    "ms":                       "neurological",
    "myasthenia gravis":        "neurological",
    "guillain-barre syndrome":  "neurological",
    "psoriasis":                "dermatological",
    "vitiligo":                 "dermatological",
    "alopecia areata":          "dermatological",
    "pemphigus":                "dermatological",
    "uveitis":                  "ophthalmic",
    "itp":                      "haematological",
    "autoimmune hemolytic anemia": "haematological",
    "lupus nephritis":          "renal",
    "pulmonary fibrosis":       "pulmonary",
    "sarcoidosis":              "other_autoimmune",
}

AGE_BUCKETS = [
    (0, 17, "0-17"),
    (18, 30, "18-30"),
    (31, 45, "31-45"),
    (46, 60, "46-60"),
    (61, 200, "61+"),
]

logger.info("Aura data access layer loaded. Schema: %s", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Catalog View
# MAGIC Shows all available tables with row counts and column counts.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_catalog AS
# MAGIC SELECT 'core_matrix' AS table_name, 1 AS tier, COUNT(*) AS row_count FROM workspace.aura.core_matrix
# MAGIC UNION ALL
# MAGIC SELECT 'autoantibody_panel', 2, COUNT(*) FROM workspace.aura.autoantibody_panel
# MAGIC UNION ALL
# MAGIC SELECT 'longitudinal_labs', 2, COUNT(*) FROM workspace.aura.longitudinal_labs
# MAGIC UNION ALL
# MAGIC SELECT 'genetic_risk_scores', 2, COUNT(*) FROM workspace.aura.genetic_risk_scores
# MAGIC UNION ALL
# MAGIC SELECT 'healthy_baselines', 3, COUNT(*) FROM workspace.aura.healthy_baselines
# MAGIC UNION ALL
# MAGIC SELECT 'icd_cluster_map', 3, COUNT(*) FROM workspace.aura.icd_cluster_map
# MAGIC UNION ALL
# MAGIC SELECT 'drug_risk_index', 3, COUNT(*) FROM workspace.aura.drug_risk_index
# MAGIC ORDER BY tier, table_name;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM workspace.aura.v_catalog;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Core + Autoantibodies View
# MAGIC Left-joins core_matrix with autoantibody_panel so every patient row includes
# MAGIC autoantibody results where available (Harvard patients only).

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_core_with_autoantibodies AS
# MAGIC SELECT
# MAGIC   cm.*,
# MAGIC   ab.ana_status,
# MAGIC   ab.anti_dsdna,
# MAGIC   ab.hla_b27,
# MAGIC   ab.anti_sm,
# MAGIC   ab.anti_ro,
# MAGIC   ab.anti_la,
# MAGIC   ab.rf_status,
# MAGIC   ab.anti_ccp,
# MAGIC   ab.c3,
# MAGIC   ab.c4
# MAGIC FROM workspace.aura.core_matrix cm
# MAGIC LEFT JOIN workspace.aura.autoantibody_panel ab
# MAGIC   ON cm.patient_id = ab.patient_id;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Training Dataset Views
# MAGIC Ready-to-use feature matrices for ML training.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Binary classification: autoimmune (1) vs healthy (0)
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_training_binary AS
# MAGIC SELECT
# MAGIC   patient_id,
# MAGIC   source,
# MAGIC   age,
# MAGIC   CASE WHEN sex = 'M' THEN 1 ELSE 0 END AS sex_numeric,
# MAGIC   wbc, rbc, hemoglobin, hematocrit, platelet_count,
# MAGIC   mcv, mch, rdw, esr, crp, bmi,
# MAGIC   lymphocyte_pct, neutrophil_pct,
# MAGIC   wbc_zscore, rbc_zscore, hemoglobin_zscore, hematocrit_zscore,
# MAGIC   platelet_count_zscore, mcv_zscore, mch_zscore, rdw_zscore,
# MAGIC   crp_zscore,
# MAGIC   esr_missing, crp_missing, wbc_missing, rbc_missing,
# MAGIC   hemoglobin_missing, hematocrit_missing, platelet_count_missing,
# MAGIC   CASE WHEN diagnosis_cluster = 'healthy' THEN 0 ELSE 1 END AS label,
# MAGIC   diagnosis_cluster
# MAGIC FROM workspace.aura.core_matrix
# MAGIC WHERE diagnosis_cluster IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Multiclass: predict which autoimmune cluster (excludes healthy)
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_training_multiclass AS
# MAGIC SELECT
# MAGIC   patient_id,
# MAGIC   source,
# MAGIC   age,
# MAGIC   CASE WHEN sex = 'M' THEN 1 ELSE 0 END AS sex_numeric,
# MAGIC   wbc, rbc, hemoglobin, hematocrit, platelet_count,
# MAGIC   mcv, mch, rdw, esr, crp, bmi,
# MAGIC   lymphocyte_pct, neutrophil_pct,
# MAGIC   wbc_zscore, rbc_zscore, hemoglobin_zscore, hematocrit_zscore,
# MAGIC   platelet_count_zscore, mcv_zscore, mch_zscore, rdw_zscore,
# MAGIC   crp_zscore,
# MAGIC   esr_missing, crp_missing, wbc_missing, rbc_missing,
# MAGIC   hemoglobin_missing, hematocrit_missing, platelet_count_missing,
# MAGIC   diagnosis_cluster AS label
# MAGIC FROM workspace.aura.core_matrix
# MAGIC WHERE diagnosis_cluster IS NOT NULL
# MAGIC   AND diagnosis_cluster != 'healthy';

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Patient Abnormal Flags View
# MAGIC For each patient, compares lab values against age/sex-matched healthy reference
# MAGIC ranges (p5/p95). Flags values as 'low', 'high', or 'normal'.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_patient_abnormal_flags AS
# MAGIC WITH patient_buckets AS (
# MAGIC   SELECT
# MAGIC     patient_id, source, age, sex, diagnosis_cluster,
# MAGIC     wbc, rbc, hemoglobin, hematocrit, platelet_count,
# MAGIC     mcv, mch, rdw, crp, lymphocyte_pct, neutrophil_pct,
# MAGIC     CASE
# MAGIC       WHEN age <= 17 THEN '0-17'
# MAGIC       WHEN age <= 30 THEN '18-30'
# MAGIC       WHEN age <= 45 THEN '31-45'
# MAGIC       WHEN age <= 60 THEN '46-60'
# MAGIC       ELSE '61+'
# MAGIC     END AS age_bucket
# MAGIC   FROM workspace.aura.core_matrix
# MAGIC   WHERE age IS NOT NULL AND sex IS NOT NULL
# MAGIC ),
# MAGIC flagged AS (
# MAGIC   SELECT
# MAGIC     p.patient_id,
# MAGIC     p.source,
# MAGIC     p.age,
# MAGIC     p.sex,
# MAGIC     p.age_bucket,
# MAGIC     p.diagnosis_cluster,
# MAGIC     -- WBC flags
# MAGIC     p.wbc,
# MAGIC     bw.p5 AS wbc_p5, bw.p95 AS wbc_p95,
# MAGIC     CASE
# MAGIC       WHEN p.wbc IS NULL THEN 'no_data'
# MAGIC       WHEN p.wbc < bw.p5 THEN 'low'
# MAGIC       WHEN p.wbc > bw.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS wbc_flag,
# MAGIC     -- RBC flags
# MAGIC     p.rbc,
# MAGIC     br.p5 AS rbc_p5, br.p95 AS rbc_p95,
# MAGIC     CASE
# MAGIC       WHEN p.rbc IS NULL THEN 'no_data'
# MAGIC       WHEN p.rbc < br.p5 THEN 'low'
# MAGIC       WHEN p.rbc > br.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS rbc_flag,
# MAGIC     -- Hemoglobin flags
# MAGIC     p.hemoglobin,
# MAGIC     bh.p5 AS hemoglobin_p5, bh.p95 AS hemoglobin_p95,
# MAGIC     CASE
# MAGIC       WHEN p.hemoglobin IS NULL THEN 'no_data'
# MAGIC       WHEN p.hemoglobin < bh.p5 THEN 'low'
# MAGIC       WHEN p.hemoglobin > bh.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS hemoglobin_flag,
# MAGIC     -- Hematocrit flags
# MAGIC     p.hematocrit,
# MAGIC     bhct.p5 AS hematocrit_p5, bhct.p95 AS hematocrit_p95,
# MAGIC     CASE
# MAGIC       WHEN p.hematocrit IS NULL THEN 'no_data'
# MAGIC       WHEN p.hematocrit < bhct.p5 THEN 'low'
# MAGIC       WHEN p.hematocrit > bhct.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS hematocrit_flag,
# MAGIC     -- Platelet flags
# MAGIC     p.platelet_count,
# MAGIC     bp.p5 AS platelet_p5, bp.p95 AS platelet_p95,
# MAGIC     CASE
# MAGIC       WHEN p.platelet_count IS NULL THEN 'no_data'
# MAGIC       WHEN p.platelet_count < bp.p5 THEN 'low'
# MAGIC       WHEN p.platelet_count > bp.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS platelet_flag,
# MAGIC     -- CRP flags
# MAGIC     p.crp,
# MAGIC     bc.p5 AS crp_p5, bc.p95 AS crp_p95,
# MAGIC     CASE
# MAGIC       WHEN p.crp IS NULL THEN 'no_data'
# MAGIC       WHEN p.crp < bc.p5 THEN 'low'
# MAGIC       WHEN p.crp > bc.p95 THEN 'high'
# MAGIC       ELSE 'normal'
# MAGIC     END AS crp_flag,
# MAGIC     -- Count of abnormal flags per patient
# MAGIC     (CASE WHEN p.wbc IS NOT NULL AND (p.wbc < bw.p5 OR p.wbc > bw.p95) THEN 1 ELSE 0 END
# MAGIC      + CASE WHEN p.rbc IS NOT NULL AND (p.rbc < br.p5 OR p.rbc > br.p95) THEN 1 ELSE 0 END
# MAGIC      + CASE WHEN p.hemoglobin IS NOT NULL AND (p.hemoglobin < bh.p5 OR p.hemoglobin > bh.p95) THEN 1 ELSE 0 END
# MAGIC      + CASE WHEN p.hematocrit IS NOT NULL AND (p.hematocrit < bhct.p5 OR p.hematocrit > bhct.p95) THEN 1 ELSE 0 END
# MAGIC      + CASE WHEN p.platelet_count IS NOT NULL AND (p.platelet_count < bp.p5 OR p.platelet_count > bp.p95) THEN 1 ELSE 0 END
# MAGIC      + CASE WHEN p.crp IS NOT NULL AND (p.crp < bc.p5 OR p.crp > bc.p95) THEN 1 ELSE 0 END
# MAGIC     ) AS abnormal_count
# MAGIC   FROM patient_buckets p
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines bw
# MAGIC     ON bw.marker = 'wbc' AND bw.age_bucket = p.age_bucket AND bw.sex = p.sex
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines br
# MAGIC     ON br.marker = 'rbc' AND br.age_bucket = p.age_bucket AND br.sex = p.sex
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines bh
# MAGIC     ON bh.marker = 'hemoglobin' AND bh.age_bucket = p.age_bucket AND bh.sex = p.sex
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines bhct
# MAGIC     ON bhct.marker = 'hematocrit' AND bhct.age_bucket = p.age_bucket AND bhct.sex = p.sex
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines bp
# MAGIC     ON bp.marker = 'platelet_count' AND bp.age_bucket = p.age_bucket AND bp.sex = p.sex
# MAGIC   LEFT JOIN workspace.aura.healthy_baselines bc
# MAGIC     ON bc.marker = 'crp' AND bc.age_bucket = p.age_bucket AND bc.sex = p.sex
# MAGIC )
# MAGIC SELECT * FROM flagged;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Cluster Summary View
# MAGIC Per-cluster average labs, patient counts, and source distribution.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_cluster_summary AS
# MAGIC SELECT
# MAGIC   diagnosis_cluster,
# MAGIC   COUNT(*) AS patient_count,
# MAGIC   COUNT(DISTINCT source) AS source_count,
# MAGIC   ROUND(AVG(age), 1) AS avg_age,
# MAGIC   ROUND(AVG(wbc), 2) AS avg_wbc,
# MAGIC   ROUND(AVG(rbc), 2) AS avg_rbc,
# MAGIC   ROUND(AVG(hemoglobin), 2) AS avg_hemoglobin,
# MAGIC   ROUND(AVG(platelet_count), 1) AS avg_platelets,
# MAGIC   ROUND(AVG(esr), 2) AS avg_esr,
# MAGIC   ROUND(AVG(crp), 2) AS avg_crp,
# MAGIC   ROUND(AVG(hematocrit), 2) AS avg_hematocrit,
# MAGIC   ROUND(AVG(rdw), 2) AS avg_rdw
# MAGIC FROM workspace.aura.core_matrix
# MAGIC WHERE diagnosis_cluster IS NOT NULL
# MAGIC GROUP BY diagnosis_cluster
# MAGIC ORDER BY patient_count DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM workspace.aura.v_cluster_summary;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Genetic Top Genes View
# MAGIC Top GWAS genes per diagnosis cluster, ranked by strongest p-value.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW workspace.aura.v_genetic_top_genes AS
# MAGIC WITH ranked AS (
# MAGIC   SELECT
# MAGIC     diagnosis_cluster,
# MAGIC     gene,
# MAGIC     COUNT(*) AS variant_count,
# MAGIC     MIN(pvalue) AS best_pvalue,
# MAGIC     AVG(ABS(beta)) AS avg_abs_beta,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY diagnosis_cluster ORDER BY MIN(pvalue)) AS rank
# MAGIC   FROM workspace.aura.genetic_risk_scores
# MAGIC   WHERE gene IS NOT NULL AND gene != ''
# MAGIC   GROUP BY diagnosis_cluster, gene
# MAGIC )
# MAGIC SELECT
# MAGIC   diagnosis_cluster, gene, variant_count, best_pvalue, avg_abs_beta, rank
# MAGIC FROM ranked
# MAGIC WHERE rank <= 25;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Python Helper Functions
# MAGIC These are available in this notebook and any notebook that `%run`s this one.

# COMMAND ----------

def aura(table_name):
    """Load any Aura table as a Spark DataFrame.

    Args:
        table_name: Short name (e.g. 'core_matrix') or view name (e.g. 'v_training_binary').

    Returns:
        Spark DataFrame.

    Example:
        df = aura('core_matrix')
        df = aura('v_training_binary')
    """
    full_name = f"{SCHEMA}.{table_name}"
    try:
        df = spark.table(full_name)
        logger.info("Loaded %s: %d rows", full_name, df.count())
        return df
    except Exception as exc:
        logger.error("Failed to load %s: %s", full_name, exc)
        raise


def filter_core(source=None, cluster=None, age_min=None, age_max=None, sex=None):
    """Filter core_matrix with optional criteria. All filters combine with AND.

    Args:
        source: 'harvard', 'nhanes', or 'mimic_demo'.
        cluster: One of AURA_CLUSTERS (e.g. 'systemic', 'healthy').
        age_min: Minimum age (inclusive).
        age_max: Maximum age (inclusive).
        sex: 'M' or 'F'.

    Returns:
        Spark DataFrame with matching rows.

    Example:
        lupus_women = filter_core(source='harvard', cluster='systemic', sex='F')
        young_healthy = filter_core(cluster='healthy', age_max=30)
    """
    conditions = []

    if source is not None:
        conditions.append(f"source = '{source}'")

    if cluster is not None:
        if cluster not in AURA_CLUSTERS:
            raise ValueError(
                f"Unknown cluster '{cluster}'. Valid clusters: {AURA_CLUSTERS}"
            )
        conditions.append(f"diagnosis_cluster = '{cluster}'")

    if age_min is not None:
        conditions.append(f"age >= {age_min}")

    if age_max is not None:
        conditions.append(f"age <= {age_max}")

    if sex is not None:
        if sex not in ("M", "F"):
            raise ValueError(f"sex must be 'M' or 'F', got '{sex}'")
        conditions.append(f"sex = '{sex}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM {SCHEMA}.core_matrix WHERE {where_clause}"
    logger.info("filter_core: %s", query)
    return spark.sql(query)


def disease_to_cluster(name):
    """Map a disease name to its Aura diagnosis cluster.

    Case-insensitive lookup against common autoimmune conditions.

    Args:
        name: Disease name (e.g. 'Rheumatoid Arthritis', 'lupus', 'Crohn's Disease').

    Returns:
        Cluster name string, or None if not found.

    Example:
        disease_to_cluster('Lupus')         # returns 'systemic'
        disease_to_cluster('Celiac')        # returns 'gastrointestinal'
        disease_to_cluster('Not A Disease') # returns None
    """
    return DISEASE_CLUSTER_MAP.get(name.lower().strip())


def _age_to_bucket(age):
    """Convert a numeric age to the healthy_baselines age bucket string."""
    for low, high, label in AGE_BUCKETS:
        if low <= age <= high:
            return label
    return "61+"


def reference_range(age, sex, marker=None):
    """Get healthy reference ranges for a given age and sex.

    Args:
        age: Patient age in years (numeric).
        sex: 'M' or 'F'.
        marker: Optional specific marker (e.g. 'wbc', 'crp'). If None, returns all markers.

    Returns:
        Spark DataFrame with columns: marker, age_bucket, sex, count, p5, p25, p50, p75, p95.

    Example:
        reference_range(35, 'M')               # all markers for 35yo male
        reference_range(35, 'M', marker='wbc')  # just WBC
    """
    bucket = _age_to_bucket(age)
    query = f"""
        SELECT * FROM {SCHEMA}.healthy_baselines
        WHERE age_bucket = '{bucket}' AND sex = '{sex}'
    """
    if marker is not None:
        query += f" AND marker = '{marker}'"
    return spark.sql(query)


def flag_abnormal(patient_id):
    """Show which lab values are abnormal for a specific patient.

    Compares the patient's labs against their age/sex-matched healthy
    reference ranges (p5 = low threshold, p95 = high threshold).

    Args:
        patient_id: The patient_id string (e.g. 'harvard_00001', 'nhanes_12345').

    Returns:
        Spark DataFrame with columns: marker, value, p5, p95, status.
        status is 'low', 'high', 'normal', or 'no_data'.

    Example:
        flag_abnormal('harvard_00001').show()
    """
    query = f"""
        SELECT
          patient_id, age, sex, diagnosis_cluster,
          wbc_flag, rbc_flag, hemoglobin_flag, hematocrit_flag,
          platelet_flag, crp_flag, abnormal_count,
          wbc, wbc_p5, wbc_p95,
          rbc, rbc_p5, rbc_p95,
          hemoglobin, hemoglobin_p5, hemoglobin_p95,
          hematocrit, hematocrit_p5, hematocrit_p95,
          platelet_count, platelet_p5, platelet_p95,
          crp, crp_p5, crp_p95
        FROM {SCHEMA}.v_patient_abnormal_flags
        WHERE patient_id = '{patient_id}'
    """
    return spark.sql(query)


def catalog():
    """Print and return the data lake inventory.

    Returns:
        Spark DataFrame from v_catalog (table_name, tier, row_count).

    Example:
        catalog().show()
    """
    df = spark.sql(f"SELECT * FROM {SCHEMA}.v_catalog")
    df.show(truncate=False)
    return df

logger.info("Python helpers loaded: aura(), filter_core(), disease_to_cluster(), reference_range(), flag_abnormal(), catalog()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Quick Verification
# MAGIC Run these cells to confirm everything works.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Data lake inventory
# MAGIC SELECT * FROM workspace.aura.v_catalog;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Cluster-level lab averages
# MAGIC SELECT * FROM workspace.aura.v_cluster_summary;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Patients with the most abnormal lab values
# MAGIC SELECT patient_id, source, diagnosis_cluster, abnormal_count,
# MAGIC        wbc_flag, hemoglobin_flag, platelet_flag, crp_flag
# MAGIC FROM workspace.aura.v_patient_abnormal_flags
# MAGIC WHERE abnormal_count >= 3
# MAGIC ORDER BY abnormal_count DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Top genetic hits per cluster
# MAGIC SELECT * FROM workspace.aura.v_genetic_top_genes
# MAGIC WHERE rank <= 5
# MAGIC ORDER BY diagnosis_cluster, rank;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Training dataset sizes
# MAGIC SELECT 'binary' AS dataset, COUNT(*) AS rows,
# MAGIC        SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END) AS positive,
# MAGIC        SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END) AS negative
# MAGIC FROM workspace.aura.v_training_binary
# MAGIC UNION ALL
# MAGIC SELECT 'multiclass', COUNT(*), NULL, NULL
# MAGIC FROM workspace.aura.v_training_multiclass;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Usage from Other Notebooks
# MAGIC
# MAGIC To use these views and helpers from any other Databricks notebook:
# MAGIC
# MAGIC **Option A: SQL views are always available** (no setup needed):
# MAGIC ```sql
# MAGIC -- Just query the views directly
# MAGIC SELECT * FROM workspace.aura.v_training_binary LIMIT 10;
# MAGIC SELECT * FROM workspace.aura.v_patient_abnormal_flags WHERE patient_id = 'harvard_00001';
# MAGIC SELECT * FROM workspace.aura.v_cluster_summary;
# MAGIC ```
# MAGIC
# MAGIC **Option B: Python helpers** (run this notebook first):
# MAGIC ```python
# MAGIC %run /Workspace/path/to/aura_data
# MAGIC
# MAGIC # Then use the helpers
# MAGIC df = aura('core_matrix')
# MAGIC lupus = filter_core(cluster='systemic', source='harvard')
# MAGIC flag_abnormal('harvard_00001').show()
# MAGIC reference_range(35, 'M', marker='wbc').show()
# MAGIC disease_to_cluster('Lupus')  # returns 'systemic'
# MAGIC ```
# MAGIC
# MAGIC **Available SQL views:**
# MAGIC | View | Description |
# MAGIC |------|-------------|
# MAGIC | `v_catalog` | Table inventory with row counts |
# MAGIC | `v_core_with_autoantibodies` | core_matrix + autoantibody panel (left join) |
# MAGIC | `v_training_binary` | Binary classification features (autoimmune vs healthy) |
# MAGIC | `v_training_multiclass` | Multiclass cluster prediction features |
# MAGIC | `v_patient_abnormal_flags` | Lab values flagged against healthy baselines |
# MAGIC | `v_cluster_summary` | Per-cluster average labs and patient counts |
# MAGIC | `v_genetic_top_genes` | Top 25 GWAS genes per diagnosis cluster |
