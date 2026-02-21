# Databricks notebook source
import os
import json
import requests
import pandas as pd

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"
RAW_GWAS = os.path.join(VOLUME_ROOT, "raw", "gwas")
os.makedirs(RAW_GWAS, exist_ok=True)

results = {}

# COMMAND ----------

# HugeAmp download
try:
    phenotypes = {"T1D": "Type 1 Diabetes", "RhA": "Rheumatoid Arthritis", "SLE": "SLE"}
    all_rows = []
    for pheno, label in phenotypes.items():
        resp = requests.get(
            "https://bioindex.hugeamp.org/api/bio/query/global-associations",
            params={"q": pheno, "limit": 500},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        records = data.get("data", [])
        for r in records:
            r["queried_phenotype"] = pheno
        all_rows.extend(records)
        results[f"hugeamp_{pheno}"] = len(records)

    results["hugeamp_total"] = len(all_rows)

    if all_rows:
        df = pd.DataFrame(all_rows)
        dest = os.path.join(RAW_GWAS, "hugeamp_autoimmune_associations.parquet")
        df.to_parquet(dest, index=False)
        results["parquet_written"] = True
        results["parquet_size"] = os.path.getsize(dest)
        results["parquet_path"] = dest
    else:
        results["parquet_written"] = False
except Exception as e:
    results["hugeamp_error"] = f"{type(e).__name__}: {e}"

# COMMAND ----------

# ImmPort auth test
try:
    username = dbutils.secrets.get(scope="aura", key="immport-username")
    password = dbutils.secrets.get(scope="aura", key="immport-password")
    results["immport_user"] = username
    resp = requests.post(
        "https://auth.immport.org/auth/token",
        data={"username": username, "password": password},
        timeout=30,
    )
    results["immport_auth_status"] = resp.status_code
    if resp.status_code == 200:
        try:
            token_data = resp.json()
            results["immport_token_len"] = len(str(token_data.get("token", "")))
        except Exception:
            results["immport_response"] = resp.text[:200]
    else:
        results["immport_error_body"] = resp.text[:300]
except Exception as e:
    results["immport_error"] = f"{type(e).__name__}: {e}"

# COMMAND ----------

# Verify files
for subdir in ["gwas", "nhanes", "immport"]:
    path = os.path.join(VOLUME_ROOT, "raw", subdir)
    if os.path.exists(path):
        files = os.listdir(path)
        results[f"files_{subdir}"] = files
    else:
        results[f"files_{subdir}"] = "DIR_NOT_FOUND"

dbutils.notebook.exit(json.dumps(results))
