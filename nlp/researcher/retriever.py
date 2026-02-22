"""
Retriever — The Researcher, Step 3.

Formulates cluster-targeted sub-queries from a patient bundle
and queries the configured vector backend for the top-50 passages.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from typing import Optional

from nlp.shared.schemas import (
    Cluster,
    InterviewResult,
    LabReport,
    RetrievedPassage,
)
from nlp.researcher.embedder import get_embedder, VS_ENDPOINT, VS_INDEX_NAME

logger = logging.getLogger(__name__)

TOP_K_RETRIEVAL = 50
AURA_VECTOR_BACKEND = os.environ.get("AURA_VECTOR_BACKEND", "actian").strip().lower()
ACTIAN_HOST = os.environ.get("ACTIAN_HOST", "100.100.165.29:50051")
ACTIAN_COLLECTION = os.environ.get("ACTIAN_COLLECTION", "pubmed_chunks")


def formulate_queries(
    lab_report:       Optional[LabReport]       = None,
    interview_result: Optional[InterviewResult] = None,
) -> list[str]:
    """
    Build 3–5 cluster-targeted sub-queries from the patient bundle.

    Returns a list of natural-language query strings.
    """
    queries: list[str] = []

    # ── Lab query ─────────────────────────────────────────────────────────────
    if lab_report:
        fp     = lab_report.bio_fingerprint
        parts  = []
        if fp.sustained_abnormalities:
            parts.append("sustained " + " ".join(fp.sustained_abnormalities[:3]) + " elevation")
        if fp.NLR:
            latest_nlr = fp.NLR[-1].value
            parts.append(f"NLR ratio {round(latest_nlr, 1)} autoimmune systemic inflammation")
        if fp.morphological_shifts:
            parts.append(" ".join(fp.morphological_shifts[:2]) + " morphological shift")
        if fp.C3_C4 and fp.C3_C4[-1].flag == "LOW":
            parts.append("low complement C3 C4 ratio lupus")
        if parts:
            queries.append("Lab findings: " + ", ".join(parts))

    # ── Symptom query ─────────────────────────────────────────────────────────
    if interview_result:
        cluster_syms: dict[str, list[str]] = {}
        for sym in interview_result.symptoms:
            if sym.cluster_signal:
                cluster_syms.setdefault(sym.cluster_signal.value, []).append(sym.entity)

        for cluster, syms in cluster_syms.items():
            queries.append(
                " ".join(syms[:6]) + f" {cluster.lower()} autoimmune"
            )

        # Visual keywords query
        if interview_result.visual_keywords:
            queries.append(" ".join(interview_result.visual_keywords[:8]))

    # Fallback generic query
    if not queries:
        queries.append("autoimmune disease biomarkers inflammation")

    return queries[:5]  # max 5 sub-queries


def retrieve_passages(
    queries:          list[str],
    cluster_filter:   Optional[Cluster] = None,
    top_k:            int = TOP_K_RETRIEVAL,
) -> list[RetrievedPassage]:
    """
    Embed each query and retrieve passages from Vector Search.
    Merge and deduplicate by chunk_id.

    Args:
        queries:        list of query strings
        cluster_filter: if provided, filter results to this cluster
        top_k:          number of results per query
    """
    # Default backend is Actian VectorAI (host:50051), with Databricks fallback.
    if AURA_VECTOR_BACKEND == "databricks":
        return _retrieve_from_databricks(queries, cluster_filter, top_k)

    actian_hits = _retrieve_from_actian(queries, cluster_filter, top_k)
    if actian_hits:
        return actian_hits

    logger.info("Actian retrieval returned no passages; trying Databricks fallback.")
    return _retrieve_from_databricks(queries, cluster_filter, top_k)


def _retrieve_from_actian(
    queries: list[str],
    cluster_filter: Optional[Cluster],
    top_k: int,
) -> list[RetrievedPassage]:
    try:
        from cortex import CortexClient
    except Exception as e:
        logger.error(f"Actian client unavailable: {e}")
        return []

    try:
        embedder = get_embedder()
    except Exception as e:
        logger.error(f"Embedding model unavailable for Actian retrieval: {e}")
        return []

    seen: set[str] = set()
    passages: list[RetrievedPassage] = []

    try:
        with CortexClient(ACTIAN_HOST) as client:
            for query in queries:
                try:
                    query_vec = embedder.embed_query(query)
                    hits = client.search(ACTIAN_COLLECTION, query=query_vec, top_k=top_k)
                except Exception as e:
                    logger.warning(f"Actian search failed for query '{query[:60]}': {e}")
                    continue

                for hit in hits or []:
                    parsed = _parse_actian_hit(hit)
                    if not parsed:
                        continue
                    if parsed.chunk_id in seen:
                        continue
                    if cluster_filter and parsed.cluster_tag != cluster_filter:
                        continue
                    seen.add(parsed.chunk_id)
                    passages.append(parsed)
    except Exception as e:
        logger.error(f"Actian VectorAI unavailable at {ACTIAN_HOST}: {e}")
        return []

    passages.sort(key=lambda p: p.score, reverse=True)
    return passages


def _parse_actian_hit(hit: Any) -> Optional[RetrievedPassage]:
    payload: dict[str, Any] = {}
    hit_id: Any = None
    score: Any = None

    if isinstance(hit, dict):
        payload = hit.get("payload") or {}
        hit_id = hit.get("id")
        score = hit.get("score")
    else:
        payload = getattr(hit, "payload", None) or {}
        hit_id = getattr(hit, "id", None)
        score = getattr(hit, "score", None)

    if not isinstance(payload, dict):
        payload = {}

    chunk_id = str(payload.get("chunk_id") or hit_id or "")
    if not chunk_id:
        return None

    cluster_enum = None
    cluster_tag = payload.get("cluster_tag")
    if cluster_tag:
        try:
            cluster_enum = Cluster(cluster_tag)
        except ValueError:
            cluster_enum = None

    return RetrievedPassage(
        chunk_id=chunk_id,
        doi=payload.get("doi"),
        journal=payload.get("journal"),
        year=int(payload["year"]) if payload.get("year") is not None else None,
        section=payload.get("section"),
        cluster_tag=cluster_enum,
        text=payload.get("text") or "",
        score=float(score) if score is not None else 0.0,
    )


def _retrieve_from_databricks(
    queries: list[str],
    cluster_filter: Optional[Cluster],
    top_k: int,
) -> list[RetrievedPassage]:
    from nlp.shared.databricks_client import get_client

    try:
        embedder = get_embedder()
    except Exception as e:
        logger.error(f"Embedding model unavailable for Databricks retrieval: {e}")
        return []

    client = get_client()
    try:
        index = client.get_vs_index(VS_ENDPOINT, VS_INDEX_NAME)
    except Exception as e:
        logger.error(f"Databricks Vector Search unavailable: {e}")
        return []

    seen: set[str] = set()
    passages: list[RetrievedPassage] = []
    query_filter = {"cluster_tag": cluster_filter.value} if cluster_filter else None

    for query in queries:
        try:
            query_vec = embedder.embed_query(query)
            results = index.similarity_search(
                query_vector=query_vec,
                columns=["chunk_id", "doi", "journal", "year", "section", "cluster_tag", "text"],
                num_results=top_k,
                filters=query_filter,
            )
        except Exception as e:
            logger.warning(f"Databricks VS search failed for query '{query[:60]}': {e}")
            continue

        for hit in results.get("result", {}).get("data_array", []):
            chunk_id, doi, journal, year, section, cluster_tag, text, score = (
                hit + [None] * 8
            )[:8]
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)

            cluster_enum = None
            if cluster_tag:
                try:
                    cluster_enum = Cluster(cluster_tag)
                except ValueError:
                    pass

            passages.append(RetrievedPassage(
                chunk_id=chunk_id,
                doi=doi,
                journal=journal,
                year=int(year) if year else None,
                section=section,
                cluster_tag=cluster_enum,
                text=text or "",
                score=float(score) if score else 0.0,
            ))

    passages.sort(key=lambda p: p.score, reverse=True)
    return passages
