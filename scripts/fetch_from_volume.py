"""
Fetch parquet files directly from Databricks Volume via REST API.

This bypasses SQL permissions and reads files directly from the volume.
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABRICKS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")
DATABRICKS_WORKSPACE = os.getenv("DATABRICKS_WORKSPACE_ID")
DATABRICKS_HOST = f"https://{DATABRICKS_WORKSPACE}.cloud.databricks.com"

VOLUME_PATH = "/Volumes/workspace/aura/aura_data"

DATA_DIR = Path(__file__).parent.parent / "modeling" / "data" / "processed"

FILES = {
    "tier1": ["tier1_core_matrix.parquet"],
    "tier2": [
        "tier2_autoantibody_panel.parquet",
        "tier2_gi_markers.parquet",
        "tier2_longitudinal_labs.parquet",
        "tier2_genetic_risk_scores.parquet",
    ],
    "tier3": [
        "tier3_healthy_baselines.parquet",
        "tier3_icd_cluster_map.parquet",
        "tier3_drug_risk_index.parquet",
    ],
}


def download_file(session: requests.Session, volume_file: str, local_path: Path):
    """Download a file from Databricks Volume."""
    url = f"{DATABRICKS_HOST}/api/2.0/fs/files{VOLUME_PATH}/{volume_file}"
    print(f"  Downloading {volume_file}...")

    response = session.get(url, stream=True)

    if response.status_code == 200:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"    -> Saved ({size_mb:.1f} MB)")
        return True
    elif response.status_code == 404:
        print(f"    -> File not found (404)")
        return False
    else:
        print(f"    -> Error {response.status_code}: {response.text[:200]}")
        return False


def list_volume_files(session: requests.Session):
    """List files in the volume."""
    url = f"{DATABRICKS_HOST}/api/2.0/fs/directories{VOLUME_PATH}"
    response = session.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Could not list volume: {response.status_code}")
        print(response.text[:500])
        return None


def main():
    if not DATABRICKS_TOKEN or not DATABRICKS_WORKSPACE:
        print("ERROR: Missing DATABRICKS credentials in .env")
        sys.exit(1)

    print(f"Connecting to: {DATABRICKS_HOST}")
    print(f"Volume path: {VOLUME_PATH}")
    print()

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {DATABRICKS_TOKEN}"

    # First, list what's in the volume
    print("Listing volume contents...")
    contents = list_volume_files(session)
    if contents:
        print("Files found:")
        for item in contents.get("contents", []):
            print(f"  - {item.get('name', item.get('path', 'unknown'))}")
        print()

    # Download files
    success_count = 0
    fail_count = 0

    for tier, files in FILES.items():
        tier_dir = DATA_DIR / tier
        print(f"\n=== {tier.upper()} ===")

        for filename in files:
            # Remove tier prefix for local filename
            local_name = filename.replace(f"{tier}_", "")
            local_path = tier_dir / local_name

            if download_file(session, filename, local_path):
                success_count += 1
            else:
                fail_count += 1

    print("\n" + "=" * 50)
    print(f"Complete: {success_count} downloaded, {fail_count} failed")


if __name__ == "__main__":
    main()
