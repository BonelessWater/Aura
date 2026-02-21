"""
Pull all chunks from aura.rag.pubmed_chunks (Databricks Delta)
and save locally as chunks.parquet.

Usage:
    pip install databricks-sdk pyarrow
    python pull_chunks.py

Requires ~/.databrickscfg (or C:\\Users\\<name>\\.databrickscfg on Windows):
    [DEFAULT]
    host  = https://dbc-893d098d-9dcb.cloud.databricks.com
    token = <your-token>
"""

from databricks.sdk import WorkspaceClient
import pyarrow as pa
import pyarrow.parquet as pq

WAREHOUSE_ID = "a3f84fea6e440a44"
PAGE_SIZE    = 5_000
OUTPUT_FILE  = "chunks.parquet"

w      = WorkspaceClient()
offset = 0
rows   = []

print("Pulling chunks from aura.rag.pubmed_chunks...")

while True:
    r = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=(
            "SELECT chunk_id, doi, journal, year, section, cluster_tag, text, pmc_id "
            "FROM aura.rag.pubmed_chunks "
            f"ORDER BY chunk_id LIMIT {PAGE_SIZE} OFFSET {offset}"
        ),
        wait_timeout="50s",
    )
    batch = r.result.data_array or []
    if not batch:
        break
    rows.extend(batch)
    offset += PAGE_SIZE
    print(f"  {len(rows):,} chunks pulled...")

print(f"Writing {len(rows):,} chunks to {OUTPUT_FILE}...")

table = pa.table({
    "chunk_id":    [r[0] for r in rows],
    "doi":         [r[1] for r in rows],
    "journal":     [r[2] for r in rows],
    "year":        pa.array([int(r[3]) if r[3] else None for r in rows], type=pa.int32()),
    "section":     [r[4] for r in rows],
    "cluster_tag": [r[5] for r in rows],
    "text":        [r[6] for r in rows],
    "pmc_id":      [r[7] for r in rows],
})

pq.write_table(table, OUTPUT_FILE)
print(f"Done — {OUTPUT_FILE} ({table.nbytes / 1e6:.1f} MB)")
