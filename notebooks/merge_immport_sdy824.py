# Databricks notebook source
# MAGIC %md
# MAGIC # Merge ImmPort SDY824 into Aura Data Lake
# MAGIC Adds 63 RA patients from ImmPort SDY824 (Anti-TNF Agents in RA) to:
# MAGIC - Tier 1: core_matrix
# MAGIC - Tier 2: autoantibody_panel
# MAGIC - Tier 2: longitudinal_labs

# COMMAND ----------

volume = "/Volumes/workspace/aura/aura_data"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Merge into core_matrix

# COMMAND ----------

existing_core = spark.read.parquet(f"{volume}/tier1_core_matrix.parquet")
sdy824_core = spark.read.parquet(f"{volume}/immport_sdy824_core.parquet")

print(f"Existing core_matrix: {existing_core.count()} rows")
print(f"SDY824 new rows: {sdy824_core.count()} rows")

# Check for duplicate sources
existing_sources = [r.source for r in existing_core.select("source").distinct().collect()]
print(f"Existing sources: {existing_sources}")

# COMMAND ----------

# Only merge if not already present
if "immport_sdy824" not in existing_sources:
    from pyspark.sql.functions import lit, col

    # Align columns: add missing columns as nulls in both directions
    existing_cols = set(existing_core.columns)
    new_cols = set(sdy824_core.columns)

    for c in new_cols - existing_cols:
        existing_core = existing_core.withColumn(c, lit(None).cast(sdy824_core.schema[c].dataType))
    for c in existing_cols - new_cols:
        sdy824_core = sdy824_core.withColumn(c, lit(None).cast(existing_core.schema[c].dataType))

    # Reorder columns to match
    sdy824_core = sdy824_core.select(existing_core.columns)

    merged_core = existing_core.unionByName(sdy824_core, allowMissingColumns=True)
    print(f"Merged core_matrix: {merged_core.count()} rows")

    # Save back
    merged_core.write.mode("overwrite").parquet(f"{volume}/tier1_core_matrix.parquet")
    print("Saved tier1_core_matrix.parquet")
else:
    print("immport_sdy824 already in core_matrix, skipping merge")
    merged_core = existing_core

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Merge into autoantibody_panel

# COMMAND ----------

existing_ab = spark.read.parquet(f"{volume}/tier2_autoantibody_panel.parquet")
sdy824_ab = spark.read.parquet(f"{volume}/immport_sdy824_autoantibody.parquet")

print(f"Existing autoantibody_panel: {existing_ab.count()} rows")
print(f"SDY824 autoantibody rows: {sdy824_ab.count()} rows")

# Check if already merged by looking for immport patient_ids
has_immport = existing_ab.filter(col("patient_id").startswith("immport_sdy824_")).count()
if has_immport == 0:
    from pyspark.sql.functions import lit

    for c in set(existing_ab.columns) - set(sdy824_ab.columns):
        sdy824_ab = sdy824_ab.withColumn(c, lit(None).cast(existing_ab.schema[c].dataType))
    for c in set(sdy824_ab.columns) - set(existing_ab.columns):
        existing_ab = existing_ab.withColumn(c, lit(None).cast(sdy824_ab.schema[c].dataType))

    merged_ab = existing_ab.unionByName(sdy824_ab, allowMissingColumns=True)
    print(f"Merged autoantibody_panel: {merged_ab.count()} rows")

    merged_ab.write.mode("overwrite").parquet(f"{volume}/tier2_autoantibody_panel.parquet")
    print("Saved tier2_autoantibody_panel.parquet")
else:
    print(f"SDY824 already in autoantibody_panel ({has_immport} rows), skipping")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Merge into longitudinal_labs

# COMMAND ----------

existing_long = spark.read.parquet(f"{volume}/tier2_longitudinal_labs.parquet")
sdy824_long = spark.read.parquet(f"{volume}/immport_sdy824_longitudinal.parquet")

print(f"Existing longitudinal_labs: {existing_long.count()} rows")
print(f"SDY824 longitudinal rows: {sdy824_long.count()} rows")

has_immport_long = existing_long.filter(col("patient_id").startswith("immport_sdy824_")).count()
if has_immport_long == 0:
    merged_long = existing_long.unionByName(sdy824_long, allowMissingColumns=True)
    print(f"Merged longitudinal_labs: {merged_long.count()} rows")

    merged_long.write.mode("overwrite").parquet(f"{volume}/tier2_longitudinal_labs.parquet")
    print("Saved tier2_longitudinal_labs.parquet")
else:
    print(f"SDY824 already in longitudinal_labs ({has_immport_long} rows), skipping")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Re-register tables in Unity Catalog

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.core_matrix
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier1_core_matrix.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.autoantibody_panel
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_autoantibody_panel.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.longitudinal_labs
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_longitudinal_labs.parquet`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT source, COUNT(*) as rows, COUNT(DISTINCT patient_id) as patients
# MAGIC FROM workspace.aura.core_matrix
# MAGIC GROUP BY source
# MAGIC ORDER BY rows DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Spot check SDY824 data
# MAGIC SELECT patient_id, age, sex, diagnosis_cluster, wbc, rbc, hemoglobin, crp, platelet_count
# MAGIC FROM workspace.aura.core_matrix
# MAGIC WHERE source = 'immport_sdy824'
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'core_matrix' as tbl, COUNT(*) as rows FROM workspace.aura.core_matrix
# MAGIC UNION ALL
# MAGIC SELECT 'autoantibody_panel', COUNT(*) FROM workspace.aura.autoantibody_panel
# MAGIC UNION ALL
# MAGIC SELECT 'longitudinal_labs', COUNT(*) FROM workspace.aura.longitudinal_labs;

# COMMAND ----------

print("SDY824 merge complete")
dbutils.notebook.exit("SDY824_MERGE_COMPLETE")
