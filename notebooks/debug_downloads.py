# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Test download connectivity and file writes

# COMMAND ----------

import os
import requests

VOLUME_ROOT = "/Volumes/workspace/aura/aura_data"

# Test 1: HugeAmp API connectivity
print("=== Test 1: HugeAmp API ===")
try:
    resp = requests.get(
        "https://bioindex.hugeamp.org/api/bio/query/global-associations",
        params={"q": "T1D", "limit": 2},
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Records: {data.get('count', 0)}")
    if data.get("data"):
        print(f"First record keys: {list(data['data'][0].keys())}")
        print(f"First varId: {data['data'][0].get('varId')}")
except Exception as e:
    print(f"FAILED: {e}")

# COMMAND ----------

# Test 2: CDC NHANES connectivity
print("=== Test 2: CDC NHANES ===")
try:
    resp = requests.get(
        "https://wwwn.cdc.gov/Nchs/Nhanes/2011-2012/HSCRP_G.XPT",
        stream=True,
        timeout=30,
        allow_redirects=True,
    )
    print(f"Status: {resp.status_code}")
    print(f"Content-Length: {resp.headers.get('Content-Length', 'unknown')}")
    print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
    # Download first 1KB to check
    chunk = next(resp.iter_content(chunk_size=1024))
    print(f"First chunk size: {len(chunk)} bytes")
    resp.close()
except Exception as e:
    print(f"FAILED: {e}")

# COMMAND ----------

# Test 3: ImmPort auth
print("=== Test 3: ImmPort Auth ===")
try:
    username = dbutils.secrets.get(scope="aura", key="immport-username")
    password = dbutils.secrets.get(scope="aura", key="immport-password")
    print(f"Got credentials for user: {username}")
    resp = requests.post(
        "https://auth.immport.org/auth/token",
        data={"username": username, "password": password},
        timeout=30,
    )
    print(f"Auth status: {resp.status_code}")
    print(f"Response length: {len(resp.text)}")
    if resp.status_code == 200:
        print("Auth SUCCESS")
    else:
        print(f"Auth response: {resp.text[:500]}")
except Exception as e:
    print(f"FAILED: {e}")

# COMMAND ----------

# Test 4: Volume write test
print("=== Test 4: Volume Write ===")
test_path = os.path.join(VOLUME_ROOT, "raw", "gwas", "_test_write.txt")
try:
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "w") as f:
        f.write("test write OK")
    size = os.path.getsize(test_path)
    print(f"Write successful: {test_path} ({size} bytes)")
    os.remove(test_path)
    print("Cleanup OK")
except Exception as e:
    print(f"FAILED: {e}")

# COMMAND ----------

# Test 5: Full HugeAmp download test (small)
print("=== Test 5: Small HugeAmp Download ===")
import pandas as pd
try:
    resp = requests.get(
        "https://bioindex.hugeamp.org/api/bio/query/global-associations",
        params={"q": "Addison", "limit": 500},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    records = data.get("data", [])
    print(f"Addison records: {len(records)}")
    if records:
        df = pd.DataFrame(records)
        dest = os.path.join(VOLUME_ROOT, "raw", "gwas", "_test_addison.parquet")
        df.to_parquet(dest, index=False)
        size = os.path.getsize(dest)
        print(f"Wrote parquet: {dest} ({size} bytes)")
        os.remove(dest)
except Exception as e:
    print(f"FAILED: {e}")
