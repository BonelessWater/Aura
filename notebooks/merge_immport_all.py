# Databricks notebook source
# MAGIC %md
# MAGIC # Merge All ImmPort Studies into Aura Data Lake
# MAGIC Adds 676 patients from 14 ImmPort autoimmune clinical trials to:
# MAGIC - Tier 1: core_matrix (baseline CBC + demographics + diagnoses)
# MAGIC - Tier 2: autoantibody_panel (ANA, anti-dsDNA, RF, anti-CCP, C3/C4, anti-Ro/La)
# MAGIC - Tier 2: longitudinal_labs (all-timepoint lab measurements)
# MAGIC
# MAGIC Studies: SDY91 (Vasculitis), SDY471/547/661 (MS), SDY473/824 (RA),
# MAGIC SDY474/625 (SLE), SDY568/569 (T1D), SDY655 (Pemphigus),
# MAGIC SDY823/961 (Sjogren's), SDY3216 (Systemic Sclerosis)

# COMMAND ----------

from pyspark.sql.functions import lit, col

volume = "/Volumes/workspace/aura/aura_data"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Merge into core_matrix

# COMMAND ----------

# Read from Unity Catalog table (parquet on volume may be corrupted by partial writes)
existing_core = spark.table("workspace.aura.core_matrix")
immport_core = spark.read.parquet(f"{volume}/immport_all_core.parquet")

print(f"Existing core_matrix: {existing_core.count()} rows")
print(f"ImmPort new rows: {immport_core.count()} rows")

existing_sources = [r.source for r in existing_core.select("source").distinct().collect()]
print(f"Existing sources: {existing_sources}")

# COMMAND ----------

# Remove any previously merged immport rows (idempotent re-run)
existing_core_clean = existing_core.filter(~col("source").startswith("immport_"))
removed = existing_core.count() - existing_core_clean.count()
if removed > 0:
    print(f"Removed {removed} previously merged immport rows for clean re-merge")

merged_core = existing_core_clean.unionByName(immport_core, allowMissingColumns=True)
print(f"Merged core_matrix: {merged_core.count()} rows")

merged_core.createOrReplaceTempView("_merged_core")

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.core_matrix
# MAGIC AS SELECT * FROM _merged_core;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Merge into autoantibody_panel

# COMMAND ----------

existing_ab = spark.table("workspace.aura.autoantibody_panel")
immport_ab = spark.read.parquet(f"{volume}/immport_all_autoantibody.parquet")

print(f"Existing autoantibody_panel: {existing_ab.count()} rows")
print(f"ImmPort autoantibody rows: {immport_ab.count()} rows")

existing_ab_clean = existing_ab.filter(~col("patient_id").startswith("immport_"))
merged_ab = existing_ab_clean.unionByName(immport_ab, allowMissingColumns=True)
print(f"Merged autoantibody_panel: {merged_ab.count()} rows")

merged_ab.createOrReplaceTempView("_merged_ab")

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.autoantibody_panel
# MAGIC AS SELECT * FROM _merged_ab;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Merge into longitudinal_labs

# COMMAND ----------

existing_long = spark.table("workspace.aura.longitudinal_labs")
immport_long = spark.read.parquet(f"{volume}/immport_all_longitudinal.parquet")

print(f"Existing longitudinal_labs: {existing_long.count()} rows")
print(f"ImmPort longitudinal rows: {immport_long.count()} rows")

existing_long_clean = existing_long.filter(~col("source").startswith("immport_"))
merged_long = existing_long_clean.unionByName(immport_long, allowMissingColumns=True)
print(f"Merged longitudinal_labs: {merged_long.count()} rows")

merged_long.createOrReplaceTempView("_merged_long")

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.longitudinal_labs
# MAGIC AS SELECT * FROM _merged_long;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT source, diagnosis_cluster, COUNT(*) as rows
# MAGIC FROM workspace.aura.core_matrix
# MAGIC GROUP BY source, diagnosis_cluster
# MAGIC ORDER BY rows DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Summary counts
# MAGIC SELECT 'core_matrix' as tbl, COUNT(*) as rows FROM workspace.aura.core_matrix
# MAGIC UNION ALL
# MAGIC SELECT 'autoantibody_panel', COUNT(*) FROM workspace.aura.autoantibody_panel
# MAGIC UNION ALL
# MAGIC SELECT 'longitudinal_labs', COUNT(*) FROM workspace.aura.longitudinal_labs;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Diagnosis cluster distribution
# MAGIC SELECT diagnosis_cluster, COUNT(*) as patients,
# MAGIC        AVG(wbc) as avg_wbc, AVG(hemoglobin) as avg_hgb, AVG(crp) as avg_crp
# MAGIC FROM workspace.aura.core_matrix
# MAGIC GROUP BY diagnosis_cluster
# MAGIC ORDER BY patients DESC;

# COMMAND ----------

print("ImmPort merge complete - 14 studies, 676 new patients")
dbutils.notebook.exit("IMMPORT_ALL_MERGE_COMPLETE")
