# Databricks notebook source
# MAGIC %md
# MAGIC # Aura: Download Additional Datasets (Direct to Volumes)
# MAGIC
# MAGIC Downloads FinnGen R12 summary stats and HugeAmp GWAS data
# MAGIC directly into Databricks Volumes -- nothing touches your local machine.
# MAGIC
# MAGIC **Datasets:**
# MAGIC 1. FinnGen R12 summary statistics (5 autoimmune endpoints)
# MAGIC 2. HugeAmp BioIndex (autoimmune GWAS associations via REST API)
# MAGIC 3. NHANES CRP re-download (corrupt 2011-2014 files)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import os
import logging
import json

import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura_download")

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_FINNGEN = os.path.join(VOLUME_ROOT, "raw", "finngen")
RAW_GWAS = os.path.join(VOLUME_ROOT, "raw", "gwas")
RAW_NHANES = os.path.join(VOLUME_ROOT, "raw", "nhanes")

for d in [RAW_FINNGEN, RAW_GWAS, RAW_NHANES]:
    os.makedirs(d, exist_ok=True)
    logger.info("Directory ready: %s", d)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. FinnGen R12 Summary Statistics
# MAGIC
# MAGIC Downloads GWAS summary statistics for 5 key autoimmune endpoints from
# MAGIC FinnGen Data Release R12 (public, hosted on Google Cloud Storage).
# MAGIC
# MAGIC Each file is ~400-900 MB compressed. The Databricks cluster handles this
# MAGIC directly -- no local disk needed.
# MAGIC
# MAGIC **Note:** You may need to accept the FinnGen terms at
# MAGIC [finngen.fi/en/access_results](https://www.finngen.fi/en/access_results) first.

# COMMAND ----------

FINNGEN_ENDPOINTS = {
    "M13_RHEUMA": "Rheumatoid Arthritis",
    "SLE_FG": "Systemic Lupus Erythematosus",
    "K11_IBD_STRICT": "Inflammatory Bowel Disease",
    "E4_THYROIDITAUTOIM": "Autoimmune Thyroiditis",
    "L12_PSORIASIS": "Psoriasis",
}

FINNGEN_BASE_URL = (
    "https://storage.googleapis.com/finngen-public-data-r12/"
    "summary_stats/release/finngen_R12_{endpoint}.gz"
)


def download_finngen():
    """Download FinnGen R12 summary stats to Volume."""
    results = {}
    for endpoint, label in FINNGEN_ENDPOINTS.items():
        url = FINNGEN_BASE_URL.format(endpoint=endpoint)
        dest = os.path.join(RAW_FINNGEN, f"finngen_R12_{endpoint}.gz")

        if os.path.exists(dest):
            size_mb = os.path.getsize(dest) / 1e6
            logger.info("Already exists (%s, %.1f MB), skipping: %s", label, size_mb, dest)
            results[endpoint] = f"skipped ({size_mb:.1f} MB)"
            continue

        logger.info("Downloading %s (%s)...", endpoint, label)
        try:
            resp = requests.get(url, stream=True, timeout=600)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            size_mb = os.path.getsize(dest) / 1e6
            logger.info("Done: %s (%.1f MB)", endpoint, size_mb)
            results[endpoint] = f"downloaded ({size_mb:.1f} MB)"
        except requests.RequestException as e:
            logger.error("Failed to download %s: %s", endpoint, e)
            results[endpoint] = f"FAILED: {e}"

    return results


