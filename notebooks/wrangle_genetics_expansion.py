# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle Genetics Expansion (Phase 3)
# MAGIC
# MAGIC Processes genetic datasets from Databricks Volume into Tier 2 extension tables.
# MAGIC
# MAGIC **Produces:**
# MAGIC - `gwas_catalog_associations` (NHGRI-EBI curated autoimmune GWAS hits)
# MAGIC - `hla_frequencies` (AFND HLA allele-disease associations)
# MAGIC - `pan_ukbb_sumstats` (Pan-ancestry GWAS summary statistics)
# MAGIC - `immunobase_credible_sets` (Fine-mapped autoimmune loci)
# MAGIC
# MAGIC **Raw data location:** `/Volumes/workspace/aura/aura_data/raw/`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_genetics")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_GWAS_CATALOG = os.path.join(VOLUME_ROOT, "raw", "gwas_catalog")
RAW_AFND = os.path.join(VOLUME_ROOT, "raw", "afnd")
RAW_PAN_UKBB = os.path.join(VOLUME_ROOT, "raw", "pan_ukbb")
RAW_IMMUNOBASE = os.path.join(VOLUME_ROOT, "raw", "immunobase")

# Autoimmune trait keywords for filtering
AUTOIMMUNE_KEYWORDS = [
    "rheumatoid arthritis", "systemic lupus", "lupus", "sle",
    "crohn", "ulcerative colitis", "inflammatory bowel", "ibd", "celiac",
    "type 1 diabetes", "hashimoto", "graves", "thyroiditis",
    "multiple sclerosis", "psoriasis", "vitiligo", "alopecia areata",
    "ankylosing spondylitis", "sjogren", "scleroderma", "vasculitis",
    "myasthenia gravis", "pemphigus", "autoimmune", "dermatomyositis",
    "polymyositis", "addison", "primary biliary", "primary sclerosing",
]

# EFO ID to Aura cluster mapping for Open Targets / GWAS Catalog
TRAIT_TO_CLUSTER = {
    "rheumatoid arthritis": ("systemic", "M06.9"),
    "systemic lupus erythematosus": ("systemic", "M32.9"),
    "lupus": ("systemic", "M32.9"),
    "ankylosing spondylitis": ("systemic", "M45"),
    "sjogren": ("systemic", "M35.0"),
    "scleroderma": ("systemic", "M34.9"),
    "systemic sclerosis": ("systemic", "M34.9"),
    "vasculitis": ("systemic", "M31.9"),
    "dermatomyositis": ("systemic", "M33.9"),
    "polymyositis": ("systemic", "M33.2"),
    "psoriatic arthritis": ("systemic", "M07.3"),
    "crohn's disease": ("gastrointestinal", "K50.9"),
    "crohn disease": ("gastrointestinal", "K50.9"),
    "ulcerative colitis": ("gastrointestinal", "K51.9"),
    "inflammatory bowel disease": ("gastrointestinal", "K52.9"),
    "celiac disease": ("gastrointestinal", "K90.0"),
    "autoimmune hepatitis": ("gastrointestinal", "K75.4"),
    "primary biliary cholangitis": ("gastrointestinal", "K83.0"),
    "primary sclerosing cholangitis": ("gastrointestinal", "K83.0"),
    "type 1 diabetes": ("endocrine", "E10"),
    "hashimoto": ("endocrine", "E06.3"),
    "thyroiditis": ("endocrine", "E06.3"),
    "graves' disease": ("endocrine", "E05.0"),
    "graves disease": ("endocrine", "E05.0"),
    "addison's disease": ("endocrine", "E27.1"),
    "addison disease": ("endocrine", "E27.1"),
    "multiple sclerosis": ("neurological", "G35"),
    "myasthenia gravis": ("neurological", "G70.0"),
    "psoriasis": ("dermatological", "L40.9"),
    "vitiligo": ("dermatological", "L80"),
    "alopecia areata": ("dermatological", "L63.9"),
    "pemphigus": ("dermatological", "L10.0"),
    "autoimmune hemolytic anemia": ("haematological", "D59.1"),
    "immune thrombocytopenia": ("haematological", "D69.3"),
}


