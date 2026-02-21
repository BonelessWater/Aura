# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Wrangle Reference Tables (Phase 4)
# MAGIC
# MAGIC Processes reference/lookup datasets into Tier 3 tables. These are static
# MAGIC tables queried at inference time to add environmental, molecular, and
# MAGIC protein context to patient predictions.
# MAGIC
# MAGIC **Produces:**
# MAGIC - `open_targets_associations` (drug-target-disease evidence from Open Targets)
# MAGIC - `ctd_chemical_disease` (chemical-disease interactions from CTD)
# MAGIC - `epa_air_quality_reference` (county-level annual pollutant data)
# MAGIC - `hpa_protein_expression` (protein expression atlas)
# MAGIC - `mendeley_lipidomics` (lipidomics validation data)
# MAGIC
# MAGIC **Raw data:** `/Volumes/workspace/aura/aura_data/raw/`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_wrangle_references")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_OPEN_TARGETS = os.path.join(VOLUME_ROOT, "raw", "open_targets")
RAW_CTD = os.path.join(VOLUME_ROOT, "raw", "ctd")
RAW_EPA = os.path.join(VOLUME_ROOT, "raw", "epa_aqs")
RAW_HPA = os.path.join(VOLUME_ROOT, "raw", "hpa")
RAW_MENDELEY = os.path.join(VOLUME_ROOT, "raw", "mendeley")

AUTOIMMUNE_KEYWORDS = [
    "rheumatoid arthritis", "systemic lupus", "lupus", "sle",
    "crohn", "ulcerative colitis", "inflammatory bowel", "ibd", "celiac",
    "type 1 diabetes", "hashimoto", "graves", "thyroiditis",
    "multiple sclerosis", "psoriasis", "vitiligo", "alopecia areata",
    "ankylosing spondylitis", "sjogren", "scleroderma", "vasculitis",
    "myasthenia gravis", "pemphigus", "autoimmune", "dermatomyositis",
    "primary biliary", "primary sclerosing", "addison",
]

DISEASE_TO_CLUSTER = {
    "systemic lupus erythematosus": "systemic",
    "rheumatoid arthritis": "systemic",
    "ankylosing spondylitis": "systemic",
    "sjogren syndrome": "systemic",
    "scleroderma": "systemic",
    "systemic sclerosis": "systemic",
    "vasculitis": "systemic",
    "psoriatic arthritis": "systemic",
    "dermatomyositis": "systemic",
    "crohn's disease": "gastrointestinal",
    "crohn disease": "gastrointestinal",
    "ulcerative colitis": "gastrointestinal",
    "inflammatory bowel disease": "gastrointestinal",
    "celiac disease": "gastrointestinal",
    "autoimmune hepatitis": "gastrointestinal",
    "primary biliary cholangitis": "gastrointestinal",
    "primary sclerosing cholangitis": "gastrointestinal",
    "type 1 diabetes": "endocrine",
    "hashimoto thyroiditis": "endocrine",
    "graves disease": "endocrine",
    "addison disease": "endocrine",
    "thyroiditis": "endocrine",
    "multiple sclerosis": "neurological",
    "myasthenia gravis": "neurological",
    "psoriasis": "dermatological",
    "vitiligo": "dermatological",
    "alopecia areata": "dermatological",
    "pemphigus": "dermatological",
    "immune thrombocytopenia": "haematological",
    "autoimmune hemolytic anemia": "haematological",
}


def map_disease_to_cluster(disease_str):
    """Map disease name to Aura cluster."""
    if not disease_str or pd.isna(disease_str):
        return "other_autoimmune"
    d_lower = str(disease_str).lower().strip()
    for keyword, cluster in DISEASE_TO_CLUSTER.items():
        if keyword in d_lower:
            return cluster
    return "other_autoimmune"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Open Targets Associations
# MAGIC
# MAGIC Pre-filtered autoimmune target-disease associations with evidence scores
# MAGIC from 22 evidence sources. 52,471 rows.

