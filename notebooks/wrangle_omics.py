# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle Omics Data (Phase 4)
# MAGIC
# MAGIC Processes transcriptomics, microbiome, proteomics, and metabolomics datasets
# MAGIC from Databricks Volume into Tier 2 extension tables.
# MAGIC
# MAGIC **Produces:**
# MAGIC - `transcriptomics_signatures` (ADEx + IAAA gene expression signatures)
# MAGIC - `microbiome_profiles` (HMP + IBDMDB gut microbiome)
# MAGIC - `proteomics_associations` (Olink/UKB-PPP protein-disease associations)
# MAGIC - `metabolomics_associations` (HMDB + MetaboLights metabolite-disease data)
# MAGIC
# MAGIC **Raw data:** `/Volumes/workspace/aura/aura_data/raw/`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import re
import logging

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_omics")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_ADEX = os.path.join(VOLUME_ROOT, "raw", "adex")
RAW_IAAA = os.path.join(VOLUME_ROOT, "raw", "iaaa")
RAW_HMP = os.path.join(VOLUME_ROOT, "raw", "hmp")
RAW_OLINK = os.path.join(VOLUME_ROOT, "raw", "olink")
RAW_HMDB = os.path.join(VOLUME_ROOT, "raw", "hmdb")
RAW_METABOLIGHTS = os.path.join(VOLUME_ROOT, "raw", "metabolights")

AUTOIMMUNE_KEYWORDS = [
    "rheumatoid arthritis", "systemic lupus", "lupus", "sle",
    "crohn", "ulcerative colitis", "inflammatory bowel", "ibd", "celiac",
    "type 1 diabetes", "hashimoto", "graves", "thyroiditis",
    "multiple sclerosis", "psoriasis", "vitiligo", "alopecia areata",
    "ankylosing spondylitis", "sjogren", "scleroderma", "vasculitis",
    "myasthenia gravis", "pemphigus", "autoimmune", "dermatomyositis",
]

TRAIT_TO_CLUSTER = {
    "rheumatoid arthritis": "systemic",
    "systemic lupus erythematosus": "systemic",
    "lupus": "systemic",
    "ankylosing spondylitis": "systemic",
    "sjogren": "systemic",
    "scleroderma": "systemic",
    "vasculitis": "systemic",
    "psoriatic arthritis": "systemic",
    "crohn's disease": "gastrointestinal",
    "crohn disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "inflammatory bowel disease": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "type 1 diabetes": "endocrine",
    "hashimoto": "endocrine",
    "thyroiditis": "endocrine",
    "graves' disease": "endocrine",
    "graves disease": "endocrine",
    "multiple sclerosis": "neurological",
    "psoriasis": "dermatological",
    "vitiligo": "dermatological",
    "alopecia areata": "dermatological",
}


def map_disease_to_cluster(disease_str):
    """Map a disease name to Aura cluster using keyword matching."""
    if not disease_str or pd.isna(disease_str):
        return "other_autoimmune"
    d_lower = str(disease_str).lower().strip()
    for keyword, cluster in TRAIT_TO_CLUSTER.items():
        if keyword in d_lower:
            return cluster
    return "other_autoimmune"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Transcriptomics Signatures (ADEx + IAAA)
# MAGIC
# MAGIC GEO series matrix files contain gene expression data. We extract
# MAGIC study-level metadata and sample characteristics to build disease-level
# MAGIC gene expression signatures.
# MAGIC
# MAGIC **ADEx files:** 5 GEO series matrices (GSE15573, GSE45291, GSE50772, GSE51092, GSE65391)
# MAGIC **IAAA file:** 1 GEO series matrix (GSE87095)

# COMMAND ----------

