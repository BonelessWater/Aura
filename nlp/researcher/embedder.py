"""
Embedder — The Researcher, Step 2.

Computes 768-dim embeddings for pubmed_chunks using
pritamdeka/S-PubMedBert-MS-MARCO (SentenceTransformers).

Runs locally (Ubuntu GPU recommended).
Upserts embeddings into Databricks Vector Search Direct Vector Access Index.

Index spec:
  endpoint:   aura-vs-endpoint
  index_name: aura.rag.pubmed_index
  primary_key: chunk_id
  embedding_dim: 768
  metric: cosine
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL  = "pritamdeka/S-PubMedBert-MS-MARCO"
EMBEDDING_DIM    = 768
VS_ENDPOINT      = os.environ.get("VS_ENDPOINT", "aura-vs-endpoint")
VS_INDEX_NAME    = "aura.rag.pubmed_index"
UPSERT_BATCH     = 100    # chunks per VS upsert call
READ_BATCH       = 1000   # chunks per Delta read


class PubMedEmbedder:
    """Manages embedding computation and Vector Search upsert."""

    def __init__(self) -> None:
        self._model = None

    def load_model(self) -> None:
        if self._model:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except ImportError:
            raise ImportError("sentence-transformers required: pip install sentence-transformers")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a batch of texts. Returns list of float vectors."""
        self.load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        return self.embed([query])[0]


def ensure_vs_index_exists(client) -> None:
    """
    Create the Vector Search endpoint and Direct Vector Access Index if needed.
    Safe to call multiple times — no-ops if already exists.
    """
    vs = client.get_vs_client()

    # Create endpoint if needed
    try:
        vs.create_endpoint(name=VS_ENDPOINT, endpoint_type="STANDARD")
        logger.info(f"Created VS endpoint: {VS_ENDPOINT}")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"VS endpoint '{VS_ENDPOINT}' already exists")
        else:
            logger.warning(f"VS endpoint creation: {e}")

    # Create Direct Vector Access Index
    try:
        vs.create_direct_access_index(
            endpoint_name=VS_ENDPOINT,
            index_name=VS_INDEX_NAME,
            primary_key="chunk_id",
            embedding_dimension=EMBEDDING_DIM,
            embedding_vector_column="embedding",
            schema={
                "chunk_id":   "string",
                "doi":        "string",
                "journal":    "string",
                "year":       "int",
                "section":    "string",
                "cluster_tag":"string",
                "text":       "string",
                "embedding":  "array<float>",
            },
        )
        logger.info(f"Created VS index: {VS_INDEX_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"VS index '{VS_INDEX_NAME}' already exists")
        else:
            logger.warning(f"VS index creation: {e}")


def run_embedding_pipeline(
    batch_size:  int = READ_BATCH,
    max_chunks:  Optional[int] = None,
) -> int:
    """
    Read un-embedded chunks from aura.rag.pubmed_chunks,
    compute embeddings locally, upsert into Vector Search.

    Returns number of chunks processed.
    """
    from nlp.shared.databricks_client import get_client

    client  = get_client()
    embedder = PubMedEmbedder()
    embedder.load_model()

    ensure_vs_index_exists(client)
    index = client.get_vs_index(VS_ENDPOINT, VS_INDEX_NAME)

    total = 0
    offset = 0

    while True:
        rows = client.run_sql(
            f"SELECT chunk_id, doi, journal, year, section, cluster_tag, text "
            f"FROM aura.rag.pubmed_chunks "
            f"LIMIT {batch_size} OFFSET {offset}"
        )
        if not rows:
            break

        texts     = [r[6] for r in rows]  # text column
        chunk_ids = [r[0] for r in rows]

        logger.info(f"  Embedding {len(texts)} chunks (offset {offset})...")
        embeddings = embedder.embed(texts)

        # Upsert in sub-batches
        for i in range(0, len(rows), UPSERT_BATCH):
            items = []
            for j, row in enumerate(rows[i:i+UPSERT_BATCH]):
                chunk_id, doi, journal, year, section, cluster_tag, text = row
                items.append({
                    "chunk_id":    chunk_id,
                    "doi":         doi,
                    "journal":     journal,
                    "year":        year,
                    "section":     section,
                    "cluster_tag": cluster_tag,
                    "text":        text,
                    "embedding":   embeddings[i + j],
                })
            index.upsert(items)

        total  += len(rows)
        offset += batch_size
        logger.info(f"  Processed {total:,} chunks total")

        if max_chunks and total >= max_chunks:
            break

    logger.info(f"Embedding pipeline complete: {total:,} chunks in Vector Search")
    return total


# Module-level singleton
_embedder: Optional[PubMedEmbedder] = None

def get_embedder() -> PubMedEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = PubMedEmbedder()
        _embedder.load_model()
    return _embedder