# COMMAND ----------

def wrangle_open_targets():
    """Load and process Open Targets autoimmune associations."""
    dest = os.path.join(VOLUME_ROOT, "tier3_open_targets_associations.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    path = os.path.join(RAW_OPEN_TARGETS, "open_targets_autoimmune.parquet")
    if not os.path.exists(path):
        logger.error("Open Targets file not found: %s", path)
        return None

    df = pd.read_parquet(path)
    logger.info("Open Targets raw: %d rows x %d cols", len(df), len(df.columns))

    # Map disease_name to Aura cluster
    df["diagnosis_cluster"] = df["disease_name"].apply(map_disease_to_cluster)
    df["source"] = "open_targets"

    # Rename score columns for clarity
    rename_map = {
        "score_literature": "literature",
        "score_animal_model": "animal_model",
        "score_genetic_association": "genetic_association",
        "score_genetic_literature": "genetic_literature",
        "score_known_drug": "known_drug",
        "score_somatic_mutation": "somatic_mutation",
        "score_rna_expression": "rna_expression",
        "score_affected_pathway": "affected_pathway",
    }
    df = df.rename(columns=rename_map)

    df.to_parquet(dest, index=False)
    logger.info("Saved open_targets_associations: %d rows -> %s", len(df), dest)
    logger.info("  Cluster distribution: %s", df["diagnosis_cluster"].value_counts().head(10).to_dict())
    return df


ot_df = wrangle_open_targets()
if ot_df is not None:
    print(f"Open Targets: {len(ot_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. CTD Chemical-Disease Interactions
# MAGIC
# MAGIC 9.65M rows in the full file. We filter to autoimmune-related diseases
# MAGIC to keep the table manageable.

# COMMAND ----------

def wrangle_ctd():
    """Load and process CTD chemical-disease interactions."""
    dest = os.path.join(VOLUME_ROOT, "tier3_ctd_chemical_disease.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    ctd_path = os.path.join(RAW_CTD, "CTD_chemicals_diseases.tsv.gz")
    if not os.path.exists(ctd_path):
        logger.error("CTD file not found: %s", ctd_path)
        return None

    logger.info("Loading CTD chemicals-diseases (this may take a moment for ~10M rows)...")

    # CTD files have comment lines starting with #
    # The actual header is the first non-comment line
    try:
        # Read and skip comment lines
        import gzip
        header_line = None
        skip_rows = 0
        with gzip.open(ctd_path, "rt") as f:
            for line in f:
                if line.startswith("#"):
                    skip_rows += 1
                    # The last comment line before data typically has column names
                    if "ChemicalName" in line or "Chemical" in line:
                        header_line = line.lstrip("# ").strip()
                else:
                    if header_line is None:
                        header_line = line.strip()
                    break

        logger.info("CTD: skipping %d comment lines", skip_rows)

        # Read in chunks to filter
        chunks = pd.read_csv(
            ctd_path,
            sep="\t",
            compression="gzip",
            comment="#",
            header=None,
            chunksize=500_000,
        )

        # CTD chemicals_diseases columns (from CTD documentation):
        # ChemicalName, ChemicalID, CasRN, DiseaseName, DiseaseID,
        # DirectEvidence, InferenceGeneSymbol, InferenceScore, OmimIDs, PubMedIDs
        col_names = [
            "chemical_name", "chemical_id", "cas_rn", "disease_name",
            "disease_id", "direct_evidence", "inference_gene_symbol",
            "inference_score", "omim_ids", "pubmed_ids",
        ]

        autoimmune_pattern = "|".join(AUTOIMMUNE_KEYWORDS)
        all_filtered = []

        for i, chunk in enumerate(chunks):
            # Assign column names (may have fewer/more columns)
            actual_cols = min(len(col_names), len(chunk.columns))
            chunk.columns = col_names[:actual_cols] + [
                f"extra_{j}" for j in range(len(chunk.columns) - actual_cols)
            ] if len(chunk.columns) > actual_cols else col_names[:len(chunk.columns)]

            if "disease_name" in chunk.columns:
                mask = chunk["disease_name"].str.lower().str.contains(
                    autoimmune_pattern, na=False
                )
                filtered = chunk[mask].copy()
                if not filtered.empty:
                    all_filtered.append(filtered)

            if (i + 1) % 5 == 0:
                logger.info("  Processed %d chunks...", i + 1)

        if not all_filtered:
            logger.warning("No autoimmune-related CTD entries found.")
            return None

        result = pd.concat(all_filtered, ignore_index=True)
        logger.info("CTD filtered: %d autoimmune-related rows", len(result))

    except Exception as e:
        logger.error("Failed to process CTD: %s", e)
        return None

    # Map disease names to Aura clusters
    result["diagnosis_cluster"] = result["disease_name"].apply(map_disease_to_cluster)
    result["source"] = "ctd"

    # Convert inference_score to numeric
    if "inference_score" in result.columns:
        result["inference_score"] = pd.to_numeric(result["inference_score"], errors="coerce")

    result.to_parquet(dest, index=False)
    logger.info("Saved ctd_chemical_disease: %d rows -> %s", len(result), dest)
    return result


ctd_df = wrangle_ctd()
if ctd_df is not None:
    print(f"CTD: {len(ctd_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. EPA Air Quality Reference
# MAGIC
# MAGIC Annual county-level pollutant concentrations. We process annual summary
# MAGIC files for PM2.5, Ozone, NO2, SO2, and PM10.

# COMMAND ----------

def wrangle_epa():
    """Load and process EPA AQS annual pollutant data."""
    dest = os.path.join(VOLUME_ROOT, "tier3_epa_air_quality_reference.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    # Look for annual summary CSVs (not daily files)
    annual_files = sorted([
        f for f in os.listdir(RAW_EPA)
        if f.startswith("annual_conc_by_monitor") and f.endswith(".csv")
    ])
    logger.info("EPA annual files found: %s", annual_files)

    if not annual_files:
        logger.warning("No EPA annual CSV files found. Checking for zip files...")
        zip_files = [f for f in os.listdir(RAW_EPA) if f.startswith("annual") and f.endswith(".zip")]
        if zip_files:
            logger.info("Found zip files: %s. Unzipping...", zip_files)
            import zipfile
            for zf in zip_files:
                zf_path = os.path.join(RAW_EPA, zf)
                try:
                    with zipfile.ZipFile(zf_path, "r") as z:
                        z.extractall(RAW_EPA)
                    logger.info("  Extracted %s", zf)
                except Exception as e:
                    logger.error("  Failed to extract %s: %s", zf, e)
            annual_files = sorted([
                f for f in os.listdir(RAW_EPA)
                if f.startswith("annual_conc_by_monitor") and f.endswith(".csv")
            ])

    if not annual_files:
        logger.error("No EPA annual CSV files available after extraction.")
        return None

    all_frames = []
    # Pollutant parameter codes of interest
    # 88101 = PM2.5 (FRM), 81102 = PM10, 44201 = Ozone, 42602 = NO2, 42401 = SO2
    target_params = {88101, 81102, 44201, 42602, 42401}
    param_names = {
        88101: "PM2.5", 81102: "PM10", 44201: "Ozone",
        42602: "NO2", 42401: "SO2",
    }

    for csv_file in annual_files:
        csv_path = os.path.join(RAW_EPA, csv_file)
        # Extract year from filename
        year_match = csv_file.replace("annual_conc_by_monitor_", "").replace(".csv", "")

        try:
            df = pd.read_csv(csv_path)
            logger.info("EPA %s: %d rows x %d cols", csv_file, len(df), len(df.columns))

            # Standardize column names
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # Filter to target pollutants
            param_col = None
            for candidate in ["parameter_code", "parameter code", "aqs_parameter_code"]:
                clean = candidate.replace(" ", "_")
                if clean in df.columns:
                    param_col = clean
                    break

            if param_col:
                df[param_col] = pd.to_numeric(df[param_col], errors="coerce")
                df = df[df[param_col].isin(target_params)].copy()
                df["parameter"] = df[param_col].map(param_names)
            else:
                logger.warning("  No parameter_code column found in %s. Columns: %s",
                               csv_file, list(df.columns)[:10])

            if not df.empty:
                df["year"] = year_match
                all_frames.append(df)

        except Exception as e:
            logger.error("Failed to process %s: %s", csv_file, e)

    if not all_frames:
        logger.warning("No EPA data processed.")
        return None

    result = pd.concat(all_frames, ignore_index=True)

    # Select and standardize key columns
    output_cols = {}
    col_candidates = {
        "year": ["year"],
        "state_code": ["state_code", "state code"],
        "county_code": ["county_code", "county code"],
        "state_name": ["state_name", "state name"],
        "county_name": ["county_name", "county name"],
        "latitude": ["latitude"],
        "longitude": ["longitude"],
        "parameter": ["parameter"],
        "arithmetic_mean": ["arithmetic_mean", "arithmetic mean"],
        "first_max_value": ["first_max_value", "1st_max_value", "first max value"],
        "units_of_measure": ["units_of_measure", "units of measure"],
        "observation_count": ["observation_count", "observation count"],
    }

    for target_col, candidates in col_candidates.items():
        for cand in candidates:
            clean_cand = cand.replace(" ", "_")
            if clean_cand in result.columns:
                output_cols[target_col] = result[clean_cand]
                break

    output_df = pd.DataFrame(output_cols)
    output_df["source"] = "epa_aqs"

    output_df.to_parquet(dest, index=False)
    logger.info("Saved epa_air_quality_reference: %d rows -> %s", len(output_df), dest)
    return output_df


epa_df = wrangle_epa()
if epa_df is not None:
    print(f"EPA AQS: {len(epa_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Human Protein Atlas Expression
# MAGIC
# MAGIC Full protein atlas with 108 columns. We extract disease-relevant
# MAGIC protein expression data.

# COMMAND ----------

def wrangle_hpa():
    """Load and process Human Protein Atlas data."""
    dest = os.path.join(VOLUME_ROOT, "tier3_hpa_protein_expression.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    tsv_path = os.path.join(RAW_HPA, "proteinatlas.tsv")
    if not os.path.exists(tsv_path):
        logger.error("HPA file not found: %s", tsv_path)
        return None

    try:
        df = pd.read_csv(tsv_path, sep="\t")
    except Exception as e:
        logger.error("Failed to read HPA TSV: %s", e)
        return None

    logger.info("HPA raw: %d rows x %d cols", len(df), len(df.columns))
    logger.info("  Sample columns: %s", list(df.columns)[:20])

    # Key columns to keep: Gene, Ensembl, Uniprot, Protein class,
    # Disease involvement, Blood expression, etc.
    keep_cols = []
    col_lower_map = {c.lower(): c for c in df.columns}

    important_patterns = [
        "gene", "ensembl", "uniprot", "protein class", "disease",
        "blood", "reliability", "evidence", "chromosome", "position",
    ]

    for pattern in important_patterns:
        for col_lower, col_orig in col_lower_map.items():
            if pattern in col_lower and col_orig not in keep_cols:
                keep_cols.append(col_orig)

    if not keep_cols:
        # Fallback: keep first 20 columns
        keep_cols = list(df.columns)[:20]

    df_slim = df[keep_cols].copy()
    logger.info("HPA keeping %d/%d columns: %s", len(keep_cols), len(df.columns), keep_cols)

    # Filter to rows with disease involvement if available
    disease_col = None
    for col in df_slim.columns:
        if "disease" in col.lower():
            disease_col = col
            break

    if disease_col:
        # Keep rows that mention autoimmune diseases
        autoimmune_pattern = "|".join(AUTOIMMUNE_KEYWORDS)
        mask = df_slim[disease_col].str.lower().str.contains(autoimmune_pattern, na=False)
        # Also keep all rows if filter is too aggressive (< 100 rows)
        if mask.sum() > 100:
            df_slim = df_slim[mask].copy()
            logger.info("HPA filtered to autoimmune: %d rows", len(df_slim))
        else:
            logger.info("HPA autoimmune filter too strict (%d rows), keeping all %d rows",
                        mask.sum(), len(df_slim))

    df_slim["source"] = "hpa_v25"
    df_slim["diagnosis_cluster"] = (
        df_slim[disease_col].apply(map_disease_to_cluster)
        if disease_col else "other_autoimmune"
    )

    # Sanitize column names for Delta Lake compatibility
    # Delta rejects: spaces, commas, semicolons, braces, parens, tabs, newlines, equals
    import re
    clean_cols = {}
    for col in df_slim.columns:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', col)
        clean = re.sub(r'_+', '_', clean).strip('_').lower()
        clean_cols[col] = clean
    df_slim = df_slim.rename(columns=clean_cols)
    logger.info("HPA sanitized column names: %s", list(df_slim.columns))

    df_slim.to_parquet(dest, index=False)
    logger.info("Saved hpa_protein_expression: %d rows -> %s", len(df_slim), dest)
    return df_slim


hpa_df = wrangle_hpa()
if hpa_df is not None:
    print(f"HPA: {len(hpa_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Mendeley Lipidomics
# MAGIC
# MAGIC Mouse lipidomics data for EAE (experimental autoimmune encephalomyelitis)
# MAGIC model validation. 3 CSV files: raw data, transformed data, metadata.

# COMMAND ----------

def wrangle_mendeley():
    """Load and process Mendeley lipidomics data."""
    dest = os.path.join(VOLUME_ROOT, "tier3_mendeley_lipidomics.parquet")
    if os.path.exists(dest):
        logger.info("SKIP: %s already exists. Delete manually to force rewrangle.", dest)
        return None

    # Load metadata
    meta_path = os.path.join(RAW_MENDELEY, "mouse_lipidomics_metadata.csv")
    raw_path = os.path.join(RAW_MENDELEY, "mouse_lipidomics_data_raw.csv")
    transformed_path = os.path.join(RAW_MENDELEY, "mouse_lipidomics_data_transformed_imputed.csv")

    if not os.path.exists(meta_path):
        logger.error("Mendeley metadata not found: %s", meta_path)
        return None

    try:
        metadata = pd.read_csv(meta_path)
        logger.info("Mendeley metadata: %d rows x %d cols. Columns: %s",
                     len(metadata), len(metadata.columns), list(metadata.columns))
    except Exception as e:
        logger.error("Failed to read Mendeley metadata: %s", e)
        return None

    # Load transformed (imputed) data for analysis
    data_df = None
    for data_path, label in [(transformed_path, "transformed"), (raw_path, "raw")]:
        if os.path.exists(data_path):
            try:
                data_df = pd.read_csv(data_path)
                logger.info("Mendeley %s data: %d rows x %d cols",
                            label, len(data_df), len(data_df.columns))
                break
            except Exception as e:
                logger.warning("Failed to read Mendeley %s: %s", label, e)

    if data_df is None:
        logger.warning("No Mendeley data files could be read. Using metadata only.")
        metadata["source"] = "mendeley"
        metadata["diagnosis_cluster"] = "neurological"  # EAE is MS model
        metadata.to_parquet(dest, index=False)
        return metadata

    # Merge metadata with data
    # Metadata has: ID, DRUG, EAE, GROUP
    # EAE = 0 (control) or 1 (EAE model = autoimmune encephalomyelitis)
    if "ID" in metadata.columns and data_df.shape[0] == metadata.shape[0]:
        # Drop overlapping columns from data_df before concat to avoid duplicates
        overlap_cols = [c for c in metadata.columns if c in data_df.columns]
        if overlap_cols:
            logger.info("Dropping overlapping columns from data: %s", overlap_cols)
            data_df = data_df.drop(columns=overlap_cols, errors="ignore")
        data_df = pd.concat([metadata, data_df], axis=1)
    # Ensure no duplicate column names (can cause melt failures)
    if data_df.columns.duplicated().any():
        logger.warning("Duplicate columns detected, keeping first occurrence")
        data_df = data_df.loc[:, ~data_df.columns.duplicated()]

    # Determine condition from EAE column
    if "EAE" in data_df.columns:
        data_df["condition"] = data_df["EAE"].map({0: "control", 1: "eae_model"})
        data_df["diagnosis_cluster"] = data_df["EAE"].map({
            0: "healthy", 1: "neurological"  # EAE models MS
        })
    else:
        data_df["condition"] = "unknown"
        data_df["diagnosis_cluster"] = "other_autoimmune"

    data_df["source"] = "mendeley"

    # Melt lipid columns to long format
    meta_cols_present = [c for c in ["ID", "DRUG", "EAE", "GROUP", "condition",
                                      "diagnosis_cluster", "source"] if c in data_df.columns]
    lipid_cols = [c for c in data_df.columns if c not in meta_cols_present]

    if lipid_cols:
        long_df = data_df.melt(
            id_vars=meta_cols_present,
            value_vars=lipid_cols,
            var_name="analyte_name",
            value_name="value",
        )
        long_df["analyte_type"] = "lipid"
        long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
        result = long_df.dropna(subset=["value"])
    else:
        result = data_df

    result.to_parquet(dest, index=False)
    logger.info("Saved mendeley_lipidomics: %d rows -> %s", len(result), dest)
    return result


mendeley_df = wrangle_mendeley()
if mendeley_df is not None:
    print(f"Mendeley: {len(mendeley_df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Register New Tables

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.open_targets_associations
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_open_targets_associations.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.ctd_chemical_disease
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_ctd_chemical_disease.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.epa_air_quality_reference
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_epa_air_quality_reference.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.hpa_protein_expression
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_hpa_protein_expression.parquet`;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE workspace.aura.mendeley_lipidomics
# MAGIC AS SELECT * FROM parquet.`/Volumes/workspace/aura/aura_data/tier3_mendeley_lipidomics.parquet`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Verification

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'open_targets_associations' as tbl, COUNT(*) as rows FROM workspace.aura.open_targets_associations
# MAGIC UNION ALL
# MAGIC SELECT 'ctd_chemical_disease', COUNT(*) FROM workspace.aura.ctd_chemical_disease
# MAGIC UNION ALL
# MAGIC SELECT 'epa_air_quality_reference', COUNT(*) FROM workspace.aura.epa_air_quality_reference
# MAGIC UNION ALL
# MAGIC SELECT 'hpa_protein_expression', COUNT(*) FROM workspace.aura.hpa_protein_expression
# MAGIC UNION ALL
# MAGIC SELECT 'mendeley_lipidomics', COUNT(*) FROM workspace.aura.mendeley_lipidomics;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Table | Tier | Source | Description |
# MAGIC |-------|------|--------|-------------|
# MAGIC | `open_targets_associations` | 3 | Open Targets | 52K+ drug-target-disease evidence scores |
# MAGIC | `ctd_chemical_disease` | 3 | CTD | Chemical-disease interactions (autoimmune filtered) |
# MAGIC | `epa_air_quality_reference` | 3 | EPA AQS | County-level annual pollutant concentrations |
# MAGIC | `hpa_protein_expression` | 3 | HPA v25 | Protein expression with disease involvement |
# MAGIC | `mendeley_lipidomics` | 3 | Mendeley | Mouse lipidomics EAE model data |
