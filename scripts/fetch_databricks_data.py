"""
Fetch data from Databricks Unity Catalog and save as local parquet files.

Usage:
    python scripts/fetch_databricks_data.py

Requires:
    pip install databricks-sql-connector python-dotenv pandas pyarrow
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Databricks connection settings
DATABRICKS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")
DATABRICKS_WORKSPACE = os.getenv("DATABRICKS_WORKSPACE_ID")
WAREHOUSE_ID = "a3f84fea6e440a44"  # Serverless Starter Warehouse

# Construct the server hostname
DATABRICKS_HOST = f"{DATABRICKS_WORKSPACE}.cloud.databricks.com"

# Output directory
DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# Tables to fetch
TABLES = {
    "tier1": [
        "core_matrix",
    ],
    "tier2": [
        "autoantibody_panel",
        "longitudinal_labs",
        "genetic_risk_scores",
    ],
    "tier3": [
        "healthy_baselines",
        "icd_cluster_map",
        "drug_risk_index",
    ],
}


def fetch_table(cursor, table_name: str) -> pd.DataFrame:
    """Fetch a table from Databricks and return as DataFrame."""
    print(f"  Fetching workspace.aura.{table_name}...")
    cursor.execute(f"SELECT * FROM workspace.aura.{table_name}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    print(f"    -> {len(df):,} rows, {len(df.columns)} columns")
    return df


def main():
    if not DATABRICKS_TOKEN:
        print("ERROR: DATABRICKS_ACCESS_TOKEN not found in .env")
        sys.exit(1)

    if not DATABRICKS_WORKSPACE:
        print("ERROR: DATABRICKS_WORKSPACE_ID not found in .env")
        sys.exit(1)

    print(f"Connecting to Databricks: {DATABRICKS_HOST}")
    print(f"Using warehouse: {WAREHOUSE_ID}")
    print()

    try:
        from databricks import sql

        connection = sql.connect(
            server_hostname=DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            access_token=DATABRICKS_TOKEN,
        )

        cursor = connection.cursor()

        for tier, tables in TABLES.items():
            tier_dir = DATA_DIR / tier
            tier_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n=== {tier.upper()} ===")
            for table_name in tables:
                df = fetch_table(cursor, table_name)
                output_path = tier_dir / f"{table_name}.parquet"
                df.to_parquet(output_path, index=False)
                print(f"    Saved to {output_path}")

        cursor.close()
        connection.close()

        print("\n" + "=" * 50)
        print("Data fetch complete!")
        print(f"Files saved to: {DATA_DIR}")

    except ImportError:
        print("ERROR: databricks-sql-connector not installed")
        print("Run: pip install databricks-sql-connector")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
