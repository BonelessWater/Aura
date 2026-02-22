"""
Retriever — The Researcher, Step 3.

Formulates cluster-targeted sub-queries from a patient bundle
and queries Databricks Vector Search for the top-50 passages.

Backend modes (controlled by AURA_NLP_BACKEND or AURA_NLP_BACKEND_RESEARCHER):
  - "local": Databricks Vector Search (Direct Access with local embedder)
  - "azure": Databricks Vector Search (Managed Embeddings with query_text),
             falls back to Azure OpenAI evidence generation if VS unavailable
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from nlp.shared.schemas import (
    BioFingerprint,
    Cluster,
    InterviewResult,
    LabReport,
    RetrievedPassage,
)

logger = logging.getLogger(__name__)

VS_ENDPOINT   = os.environ.get("VS_ENDPOINT", "aura-vs-endpoint")
VS_INDEX_NAME = os.environ.get("VS_INDEX_NAME", "workspace.aura.pubmed_chunks_index")
TOP_K_RETRIEVAL = 50


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
    Retrieve passages from Databricks Vector Search.

    Uses Azure OpenAI when AURA_NLP_BACKEND=azure and VS is unavailable,
    otherwise local S-PubMedBert embedder with Direct Access index.

    Merge and deduplicate by chunk_id across all sub-queries.
    """
    from nlp.shared.azure_client import get_nlp_backend

    backend = get_nlp_backend("researcher")

    # Try Databricks Vector Search first (works with both backends)
    passages = _retrieve_from_vs(queries, cluster_filter, top_k, use_local_embedder=(backend != "azure"))
    if passages:
        return passages

    # Fallback: Azure generates evidence passages when VS is unavailable
    if backend == "azure":
        logger.info("Vector Search unavailable, falling back to Azure evidence generation")
        return _retrieve_azure_evidence(queries, top_k)

    return []


def _retrieve_from_vs(
    queries: list[str],
    cluster_filter: Optional[Cluster],
    top_k: int,
    use_local_embedder: bool = False,
) -> list[RetrievedPassage]:
    """Retrieve from Databricks Vector Search (managed or direct access)."""
    from nlp.shared.databricks_client import get_client

    client = get_client()

    try:
        index = client.get_vs_index(VS_ENDPOINT, VS_INDEX_NAME)
    except Exception as e:
        logger.error(f"Vector Search unavailable: {e}")
        return []

    # Detect index type to decide query method
    use_query_text = not use_local_embedder
    try:
        index_desc = index.describe()
        index_type = index_desc.get("index_type", "")
        if index_type == "DIRECT_ACCESS":
            use_query_text = False
    except Exception:
        pass

    # Load local embedder only if needed for direct access index
    embedder = None
    if not use_query_text:
        from nlp.researcher.embedder import get_embedder
        embedder = get_embedder()

    seen:     set[str] = set()
    passages: list[RetrievedPassage] = []

    columns = ["chunk_id", "doi", "journal", "year", "section", "text"]

    for query in queries:
        try:
            if use_query_text:
                results = index.similarity_search(
                    query_text=query,
                    columns=columns,
                    num_results=top_k,
                )
            else:
                query_vec = embedder.embed_query(query)
                results = index.similarity_search(
                    query_vector=query_vec,
                    columns=columns + ["cluster_tag"],
                    num_results=top_k,
                )
        except Exception as e:
            logger.warning(f"VS search failed for query '{query[:60]}': {e}")
            continue

        for hit in results.get("result", {}).get("data_array", []):
            # Pad to expected length
            hit = list(hit) + [None] * 10
            if use_query_text:
                chunk_id, doi, journal, year, section, text, score = hit[:7]
                cluster_tag = None
            else:
                chunk_id, doi, journal, year, section, cluster_tag, text, score = hit[:8]

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
                chunk_id    = chunk_id,
                doi         = doi,
                journal     = journal,
                year        = int(year) if year else None,
                section     = section,
                cluster_tag = cluster_enum,
                text        = text or "",
                score       = float(score) if score else 0.0,
            ))

    # Sort by score descending
    passages.sort(key=lambda p: p.score, reverse=True)
    return passages


def _retrieve_azure_evidence(
    queries: list[str],
    top_k: int = 10,
) -> list[RetrievedPassage]:
    """Generate evidence passages using Azure OpenAI when VS is unavailable."""
    import json as _json
    import hashlib

    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    combined_query = "; ".join(queries)

    prompt = (
        "You are a medical evidence retrieval system. Given the clinical query below, "
        "generate evidence-based passages that a physician would find in PubMed.\n\n"
        "For each passage, provide real published findings with accurate DOIs when possible.\n"
        "Return a JSON array of objects, each with:\n"
        '- "text": a 2-3 sentence evidence passage (clinical facts, not opinions)\n'
        '- "doi": a real DOI if you know one, otherwise null\n'
        '- "journal": the journal name\n'
        '- "year": publication year\n'
        '- "section": "Evidence Summary"\n\n'
        f"Generate {min(top_k, 8)} passages.\n\n"
        f"Clinical query: {combined_query}"
    )

    raw = client.chat(
        deployment="mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    if not raw:
        return []

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        items = _json.loads(raw)
    except (_json.JSONDecodeError, ValueError):
        logger.warning("Azure evidence generation returned non-JSON: %s", raw[:200])
        return []

    passages = []
    for i, item in enumerate(items):
        text = item.get("text", "")
        if not text:
            continue
        chunk_id = hashlib.md5(f"azure_evidence_{i}_{text[:50]}".encode()).hexdigest()
        passages.append(RetrievedPassage(
            chunk_id    = chunk_id,
            doi         = item.get("doi"),
            journal     = item.get("journal"),
            year        = int(item["year"]) if item.get("year") else None,
            section     = item.get("section", "Evidence Summary"),
            cluster_tag = None,
            text        = text,
            score       = 1.0 - (i * 0.05),  # descending relevance
        ))

    logger.info(f"Azure evidence generation returned {len(passages)} passages")
    return passages
