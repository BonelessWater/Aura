"""
Embed chunks and push to Actian VectorAI DB.

Setup (run once):
    1. Clone Actian repo and start Docker:
           git clone https://github.com/hackmamba-io/actian-vectorAI-db-beta
           cd actian-vectorAI-db-beta
           docker compose up -d
    2. Install the client wheel (from inside the cloned repo):
           pip install actiancortex-0.1.0b1-py3-none-any.whl
    3. Install other deps:
           pip install sentence-transformers pyarrow torch

Usage:
    python embed_and_index.py                  # uses chunks.parquet in same dir
    python embed_and_index.py my_chunks.parquet
"""

import sys
import time
from pathlib import Path

import pyarrow.parquet as pq
from cortex import CortexClient, DistanceMetric

ACTIAN_HOST     = "localhost:50051"
COLLECTION_NAME = "pubmed_chunks"
EMBEDDING_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
EMBEDDING_DIM   = 768
EMBED_BATCH     = 64    # rows to embed at once (tune up if VRAM allows)
UPSERT_BATCH    = 200   # rows per batch_upsert call

# ── Load parquet ──────────────────────────────────────────────────────────────

parquet_file = Path(sys.argv[1] if len(sys.argv) > 1 else "chunks.parquet")
if not parquet_file.exists():
    print(f"ERROR: {parquet_file} not found. Run pull_chunks.py first.")
    sys.exit(1)

print(f"Loading {parquet_file}...")
table = pq.read_table(parquet_file)
rows  = table.to_pydict()
total = len(rows["chunk_id"])
print(f"  {total:,} chunks loaded")

# ── Load embedding model ──────────────────────────────────────────────────────

print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(EMBEDDING_MODEL)
print("  Model ready")

# ── Create Actian collection ──────────────────────────────────────────────────

print(f"\nConnecting to Actian VectorAI at {ACTIAN_HOST}...")
with CortexClient(ACTIAN_HOST) as client:
    try:
        client.create_collection(
            name=COLLECTION_NAME,
            dimension=EMBEDDING_DIM,
            distance_metric=DistanceMetric.COSINE,
        )
        print(f"  Created collection: {COLLECTION_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  Collection '{COLLECTION_NAME}' already exists — continuing")
        else:
            raise

    # ── Embed + upsert ────────────────────────────────────────────────────────

    print(f"\nEmbedding and indexing {total:,} chunks...")
    start    = time.time()
    indexed  = 0

    for batch_start in range(0, total, EMBED_BATCH):
        batch_end = min(batch_start + EMBED_BATCH, total)

        texts = rows["text"][batch_start:batch_end]

        embeddings = model.encode(
            texts,
            batch_size=EMBED_BATCH,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        # Push in upsert sub-batches
        for sub_start in range(0, len(texts), UPSERT_BATCH):
            sub_end = min(sub_start + UPSERT_BATCH, len(texts))
            i       = batch_start + sub_start

            client.batch_upsert(
                COLLECTION_NAME,
                ids     = list(range(i, i + (sub_end - sub_start))),
                vectors = embeddings[sub_start:sub_end],
                payloads= [
                    {
                        "chunk_id":    rows["chunk_id"][i + k],
                        "doi":         rows["doi"][i + k],
                        "journal":     rows["journal"][i + k],
                        "year":        rows["year"][i + k],
                        "section":     rows["section"][i + k],
                        "cluster_tag": rows["cluster_tag"][i + k],
                        "text":        rows["text"][i + k],
                        "pmc_id":      rows["pmc_id"][i + k],
                    }
                    for k in range(sub_end - sub_start)
                ],
            )

        indexed += (batch_end - batch_start)
        elapsed  = time.time() - start
        rate     = indexed / elapsed
        eta      = (total - indexed) / rate if rate > 0 else 0
        print(f"  {indexed:,}/{total:,}  ({indexed/total*100:.1f}%)  "
              f"{rate:.0f} chunks/s  ETA {eta/60:.1f} min")

elapsed = time.time() - start
print(f"\nDone — {indexed:,} chunks indexed in {elapsed/60:.1f} min")
print(f"Actian collection '{COLLECTION_NAME}' is ready for search.")