def map_trait_to_cluster(trait_str):
    """Map a trait string to (cluster, icd10) using keyword matching."""
    if not trait_str or pd.isna(trait_str):
        return ("other_autoimmune", None)
    trait_lower = str(trait_str).lower().strip()
    for keyword, (cluster, icd10) in TRAIT_TO_CLUSTER.items():
        if keyword in trait_lower:
            return (cluster, icd10)
    return ("other_autoimmune", None)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. GWAS Catalog Associations
# MAGIC
# MAGIC Source: NHGRI-EBI GWAS Catalog (pre-filtered for autoimmune traits).
# MAGIC 12,489 rows with trait-level GWAS summary data.

# COMMAND ----------

def wrangle_gwas_catalog():
    """Load and process GWAS Catalog autoimmune associations."""
    dest = os.path.join(VOLUME_ROOT, "tier2_gwas_catalog_associations.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    path = os.path.join(RAW_GWAS_CATALOG, "gwas_catalog_autoimmune.parquet")
    if not os.path.exists(path):
        logger.error("GWAS Catalog file not found: %s", path)
        return None

    df = pd.read_parquet(path)
    logger.info("GWAS Catalog raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Columns: %s", list(df.columns))

    # Map traits to Aura clusters
    cluster_icd = df["trait"].apply(map_trait_to_cluster)
    df["diagnosis_cluster"] = [c[0] for c in cluster_icd]
    df["diagnosis_icd10"] = [c[1] for c in cluster_icd]
    df["source"] = "gwas_catalog"

    # Rename columns to match spec
    col_rename = {
        "efo_id": "efo_id",
        "trait": "trait",
        "pvalue": "pvalue",
        "pvalue_mlog": "pvalue_mlog",
        "risk_allele_frequency": "risk_allele_frequency",
        "or_beta": "or_beta",
        "ci": "ci_95",
    }
    df = df.rename(columns=col_rename)

    # Deduplicate
    pre_dedup = len(df)
    df = df.drop_duplicates(subset=["efo_id", "trait", "pvalue", "or_beta"])
    logger.info("GWAS Catalog deduped: %d -> %d rows", pre_dedup, len(df))

    # Save
    df.to_parquet(dest, index=False)
    logger.info("Saved gwas_catalog_associations: %d rows -> %s", len(df), dest)
    logger.info("  Cluster distribution: %s", df["diagnosis_cluster"].value_counts().to_dict())
    return df


gwas_cat_df = wrangle_gwas_catalog()
if gwas_cat_df is not None:
    print(f"GWAS Catalog: {len(gwas_cat_df)} rows")
    print(gwas_cat_df["diagnosis_cluster"].value_counts())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. AFND HLA Frequencies
# MAGIC
# MAGIC Source: Allele Frequency Net Database. 11 HLA allele-disease associations
# MAGIC with population frequency metadata.

# COMMAND ----------

def wrangle_afnd():
    """Load and process AFND HLA allele-disease associations."""
    dest = os.path.join(VOLUME_ROOT, "tier2_hla_frequencies.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    path = os.path.join(RAW_AFND, "afnd_autoimmune_hla_metadata.parquet")
    if not os.path.exists(path):
        logger.error("AFND file not found: %s", path)
        return None

    df = pd.read_parquet(path)
    logger.info("AFND raw: %d rows x %d cols", len(df), len(df.columns))

    # Map disease associations to Aura clusters
    cluster_icd = df["disease_association"].apply(map_trait_to_cluster)
    df["diagnosis_cluster"] = [c[0] for c in cluster_icd]
    df["diagnosis_icd10"] = [c[1] for c in cluster_icd]
    df["source"] = "afnd"

    # Parse allele into locus and allele name
    df["hla_locus"] = df["locus"]
    df["n_populations"] = pd.to_numeric(df["n_populations"], errors="coerce")

    # Rename for clarity
    df = df.rename(columns={
        "disease_association": "associated_diseases",
        "allele": "allele",
        "frequencies_found": "frequencies_found",
    })

    # Save
    dest_path = dest
    df.to_parquet(dest_path, index=False)
    logger.info("Saved hla_frequencies: %d rows -> %s", len(df), dest_path)
    return df


afnd_df = wrangle_afnd()
if afnd_df is not None:
    print(f"AFND HLA: {len(afnd_df)} rows")
    print(afnd_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Pan-UK Biobank Summary Statistics
# MAGIC
# MAGIC Source: Pan-ancestry GWAS (bgzipped TSV). Currently only Type 1 Diabetes
# MAGIC phenotype available.

# COMMAND ----------

def wrangle_pan_ukbb():
    """Load and process Pan-UK Biobank summary statistics."""
    dest = os.path.join(VOLUME_ROOT, "tier2_pan_ukbb_sumstats.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    raw_dir = RAW_PAN_UKBB
    bgz_files = [f for f in os.listdir(raw_dir) if f.endswith(".tsv.bgz")]
    if not bgz_files:
        logger.error("No Pan-UKBB bgz files found in %s", raw_dir)
        return None

    all_frames = []
    for bgz_file in bgz_files:
        bgz_path = os.path.join(raw_dir, bgz_file)
        logger.info("Processing Pan-UKBB: %s", bgz_file)

        # Extract phenotype from filename (e.g., icd10-E10-both_sexes.tsv.bgz)
        parts = bgz_file.replace(".tsv.bgz", "").split("-")
        phenotype_code = "-".join(parts[1:-1]) if len(parts) > 2 else parts[0]
        sex_group = parts[-1] if len(parts) > 1 else "both_sexes"

        try:
            # Read bgzipped TSV in chunks to handle large files
            chunks = pd.read_csv(
                bgz_path,
                sep="\t",
                compression="gzip",
                chunksize=500_000,
            )
            file_hits = []
            pval_col_logged = False
            for chunk in chunks:
                # Detect p-value column (check multiple naming conventions)
                pval_col = None
                neglog_col = None
                for col in chunk.columns:
                    col_lower = col.lower()
                    if col_lower == "pval" or col_lower == "p_value" or col_lower == "pvalue":
                        pval_col = col
                        break
                    if "neglog10_pval" in col_lower and neglog_col is None:
                        neglog_col = col

                if pval_col is not None:
                    sig = chunk[chunk[pval_col] < 5e-8].copy()
                    if not pval_col_logged:
                        logger.info("  Using p-value column: %s", pval_col)
                        pval_col_logged = True
                elif neglog_col is not None:
                    sig = chunk[chunk[neglog_col] > 7.3].copy()
                    if not pval_col_logged:
                        logger.info("  Using neglog10 p-value column: %s", neglog_col)
                        pval_col_logged = True
                else:
                    if not pval_col_logged:
                        logger.warning("No recognized p-value column in %s. Columns: %s",
                                       bgz_file, list(chunk.columns))
                        logger.warning("Skipping file to avoid OOM.")
                        pval_col_logged = True
                    break

                if len(sig) > 0:
                    file_hits.append(sig)

            if file_hits:
                df = pd.concat(file_hits, ignore_index=True)
                df["phenotype_code"] = phenotype_code
                df["sex_group"] = sex_group
                df["source"] = "pan_ukbb"
                all_frames.append(df)
                logger.info("  %s: %d genome-wide significant hits", bgz_file, len(df))
            else:
                logger.info("  %s: no significant hits found", bgz_file)

        except Exception as e:
            logger.error("Failed to process %s: %s", bgz_file, e)

    if not all_frames:
        logger.warning("No Pan-UKBB data processed.")
        return None

    result = pd.concat(all_frames, ignore_index=True)

    # Map phenotype to Aura cluster
    pheno_to_cluster = {
        "E10": ("endocrine", "E10"),
        "M06": ("systemic", "M06.9"),
        "M32": ("systemic", "M32.9"),
        "K50": ("gastrointestinal", "K50.9"),
        "K51": ("gastrointestinal", "K51.9"),
        "G35": ("neurological", "G35"),
        "L40": ("dermatological", "L40.9"),
        "E06": ("endocrine", "E06.3"),
    }
    cluster_data = result["phenotype_code"].map(
        lambda x: pheno_to_cluster.get(x, ("other_autoimmune", None))
    )
    result["diagnosis_cluster"] = [c[0] for c in cluster_data]
    result["diagnosis_icd10"] = [c[1] for c in cluster_data]

    result.to_parquet(dest, index=False)
    logger.info("Saved pan_ukbb_sumstats: %d rows -> %s", len(result), dest)
    return result


pan_ukbb_df = wrangle_pan_ukbb()
if pan_ukbb_df is not None:
    print(f"Pan-UKBB: {len(pan_ukbb_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. ImmunoBase Credible Sets
# MAGIC
# MAGIC Source: ImmunoBase fine-mapping data. Contains GWAS study metadata
# MAGIC (gwas_catalog_studies.tsv) with autoimmune disease associations.

# COMMAND ----------

def wrangle_immunobase():
    """Load and process ImmunoBase GWAS study data."""
    dest = os.path.join(VOLUME_ROOT, "tier2_immunobase_credible_sets.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    studies_path = os.path.join(RAW_IMMUNOBASE, "gwas_catalog_studies.tsv")
    if not os.path.exists(studies_path):
        logger.error("ImmunoBase studies file not found: %s", studies_path)
        return None

    try:
        df = pd.read_csv(studies_path, sep="\t")
    except Exception as e:
        logger.error("Failed to read ImmunoBase studies: %s", e)
        return None

    logger.info("ImmunoBase raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Columns: %s", list(df.columns))

    # Filter to autoimmune-related traits
    trait_col = "DISEASE/TRAIT"
    if trait_col not in df.columns:
        for col in df.columns:
            if "trait" in col.lower() or "disease" in col.lower():
                trait_col = col
                break

    if trait_col in df.columns:
        mask = df[trait_col].str.lower().str.contains(
            "|".join(AUTOIMMUNE_KEYWORDS), na=False
        )
        df_filtered = df[mask].copy()
        logger.info("ImmunoBase filtered to autoimmune: %d -> %d rows", len(df), len(df_filtered))
    else:
        logger.warning("No trait column found, keeping all rows")
        df_filtered = df.copy()

    if df_filtered.empty:
        logger.warning("No autoimmune entries found in ImmunoBase data.")
        return None

    # Map traits to clusters
    cluster_icd = df_filtered[trait_col].apply(map_trait_to_cluster)
    df_filtered["diagnosis_cluster"] = [c[0] for c in cluster_icd]
    df_filtered["diagnosis_icd10"] = [c[1] for c in cluster_icd]
    df_filtered["source"] = "immunobase"

    # Standardize column names
    col_rename = {}
    for col in df_filtered.columns:
        col_rename[col] = col.lower().replace(" ", "_").replace("/", "_").replace("[", "").replace("]", "")
    df_filtered = df_filtered.rename(columns=col_rename)

    # Deduplicate on study + trait
    pre_dedup = len(df_filtered)
    dedup_cols = [c for c in ["pubmedid", "disease_trait"] if c in df_filtered.columns]
    if dedup_cols:
        df_filtered = df_filtered.drop_duplicates(subset=dedup_cols)
    logger.info("ImmunoBase deduped: %d -> %d rows", pre_dedup, len(df_filtered))

    df_filtered.to_parquet(dest, index=False)
    logger.info("Saved immunobase_credible_sets: %d rows -> %s", len(df_filtered), dest)
    return df_filtered


immunobase_df = wrangle_immunobase()
if immunobase_df is not None:
    print(f"ImmunoBase: {len(immunobase_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Register New Tables

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.gwas_catalog_associations
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_gwas_catalog_associations.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.hla_frequencies
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_hla_frequencies.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.pan_ukbb_sumstats
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_pan_ukbb_sumstats.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.immunobase_credible_sets
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier2_immunobase_credible_sets.parquet`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'gwas_catalog_associations' as tbl, COUNT(*) as rows FROM workspace.aura.gwas_catalog_associations
# MAGIC UNION ALL
# MAGIC SELECT 'hla_frequencies', COUNT(*) FROM workspace.aura.hla_frequencies
# MAGIC UNION ALL
# MAGIC SELECT 'pan_ukbb_sumstats', COUNT(*) FROM workspace.aura.pan_ukbb_sumstats
# MAGIC UNION ALL
# MAGIC SELECT 'immunobase_credible_sets', COUNT(*) FROM workspace.aura.immunobase_credible_sets;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `gwas_catalog_associations` | 2 | NHGRI-EBI | Curated autoimmune GWAS hits (12K+ associations) |
# MAGIC | `hla_frequencies` | 2 | AFND | HLA allele-disease associations |
# MAGIC | `pan_ukbb_sumstats` | 2 | Pan-UKBB | Pan-ancestry GWAS summary stats (T1D) |
# MAGIC | `immunobase_credible_sets` | 2 | ImmunoBase | Fine-mapped autoimmune loci |
