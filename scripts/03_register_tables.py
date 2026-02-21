"""
Aura: Register Parquet files as Delta Tables in Unity Catalog.
This script creates SQL statements to register the uploaded Parquet files
as managed Delta tables in the workspace.aura schema.

Run this as a Databricks notebook or via SQL warehouse.
"""

VOLUME_PATH = "/Volumes/workspace/aura/aura_data"
SCHEMA = "workspace.aura"

TABLES = {
    # Tier 1
    "core_matrix": f"{VOLUME_PATH}/tier1_core_matrix.parquet",
    # Tier 2
    "autoantibody_panel": f"{VOLUME_PATH}/tier2_autoantibody_panel.parquet",
    "longitudinal_labs": f"{VOLUME_PATH}/tier2_longitudinal_labs.parquet",
    # Tier 3
    "healthy_baselines": f"{VOLUME_PATH}/tier3_healthy_baselines.parquet",
    "icd_cluster_map": f"{VOLUME_PATH}/tier3_icd_cluster_map.parquet",
    "drug_risk_index": f"{VOLUME_PATH}/tier3_drug_risk_index.parquet",
}

if __name__ == "__main__":
    print("-- Aura: SQL to register Delta tables from Parquet volumes")
    print(f"-- Schema: {SCHEMA}")
    print()
    for table_name, parquet_path in TABLES.items():
        full_table = f"{SCHEMA}.{table_name}"
        print(f"-- Table: {full_table}")
        print(f"CREATE TABLE IF NOT EXISTS {full_table}")
        print(f"USING PARQUET")
        print(f"LOCATION '{parquet_path}';")
        print()

    print("-- Verification queries:")
    for table_name in TABLES:
        full_table = f"{SCHEMA}.{table_name}"
        print(f"SELECT '{table_name}' AS table_name, COUNT(*) AS row_count FROM {full_table};")
