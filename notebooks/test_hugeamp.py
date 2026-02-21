# Databricks notebook source
# MAGIC %md
# MAGIC # Test HugeAmp API + ImmPort Auth

# COMMAND ----------

import os
import requests
import json

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"

# COMMAND ----------

# Test 1: HugeAmp single query
print("=== HugeAmp Test ===")
try:
    url = "https://bioindex.hugeamp.org/api/bio/query/global-associations"
    resp = requests.get(url, params={"q": "T1D", "limit": 3}, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type', '?')}")
    data = resp.json()
    count = data.get("count", 0)
    print(f"Count: {count}")
    records = data.get("data", [])
    print(f"Records: {len(records)}")
    if records:
        print(f"First record keys: {sorted(records[0].keys())}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

# COMMAND ----------

# Test 2: Full download to parquet
import pandas as pd

print("=== Full HugeAmp Download ===")
phenotypes = {"T1D": "Type 1 Diabetes", "RhA": "Rheumatoid Arthritis", "Addison": "Addison's"}
all_rows = []
for pheno, label in phenotypes.items():
    try:
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
            r["queried_label"] = label
        all_rows.extend(records)
        print(f"  {pheno}: {len(records)} records")
    except Exception as e:
        print(f"  {pheno}: FAILED - {type(e).__name__}: {e}")

print(f"Total records: {len(all_rows)}")
if all_rows:
    df = pd.DataFrame(all_rows)
    dest = os.path.join(VOLUME_ROOT, "raw", "gwas", "test_hugeamp.parquet")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    df.to_parquet(dest, index=False)
    size = os.path.getsize(dest)
    print(f"Saved to {dest} ({size} bytes)")
    # Read it back
    df2 = pd.read_parquet(dest)
    print(f"Read back: {len(df2)} rows, {len(df2.columns)} cols")
    os.remove(dest)
    print("Cleanup OK")

# COMMAND ----------

# Test 3: ImmPort auth
print("=== ImmPort Auth ===")
try:
    username = dbutils.secrets.get(scope="aura", key="immport-username")
    password = dbutils.secrets.get(scope="aura", key="immport-password")
    print(f"Credentials retrieved for: {username}")
    resp = requests.post(
        "https://auth.immport.org/auth/token",
        data={"username": username, "password": password},
        timeout=30,
    )
    print(f"Auth status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else resp.text
        if isinstance(result, dict):
            token = result.get("token", "")
            print(f"Token received: {len(token)} chars")
        else:
            print(f"Response: {str(result)[:200]}")
    else:
        print(f"Error response: {resp.text[:500]}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

# COMMAND ----------

# Use dbutils.notebook.exit to capture output
result_parts = []
result_parts.append("Tests completed - check cell outputs above")
dbutils.notebook.exit(json.dumps({"status": "done"}))
