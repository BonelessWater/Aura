# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Register Data Lake Tables
# MAGIC Registers the uploaded Parquet files as tables in the `workspace.aura` schema.
# MAGIC
# MAGIC Uses `CREATE OR REPLACE TABLE ... AS SELECT` syntax which works with
# MAGIC managed Volumes on serverless compute.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 1: core_matrix (Harvard + NHANES + MIMIC)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.core_matrix
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier1_core_matrix.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 2: autoantibody_panel (12,085 rows)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.autoantibody_panel
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_autoantibody_panel.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 2: longitudinal_labs (19,646 entries from MIMIC Demo)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.longitudinal_labs
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_longitudinal_labs.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 2: genetic_risk_scores (67,869 GWAS hits from FinnGen R12)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.genetic_risk_scores
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_genetic_risk_scores.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 3: healthy_baselines (110 rows)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.healthy_baselines
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_healthy_baselines.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 3: icd_cluster_map (23 rows)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.icd_cluster_map
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_icd_cluster_map.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tier 3: drug_risk_index (597 rows)
# MAGIC CREATE OR REPLACE TABLE workspace.aura.drug_risk_index
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_drug_risk_index.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify all tables
# MAGIC SELECT 'core_matrix' AS table_name, COUNT(*) AS row_count FROM workspace.aura.core_matrix
# MAGIC UNION ALL
# MAGIC SELECT 'autoantibody_panel', COUNT(*) FROM workspace.aura.autoantibody_panel
# MAGIC UNION ALL
# MAGIC SELECT 'longitudinal_labs', COUNT(*) FROM workspace.aura.longitudinal_labs
# MAGIC UNION ALL
# MAGIC SELECT 'genetic_risk_scores', COUNT(*) FROM workspace.aura.genetic_risk_scores
# MAGIC UNION ALL
# MAGIC SELECT 'healthy_baselines', COUNT(*) FROM workspace.aura.healthy_baselines
# MAGIC UNION ALL
# MAGIC SELECT 'icd_cluster_map', COUNT(*) FROM workspace.aura.icd_cluster_map
# MAGIC UNION ALL
# MAGIC SELECT 'drug_risk_index', COUNT(*) FROM workspace.aura.drug_risk_index;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick Data Preview

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Preview core matrix by source and cluster
# MAGIC SELECT source, diagnosis_cluster, COUNT(*) as count
# MAGIC FROM workspace.aura.core_matrix
# MAGIC GROUP BY source, diagnosis_cluster
# MAGIC ORDER BY count DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Preview genetic risk scores by endpoint
# MAGIC SELECT finngen_endpoint, diagnosis_cluster, COUNT(*) as gwas_hits
# MAGIC FROM workspace.aura.genetic_risk_scores
# MAGIC GROUP BY finngen_endpoint, diagnosis_cluster
# MAGIC ORDER BY gwas_hits DESC;