finngen_results = download_finngen()
for ep, status in finngen_results.items():
    print(f"  {ep}: {status}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. HugeAmp BioIndex (Autoimmune GWAS Associations)
# MAGIC
# MAGIC Queries the HugeAmp BioIndex REST API for global GWAS associations
# MAGIC across 13 autoimmune phenotypes. Uses the `/api/bio/query/global-associations`
# MAGIC endpoint with phenotype-specific queries.
# MAGIC
# MAGIC API docs: https://bioindex.hugeamp.org/docs

# COMMAND ----------

HUGEAMP_API = "https://bioindex.hugeamp.org/api/bio/query/global-associations"
HUGEAMP_CONT = "https://bioindex.hugeamp.org/api/bio/cont"

# Correct phenotype codes from the HugeAmp portal phenotypes endpoint
GWAS_PHENOTYPES = {
    "T1D": "Type 1 Diabetes",
    "RhA": "Rheumatoid Arthritis",
    "SLE": "Systemic Lupus Erythematosus",
    "CD": "Crohn's Disease",
    "UC": "Ulcerative Colitis",
    "IBD": "Inflammatory Bowel Disease",
    "MultipleSclerosis": "Multiple Sclerosis",
    "Psoriasis": "Psoriasis",
    "Celiac": "Celiac Disease",
    "Graves": "Graves' Disease",
    "Vitiligo": "Vitiligo",
    "LADA": "Latent Autoimmune Diabetes in Adults",
    "Addison": "Autoimmune Addison's Disease",
}


def query_hugeamp_associations(phenotype, limit=500):
    """Query HugeAmp BioIndex global-associations for a phenotype.

    Uses the REST endpoint /api/bio/query/global-associations with
    pagination via continuation tokens.
    """
    all_records = []
    params = {"q": phenotype, "limit": limit}
    try:
        resp = requests.get(HUGEAMP_API, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and data["data"]:
            all_records.extend(data["data"])

        # Follow continuation tokens for paginated results
        continuation = data.get("continuation")
        while continuation:
            resp = requests.get(HUGEAMP_CONT, params={"token": continuation}, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if "data" in data and data["data"]:
                all_records.extend(data["data"])
            continuation = data.get("continuation")

        return all_records
    except requests.RequestException as e:
        logger.error("HugeAmp query failed for %s: %s", phenotype, e)
        return []


def download_gwas_data():
    """Download GWAS associations for all autoimmune phenotypes."""
    dest = os.path.join(RAW_GWAS, "hugeamp_autoimmune_associations.parquet")
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / 1e6
        logger.info("HugeAmp data already exists (%.1f MB): %s", size_mb, dest)
        logger.info("Delete the file to re-download.")
        return pd.read_parquet(dest)

    all_rows = []
    for phenotype, label in GWAS_PHENOTYPES.items():
        logger.info("Querying HugeAmp for %s (%s)...", phenotype, label)
        records = query_hugeamp_associations(phenotype)
        if records:
            for r in records:
                r["queried_phenotype"] = phenotype
                r["queried_label"] = label
            all_rows.extend(records)
            logger.info("  %s: %d associations", phenotype, len(records))
        else:
            logger.warning("  %s: no results", phenotype)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_parquet(dest, index=False)
        logger.info("Saved %d GWAS associations to %s", len(df), dest)
        return df
    else:
        logger.warning("No GWAS data retrieved from HugeAmp.")
        return pd.DataFrame()


gwas_df = download_gwas_data()
if len(gwas_df) > 0:
    print(f"Total GWAS associations: {len(gwas_df)}")
    print(gwas_df.groupby("queried_phenotype").size())
else:
    print("No GWAS data retrieved.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. NHANES Data Verification
# MAGIC
# MAGIC NHANES files were uploaded to the Volume via `databricks fs cp` because:
# MAGIC - CDC changed their website and XPT download URLs no longer return data files
# MAGIC - HSCRP (high-sensitivity CRP) was NOT collected in 2011-2012 or 2013-2014 cycles
# MAGIC - Valid HSCRP data exists for 2015-2016 (I) and 2017-2018 (J) only
# MAGIC
# MAGIC **Files uploaded:** CBC + DEMO for G/H/I/J cycles, HSCRP for I/J cycles

# COMMAND ----------

# Verify NHANES files in Volume
NHANES_EXPECTED = [
    "CBC_G.XPT", "CBC_H.XPT", "CBC_I.XPT", "CBC_J.XPT",
    "DEMO_G.XPT", "DEMO_H.XPT", "DEMO_I.XPT", "DEMO_J.XPT",
    "HSCRP_I.XPT", "HSCRP_J.XPT",
]

print("=== NHANES File Verification ===")
nhanes_ok = True
for fname in NHANES_EXPECTED:
    fpath = os.path.join(RAW_NHANES, fname)
    if os.path.exists(fpath):
        size_kb = os.path.getsize(fpath) / 1e3
        print(f"  {fname}: {size_kb:.1f} KB")
    else:
        print(f"  {fname}: MISSING")
        nhanes_ok = False

if nhanes_ok:
    print("\nAll NHANES files present.")
else:
    print("\nSome files missing. Upload them via:")
    print("  databricks fs cp <local_path> dbfs:/Volumes/workspace/aura/aura_data/raw/nhanes/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC After running this notebook, your Volume should contain:
# MAGIC
# MAGIC ```
# MAGIC /Volumes/workspace/aura/aura_data/
# MAGIC   raw/
# MAGIC     finngen/         (5 x .gz files, ~4 GB total)
# MAGIC     gwas/            (hugeamp_autoimmune_associations.parquet, ~2000 rows)
# MAGIC     nhanes/          (10 x .XPT files: CBC+DEMO for 4 cycles, HSCRP for 2 cycles)
# MAGIC ```
# MAGIC
# MAGIC Next step: run the wrangling notebook to process these into Tier 2/3 tables.

# COMMAND ----------

# Verify what was downloaded
print("=== Downloaded Files ===")
for subdir in ["finngen", "gwas", "nhanes"]:
    full_path = os.path.join(VOLUME_ROOT, "raw", subdir)
    if os.path.exists(full_path):
        files = os.listdir(full_path)
        total_mb = sum(
            os.path.getsize(os.path.join(full_path, f)) / 1e6
            for f in files if os.path.isfile(os.path.join(full_path, f))
        )
        print(f"\n{subdir}/ ({total_mb:.1f} MB total)")
        for f in sorted(files):
            fpath = os.path.join(full_path, f)
            if os.path.isfile(fpath):
                print(f"  {f} ({os.path.getsize(fpath) / 1e6:.1f} MB)")
    else:
        print(f"\n{subdir}/ (not created)")