def parse_geo_series_matrix(filepath):
    """
    Parse a GEO series matrix file to extract study metadata and expression data.
    Returns (metadata_dict, expression_df) or (metadata_dict, None) if parsing fails.
    """
    metadata = {}
    data_lines = []
    in_data = False

    try:
        import gzip
        opener = gzip.open if filepath.endswith(".gz") else open
        with opener(filepath, "rt", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("!Series_"):
                    key = line.split("\t")[0].replace("!Series_", "")
                    val = "\t".join(line.split("\t")[1:]).strip('"')
                    metadata[key] = val
                elif line.startswith("!Sample_"):
                    key = line.split("\t")[0].replace("!", "")
                    vals = [v.strip('"') for v in line.split("\t")[1:]]
                    if key not in metadata:
                        metadata[key] = vals
                    else:
                        if isinstance(metadata[key], list):
                            pass  # Already stored
                elif line == "!series_matrix_table_begin":
                    in_data = True
                    continue
                elif line == "!series_matrix_table_end":
                    in_data = False
                elif in_data:
                    data_lines.append(line)
    except Exception as e:
        logger.error("Failed to parse %s: %s", filepath, e)
        return metadata, None

    if data_lines:
        try:
            import io
            expr_df = pd.read_csv(io.StringIO("\n".join(data_lines)), sep="\t", index_col=0)
            return metadata, expr_df
        except Exception as e:
            logger.warning("Failed to parse expression matrix from %s: %s", filepath, e)

    return metadata, None


def wrangle_transcriptomics():
    """Extract transcriptomics signatures from ADEx and IAAA GEO matrices."""
    dest = os.path.join(VOLUME_ROOT, "tier2_transcriptomics_signatures.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    all_signatures = []

    # Process ADEx files
    adex_files = sorted([f for f in os.listdir(RAW_ADEX) if f.endswith(".txt.gz")])
    logger.info("ADEx GEO files found: %s", adex_files)

    for geo_file in adex_files:
        geo_path = os.path.join(RAW_ADEX, geo_file)
        study_id = geo_file.split("_")[0]
        logger.info("Processing ADEx %s...", study_id)

        metadata, expr_df = parse_geo_series_matrix(geo_path)
        disease = metadata.get("title", "Unknown")

        if expr_df is not None and not expr_df.empty:
            n_genes = len(expr_df)
            n_samples = len(expr_df.columns)

            # Compute per-gene summary statistics across samples
            gene_stats = pd.DataFrame({
                "gene_symbol": expr_df.index,
                "mean_expression": expr_df.mean(axis=1).values,
                "std_expression": expr_df.std(axis=1).values,
                "median_expression": expr_df.median(axis=1).values,
            })
            gene_stats["source"] = "adex"
            gene_stats["study_id"] = study_id
            gene_stats["disease"] = disease
            gene_stats["diagnosis_cluster"] = map_disease_to_cluster(disease)
            gene_stats["sample_type"] = "expression"
            gene_stats["platform"] = metadata.get("platform_id", "unknown")
            gene_stats["n_samples"] = n_samples

            all_signatures.append(gene_stats)
            logger.info("  %s: %d genes x %d samples", study_id, n_genes, n_samples)
        else:
            # Still record study metadata even without expression matrix
            all_signatures.append(pd.DataFrame([{
                "source": "adex",
                "study_id": study_id,
                "disease": disease,
                "diagnosis_cluster": map_disease_to_cluster(disease),
                "sample_type": "expression",
                "gene_symbol": None,
                "mean_expression": None,
                "std_expression": None,
                "median_expression": None,
                "platform": metadata.get("platform_id", "unknown"),
                "n_samples": 0,
            }]))
            logger.info("  %s: metadata only (no expression matrix)", study_id)

    # Process IAAA files
    iaaa_files = sorted([f for f in os.listdir(RAW_IAAA) if f.endswith(".txt.gz")])
    logger.info("IAAA GEO files found: %s", iaaa_files)

    for geo_file in iaaa_files:
        geo_path = os.path.join(RAW_IAAA, geo_file)
        study_id = geo_file.split("_")[0]
        logger.info("Processing IAAA %s...", study_id)

        metadata, expr_df = parse_geo_series_matrix(geo_path)
        disease = metadata.get("title", "Unknown")

        if expr_df is not None and not expr_df.empty:
            n_genes = len(expr_df)
            n_samples = len(expr_df.columns)

            gene_stats = pd.DataFrame({
                "gene_symbol": expr_df.index,
                "mean_expression": expr_df.mean(axis=1).values,
                "std_expression": expr_df.std(axis=1).values,
                "median_expression": expr_df.median(axis=1).values,
            })
            gene_stats["source"] = "iaaa"
            gene_stats["study_id"] = study_id
            gene_stats["disease"] = disease
            gene_stats["diagnosis_cluster"] = map_disease_to_cluster(disease)
            gene_stats["sample_type"] = "expression"
            gene_stats["platform"] = metadata.get("platform_id", "unknown")
            gene_stats["n_samples"] = n_samples

            all_signatures.append(gene_stats)
            logger.info("  %s: %d genes x %d samples", study_id, n_genes, n_samples)

    if not all_signatures:
        logger.warning("No transcriptomics data processed.")
        return None

    result = pd.concat(all_signatures, ignore_index=True)
    result = result.dropna(subset=["gene_symbol"])

    result.to_parquet(dest, index=False)
    logger.info("Saved transcriptomics_signatures: %d rows -> %s", len(result), dest)
    logger.info("  Studies: %s", result["study_id"].unique().tolist())
    return result


transcriptomics_df = wrangle_transcriptomics()
if transcriptomics_df is not None:
    print(f"Transcriptomics: {len(transcriptomics_df)} rows")
    print(transcriptomics_df.groupby("study_id").size())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Microbiome Profiles (HMP + IBDMDB)
# MAGIC
# MAGIC The HMP data includes IBDMDB taxonomic profiles with diagnosis labels
# MAGIC (CD, UC, nonIBD) and full taxonomic hierarchy from kingdom to species.

# COMMAND ----------

def wrangle_microbiome():
    """Extract gut microbiome profiles from HMP/IBDMDB data."""
    dest = os.path.join(VOLUME_ROOT, "tier2_microbiome_profiles.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    # Load IBDMDB taxonomic profiles (has diagnosis labels)
    tax_path = os.path.join(RAW_HMP, "ibdmdb_taxonomic_profiles_week0.csv")
    if not os.path.exists(tax_path):
        logger.error("IBDMDB taxonomic file not found: %s", tax_path)
        return None

    try:
        df = pd.read_csv(tax_path)
    except Exception as e:
        logger.error("Failed to read IBDMDB taxonomic profiles: %s", e)
        return None

    logger.info("IBDMDB taxonomic raw: %d rows x %d cols", len(df), len(df.columns))

    # Metadata columns vs taxon columns
    meta_cols = ["site_name", "sex", "race", "consent_age", "diagnosis"]
    taxon_cols = [c for c in df.columns if c.startswith("k__")]
    logger.info("  Metadata cols: %s", meta_cols)
    logger.info("  Taxon columns: %d", len(taxon_cols))

    # Filter to species-level taxon columns (contain |s__)
    species_cols = [c for c in taxon_cols if "|s__" in c and "|t__" not in c]
    logger.info("  Species-level columns: %d", len(species_cols))

    # Melt to long format
    if not species_cols:
        # Fall back to genus level
        species_cols = [c for c in taxon_cols if "|g__" in c and "|s__" not in c]
        logger.info("  Falling back to genus-level: %d columns", len(species_cols))

    if not species_cols:
        logger.warning("No species or genus taxon columns found.")
        return None

    # Extract species name from full taxonomy path
    def extract_taxon_name(taxon_path):
        """Extract the lowest-level taxon name from a full path."""
        parts = taxon_path.split("|")
        return parts[-1] if parts else taxon_path

    id_vars = [c for c in meta_cols if c in df.columns]
    df["sample_id"] = df.index.astype(str)
    id_vars.append("sample_id")

    long_df = df[id_vars + species_cols].melt(
        id_vars=id_vars,
        var_name="taxon_path",
        value_name="relative_abundance",
    )

    long_df["taxon_name"] = long_df["taxon_path"].apply(extract_taxon_name)

    # Determine taxon level from the path
    def get_taxon_level(path):
        if "|s__" in path:
            return "species"
        elif "|g__" in path:
            return "genus"
        elif "|f__" in path:
            return "family"
        elif "|o__" in path:
            return "order"
        elif "|c__" in path:
            return "class"
        elif "|p__" in path:
            return "phylum"
        return "kingdom"

    long_df["taxon_level"] = long_df["taxon_path"].apply(get_taxon_level)

    # Drop zero-abundance entries
    long_df = long_df[long_df["relative_abundance"] > 0].copy()

    # Map diagnosis to Aura cluster
    diagnosis_map = {
        "CD": "gastrointestinal",
        "UC": "gastrointestinal",
        "nonIBD": "healthy",
    }
    long_df["diagnosis_cluster"] = long_df.get("diagnosis", pd.Series()).map(diagnosis_map)
    long_df["source"] = "hmp_ibdmdb"
    long_df["body_site"] = "stool"
    long_df["sequencing_method"] = "16S"

    # Select final columns
    result = long_df[[
        "source", "sample_id", "body_site", "diagnosis",
        "diagnosis_cluster", "taxon_level", "taxon_name",
        "relative_abundance", "sequencing_method",
    ]].copy()

    result.to_parquet(dest, index=False)
    logger.info("Saved microbiome_profiles: %d rows -> %s", len(result), dest)
    logger.info("  Diagnoses: %s", result["diagnosis"].value_counts().to_dict())
    return result


microbiome_df = wrangle_microbiome()
if microbiome_df is not None:
    print(f"Microbiome: {len(microbiome_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Proteomics Associations (Olink/UKB-PPP)
# MAGIC
# MAGIC The Olink file is an xlsx with protein-QTL associations from the
# MAGIC UK Biobank Pharma Proteomics Project.

# COMMAND ----------

def wrangle_proteomics():
    """Extract proteomics associations from Olink/UKB-PPP data."""
    dest = os.path.join(VOLUME_ROOT, "tier2_proteomics_associations.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    xlsx_path = os.path.join(RAW_OLINK, "ukb_ppp_pqtl_summary.xlsx")
    if not os.path.exists(xlsx_path):
        logger.error("Olink file not found: %s", xlsx_path)
        return None

    try:
        # Try reading the first sheet
        df = pd.read_excel(xlsx_path, engine="openpyxl")
    except Exception as e:
        logger.error("Failed to read Olink xlsx: %s", e)
        try:
            # Try with different engine or sheet
            xls = pd.ExcelFile(xlsx_path, engine="openpyxl")
            logger.info("  Available sheets: %s", xls.sheet_names)
            df = pd.read_excel(xls, sheet_name=0)
        except Exception as e2:
            logger.error("Second attempt failed: %s", e2)
            return None

    logger.info("Olink raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Columns: %s", list(df.columns))

    # Standardize column names
    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]

    # Add source and cluster mapping
    df["source"] = "olink_ukbppp"

    # Try to identify disease/trait column and map to clusters
    trait_col = None
    for candidate in ["trait", "disease", "phenotype", "outcome"]:
        if candidate in df.columns:
            trait_col = candidate
            break

    if trait_col:
        df["diagnosis_cluster"] = df[trait_col].apply(map_disease_to_cluster)
    else:
        df["diagnosis_cluster"] = "other_autoimmune"

    df.to_parquet(dest, index=False)
    logger.info("Saved proteomics_associations: %d rows -> %s", len(df), dest)
    return df


proteomics_df = wrangle_proteomics()
if proteomics_df is not None:
    print(f"Proteomics: {len(proteomics_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Metabolomics Associations (HMDB + MetaboLights)
# MAGIC
# MAGIC HMDB provides serum metabolome concentration data.
# MAGIC MetaboLights provides a study index.

# COMMAND ----------

def wrangle_metabolomics():
    """Extract metabolomics data from HMDB and MetaboLights."""
    dest = os.path.join(VOLUME_ROOT, "tier2_metabolomics_associations.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    all_frames = []

    # HMDB serum metabolome
    hmdb_path = os.path.join(RAW_HMDB, "serum_metabolome_concentrations.csv")
    if os.path.exists(hmdb_path):
        try:
            # Try different delimiters and encodings
            hmdb_df = None
            for sep in [",", "\t", ";"]:
                try:
                    hmdb_df = pd.read_csv(hmdb_path, sep=sep, nrows=5)
                    if len(hmdb_df.columns) > 1:
                        hmdb_df = pd.read_csv(hmdb_path, sep=sep)
                        break
                except Exception:
                    continue

            if hmdb_df is not None and len(hmdb_df.columns) > 1:
                logger.info("HMDB raw: %d rows x %d cols", len(hmdb_df), len(hmdb_df.columns))
                logger.info("  Columns: %s", list(hmdb_df.columns)[:15])
                hmdb_df["source"] = "hmdb"
                all_frames.append(hmdb_df)
            else:
                logger.warning("HMDB file has unexpected format (single column). Skipping.")
        except Exception as e:
            logger.error("Failed to read HMDB CSV: %s", e)
    else:
        logger.warning("HMDB file not found: %s", hmdb_path)

    # MetaboLights study index
    ml_path = os.path.join(RAW_METABOLIGHTS, "metabolights_study_index.parquet")
    if os.path.exists(ml_path):
        try:
            ml_df = pd.read_parquet(ml_path)
            logger.info("MetaboLights raw: %d rows x %d cols", len(ml_df), len(ml_df.columns))

            # Filter to autoimmune-related studies
            if "title" in ml_df.columns:
                mask = ml_df["title"].str.lower().str.contains(
                    "|".join(AUTOIMMUNE_KEYWORDS), na=False
                )
                if "description" in ml_df.columns:
                    mask = mask | ml_df["description"].str.lower().str.contains(
                        "|".join(AUTOIMMUNE_KEYWORDS), na=False
                    )
                ml_filtered = ml_df[mask].copy()
                logger.info("MetaboLights filtered: %d -> %d autoimmune studies",
                            len(ml_df), len(ml_filtered))
            else:
                ml_filtered = ml_df.copy()

            if not ml_filtered.empty:
                ml_filtered["source"] = "metabolights"
                all_frames.append(ml_filtered)
        except Exception as e:
            logger.error("Failed to read MetaboLights parquet: %s", e)
    else:
        logger.warning("MetaboLights file not found: %s", ml_path)

    if not all_frames:
        logger.warning("No metabolomics data processed.")
        return None

    # Combine and add cluster mapping
    result = pd.concat(all_frames, ignore_index=True)

    # Try to map diseases if a disease/trait column exists
    for col in result.columns:
        if any(kw in col.lower() for kw in ["disease", "trait", "condition"]):
            result["diagnosis_cluster"] = result[col].apply(map_disease_to_cluster)
            break
    else:
        result["diagnosis_cluster"] = "other_autoimmune"

    result.to_parquet(dest, index=False)
    logger.info("Saved metabolomics_associations: %d rows -> %s", len(result), dest)
    return result


metabolomics_df = wrangle_metabolomics()
if metabolomics_df is not None:
    print(f"Metabolomics: {len(metabolomics_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Register New Tables

# COMMAND ----------

# Register only tables whose parquet files were successfully created
tables_to_register = {
    "transcriptomics_signatures": "tier2_transcriptomics_signatures.parquet",
    "microbiome_profiles": "tier2_microbiome_profiles.parquet",
    "proteomics_associations": "tier2_proteomics_associations.parquet",
    "metabolomics_associations": "tier2_metabolomics_associations.parquet",
}

for table_name, parquet_file in tables_to_register.items():
    parquet_path = os.path.join(VOLUME_ROOT, parquet_file)
    if os.path.exists(parquet_path):
        logger.info("Registering %s from %s", table_name, parquet_path)
        spark.sql(f"""
            CREATE OR REPLACE TABLE workspace.aura.{table_name}
            AS SELECT * FROM parquet.`{parquet_path}`
        """)
        logger.info("  Registered workspace.aura.%s", table_name)
    else:
        logger.warning("SKIP registration: %s not found (data source may be unavailable)", parquet_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verification

# COMMAND ----------

# Verify registered tables
for table_name in tables_to_register:
    try:
        count_df = spark.sql(f"SELECT COUNT(*) as rows FROM workspace.aura.{table_name}")
        row_count = count_df.collect()[0][0]
        logger.info("  workspace.aura.%s: %d rows", table_name, row_count)
    except Exception as e:
        logger.warning("  workspace.aura.%s: not available (%s)", table_name, e)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `transcriptomics_signatures` | 2 | ADEx + IAAA | Per-gene expression stats from 6 GEO studies |
# MAGIC | `microbiome_profiles` | 2 | HMP/IBDMDB | Gut taxonomic profiles (CD, UC, nonIBD) |
# MAGIC | `proteomics_associations` | 2 | Olink/UKB-PPP | Protein-QTL summary statistics |
# MAGIC | `metabolomics_associations` | 2 | HMDB + MetaboLights | Metabolite concentrations + study index |
