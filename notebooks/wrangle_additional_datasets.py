# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle Additional Datasets
# MAGIC
# MAGIC Processes the FinnGen, GWAS, and ImmPort data downloaded by
# MAGIC `download_additional_datasets` into Aura's tiered table structure.
# MAGIC
# MAGIC **Produces:**
# MAGIC - Tier 2: `genetic_risk_scores` (FinnGen + GWAS loci)
# MAGIC - Tier 3: Updated `healthy_baselines` (with ImmPort 10KIP data)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_additional")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_FINNGEN = os.path.join(VOLUME_ROOT, "raw", "finngen")
RAW_GWAS = os.path.join(VOLUME_ROOT, "raw", "gwas")
RAW_IMMPORT = os.path.join(VOLUME_ROOT, "raw", "immport")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. FinnGen R12: Extract Top GWAS Hits
# MAGIC
# MAGIC Each FinnGen summary stats file contains millions of variants.
# MAGIC We extract only genome-wide significant hits (p < 5e-8) and map them
# MAGIC to autoimmune disease clusters.

# COMMAND ----------

FINNGEN_CLUSTER_MAP = {
    "M13_RHEUMA": ("rheumatological", "M06.9"),
    "SLE_FG": ("rheumatological", "M32.9"),
    "K11_IBD_STRICT": ("gastrointestinal", "K50.9"),
    "E4_THYROIDITAUTOIM": ("endocrine", "E06.3"),
    "L12_PSORIASIS": ("dermatological", "L40.9"),
}

GWAS_SIGNIFICANCE = 5e-8


def wrangle_finngen():
    """Extract genome-wide significant hits from FinnGen summary stats."""
    all_hits = []

    for endpoint, (cluster, icd10) in FINNGEN_CLUSTER_MAP.items():
        gz_path = os.path.join(RAW_FINNGEN, f"finngen_R12_{endpoint}.gz")
        if not os.path.exists(gz_path):
            logger.warning("FinnGen file not found: %s", gz_path)
            continue

        logger.info("Processing FinnGen %s (%s)...", endpoint, cluster)
        try:
            # FinnGen summary stats are tab-separated gzipped files
            # Columns: chrom, pos, ref, alt, rsids, nearest_genes,
            #          pval, mlogp, beta, sebeta, af_alt, af_alt_cases, af_alt_controls
            chunks = pd.read_csv(
                gz_path,
                sep="\t",
                compression="gzip",
                chunksize=500_000,
                dtype={"#chrom": str},
            )
            endpoint_hits = []
            for chunk in chunks:
                # Rename #chrom -> chrom if present
                if "#chrom" in chunk.columns:
                    chunk = chunk.rename(columns={"#chrom": "chrom"})

                # Filter to genome-wide significant
                if "pval" in chunk.columns:
                    sig = chunk[chunk["pval"] < GWAS_SIGNIFICANCE].copy()
                elif "mlogp" in chunk.columns:
                    # mlogp = -log10(p), so sig threshold = -log10(5e-8) ~ 7.3
                    sig = chunk[chunk["mlogp"] > 7.3].copy()
                else:
                    logger.warning("No p-value column found in %s", endpoint)
                    continue

                if len(sig) > 0:
                    endpoint_hits.append(sig)

            if endpoint_hits:
                df = pd.concat(endpoint_hits, ignore_index=True)
                df["finngen_endpoint"] = endpoint
                df["diagnosis_cluster"] = cluster
                df["diagnosis_icd10"] = icd10
                all_hits.append(df)
                logger.info("  %s: %d genome-wide significant hits", endpoint, len(df))
            else:
                logger.info("  %s: no genome-wide significant hits", endpoint)

        except Exception as e:
            logger.error("Failed to process %s: %s", endpoint, e)

    if all_hits:
        result = pd.concat(all_hits, ignore_index=True)
        logger.info("Total FinnGen significant hits: %d", len(result))
        return result
    else:
        logger.warning("No FinnGen data processed.")
        return pd.DataFrame()


finngen_df = wrangle_finngen()
if len(finngen_df) > 0:
    print(f"FinnGen hits: {len(finngen_df)}")
    print(finngen_df.groupby("finngen_endpoint").size())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. GWAS Portal: Process HugeAmp Associations

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


def wrangle_gwas():
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
    col_map = {}
    for col in df.columns:
        col_map[col] = col.lower().replace(" ", "_")
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


gwas_df = wrangle_gwas()
if len(gwas_df) > 0:
    print(f"GWAS associations: {len(gwas_df)}")
    print(gwas_df.head())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Build Genetic Risk Score Table (Tier 2)
# MAGIC
# MAGIC Combines FinnGen significant loci and GWAS portal associations
# MAGIC into a unified genetic risk score reference table.

# COMMAND ----------

def build_genetic_risk_scores(finngen_df, gwas_df):
    """Build a Tier 2 genetic risk score table from GWAS data.

    Combines FinnGen genome-wide significant hits with HugeAmp
    curated associations into a unified schema.
    """
    rows = []

    # FinnGen significant loci
    if len(finngen_df) > 0:
        for _, row in finngen_df.iterrows():
            gene = row.get("nearest_genes", "")
            rsid = row.get("rsids", "")
            rows.append({
                "source": "finngen_r12",
                "variant_id": rsid if rsid else f"{row.get('chrom', '')}:{row.get('pos', '')}",
                "gene": gene,
                "chrom": str(row.get("chrom", "")),
                "pos": row.get("pos", None),
                "ref": row.get("ref", ""),
                "alt": row.get("alt", ""),
                "pvalue": row.get("pval", None),
                "beta": row.get("beta", None),
                "se": row.get("sebeta", None),
                "af": row.get("af_alt", None),
                "finngen_endpoint": row.get("finngen_endpoint", ""),
                "diagnosis_cluster": row.get("diagnosis_cluster", ""),
                "diagnosis_icd10": row.get("diagnosis_icd10", ""),
            })

    # HugeAmp GWAS associations
    # After wrangle_gwas() lowercasing: varid, chromosome, position, pvalue,
    # beta, stderr, nearest (str), maf, reference, alt, queried_phenotype
    if len(gwas_df) > 0:
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

    if rows:
        df = pd.DataFrame(rows)
        dest = os.path.join(VOLUME_ROOT, "tier2_genetic_risk_scores.parquet")
        df.to_parquet(dest, index=False)
        logger.info("Saved genetic_risk_scores: %d rows -> %s", len(df), dest)
        return df
    else:
        logger.warning("No genetic risk data to save.")
        return pd.DataFrame()


grs_df = build_genetic_risk_scores(finngen_df, gwas_df)
if len(grs_df) > 0:
    print(f"\nGenetic Risk Scores table: {len(grs_df)} rows")
    print(grs_df.groupby("source").size())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Register New Table

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
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `genetic_risk_scores` | 2 | FinnGen + HugeAmp | GWAS significant loci for autoimmune conditions |
# MAGIC
# MAGIC Run the verification query above to confirm row counts.
