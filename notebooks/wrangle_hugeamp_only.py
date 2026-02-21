# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle HugeAmp GWAS Data (Lightweight)
# MAGIC
# MAGIC Merges newly uploaded HugeAmp GWAS associations with the existing
# MAGIC FinnGen results already in `tier2_genetic_risk_scores.parquet`.
# MAGIC
# MAGIC **Skips** FinnGen re-processing (already done in a previous run).
# MAGIC
# MAGIC **Produces:**
# MAGIC - Updated `tier2_genetic_risk_scores.parquet` (FinnGen + HugeAmp)
# MAGIC - Re-registered `workspace.aura.genetic_risk_scores` table

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_hugeamp")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_GWAS = os.path.join(VOLUME_ROOT, "raw", "gwas")
EXISTING_GRS = os.path.join(VOLUME_ROOT, "tier2_genetic_risk_scores.parquet")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Existing FinnGen Results

# COMMAND ----------

if os.path.exists(EXISTING_GRS):
    existing_df = pd.read_parquet(EXISTING_GRS)
    logger.info("Loaded existing genetic_risk_scores: %d rows", len(existing_df))

    # Keep only FinnGen rows (drop any previous HugeAmp rows to avoid duplicates)
    finngen_df = existing_df[existing_df["source"] == "finngen_r12"].copy()
    logger.info("FinnGen rows retained: %d", len(finngen_df))
else:
    logger.warning("No existing tier2_genetic_risk_scores.parquet found; FinnGen will be empty")
    finngen_df = pd.DataFrame()

print(f"FinnGen rows from existing parquet: {len(finngen_df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Wrangle HugeAmp GWAS Associations

# COMMAND ----------

# Map HugeAmp phenotype codes to Aura clusters and ICD-10 codes
HUGEAMP_CLUSTER_MAP = {
    "T1D": ("endocrine", "E10"),
    "RhA": ("rheumatological", "M06.9"),
    "SLE": ("rheumatological", "M32.9"),
    "CD": ("gastrointestinal", "K50.9"),
    "UC": ("gastrointestinal", "K51.9"),
    "IBD": ("gastrointestinal", "K50.9"),
    "MultipleSclerosis": ("neurological", "G35"),
    "Psoriasis": ("dermatological", "L40.9"),
    "Celiac": ("gastrointestinal", "K90.0"),
    "Graves": ("endocrine", "E05.0"),
    "Vitiligo": ("dermatological", "L80"),
    "LADA": ("endocrine", "E10"),
    "Addison": ("endocrine", "E27.1"),
}


def wrangle_hugeamp():
    """Load and clean HugeAmp GWAS associations.

    HugeAmp API response fields (camelCase from API, lowercased here):
    varid, chromosome, position, pvalue, beta, stderr, phenotype,
    dbsnp, consequence, nearest (list of genes), maf, af (dict),
    reference, alt, queried_phenotype, queried_label
    """
    gwas_path = os.path.join(RAW_GWAS, "hugeamp_autoimmune_associations.parquet")
    if not os.path.exists(gwas_path):
        logger.warning("GWAS file not found: %s", gwas_path)
        return pd.DataFrame()

    df = pd.read_parquet(gwas_path)
    logger.info("Loaded %d GWAS associations from HugeAmp", len(df))

    # Standardize column names to lowercase
    col_map = {col: col.lower().replace(" ", "_") for col in df.columns}
    df = df.rename(columns=col_map)

    # Convert 'nearest' from list to comma-separated string
    if "nearest" in df.columns:
        df["nearest"] = df["nearest"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else str(x) if pd.notna(x) else ""
        )

    # Drop 'af' dict column (ancestry-specific); keep 'maf' (scalar) instead
    if "af" in df.columns:
        af_sample = df["af"].dropna().iloc[0] if len(df["af"].dropna()) > 0 else None
        if isinstance(af_sample, dict):
            logger.info("Dropping 'af' dict column; using 'maf' for allele frequency")
            df = df.drop(columns=["af"])

    return df


gwas_df = wrangle_hugeamp()
if len(gwas_df) > 0:
    print(f"HugeAmp associations loaded: {len(gwas_df)}")
    print(f"Columns: {list(gwas_df.columns)}")
    print(f"Phenotypes: {gwas_df['queried_phenotype'].value_counts().to_dict()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Build HugeAmp Rows and Merge

# COMMAND ----------

def build_hugeamp_rows(gwas_df):
    """Build standardized rows from wrangled HugeAmp data (lowercased columns)."""
    rows = []
    for _, row in gwas_df.iterrows():
        phenotype = row.get("queried_phenotype", "")
        cluster_info = HUGEAMP_CLUSTER_MAP.get(phenotype, ("", ""))
        rows.append({
            "source": "hugeamp",
            "variant_id": row.get("varid", row.get("dbsnp", "")),
            "gene": row.get("nearest", ""),
            "chrom": str(row.get("chromosome", "")),
            "pos": row.get("position", None),
            "ref": row.get("reference", ""),
            "alt": row.get("alt", ""),
            "pvalue": row.get("pvalue", None),
            "beta": row.get("beta", None),
            "se": row.get("stderr", None),
            "af": row.get("maf", None),
            "finngen_endpoint": "",
            "diagnosis_cluster": cluster_info[0],
            "diagnosis_icd10": cluster_info[1],
            "queried_phenotype": phenotype,
        })
    return rows


if len(gwas_df) > 0:
    hugeamp_rows = build_hugeamp_rows(gwas_df)
    hugeamp_df = pd.DataFrame(hugeamp_rows)
    logger.info("Built %d HugeAmp standardized rows", len(hugeamp_df))
else:
    hugeamp_df = pd.DataFrame()
    logger.warning("No HugeAmp data to process")

# Merge FinnGen + HugeAmp
# Add queried_phenotype column to FinnGen rows if missing (for schema compatibility)
if len(finngen_df) > 0 and "queried_phenotype" not in finngen_df.columns:
    finngen_df["queried_phenotype"] = ""

dfs_to_merge = [df for df in [finngen_df, hugeamp_df] if len(df) > 0]
if dfs_to_merge:
    merged_df = pd.concat(dfs_to_merge, ignore_index=True)
    dest = os.path.join(VOLUME_ROOT, "tier2_genetic_risk_scores.parquet")
    merged_df.to_parquet(dest, index=False)
    logger.info("Saved merged genetic_risk_scores: %d rows -> %s", len(merged_df), dest)
    print(f"\nMerged genetic_risk_scores: {len(merged_df)} rows")
    print(merged_df.groupby("source").size())
else:
    logger.warning("No data to merge")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Register Updated Table

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.genetic_risk_scores
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_genetic_risk_scores.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT source, COUNT(*) AS hit_count
# MAGIC FROM workspace.aura.genetic_risk_scores
# MAGIC GROUP BY source;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC This lightweight notebook:
# MAGIC 1. Read existing FinnGen rows from `tier2_genetic_risk_scores.parquet`
# MAGIC 2. Wrangled HugeAmp data (nearest list->string, af dict dropped, column mapping)
# MAGIC 3. Merged both sources into unified `genetic_risk_scores` table
# MAGIC
# MAGIC | Source | Expected Rows |
# MAGIC |--------|--------------|
# MAGIC | `finngen_r12` | ~67,869 |
# MAGIC | `hugeamp` | ~2,020 |
# MAGIC | **Total** | **~69,889** |
