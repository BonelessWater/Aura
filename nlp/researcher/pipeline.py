"""
Researcher Pipeline — The Researcher (Phase 3 orchestrator).

Given a patient bundle (lab report + interview result), retrieves
the top-10 most clinically relevant PubMed passages with DOI provenance.

Usage:
    from nlp.researcher.pipeline import run_researcher
    result = run_researcher(patient_id="P001", lab_report=lab, interview_result=interview)
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import (
    Cluster,
    InterviewResult,
    LabReport,
    ResearchResult,
    RetrievedPassage,
)
from nlp.shared.thought_stream import ThoughtStream
from nlp.researcher.retriever import formulate_queries, retrieve_passages
from nlp.researcher.reranker import rerank

logger = logging.getLogger(__name__)


def run_researcher(
    patient_id:       str,
    lab_report:       Optional[LabReport]       = None,
    interview_result: Optional[InterviewResult] = None,
    cluster_hint:     Optional[Cluster]         = None,
) -> ResearchResult:
    """
    Full RAG pipeline. Returns a ResearchResult with top-10 passages.

    Steps:
      1. Formulate 3-5 sub-queries from patient data
      2. Vector Search (top-50 per query)
      3. MedCPT re-ranking → top-10
    """
    ThoughtStream.emit(
        agent="The Researcher",
        step="start",
        summary=f"Formulating queries for patient {patient_id}",
        patient_id=patient_id,
    )

    # ── Step 1: Query formulation ─────────────────────────────────────────────
    queries = formulate_queries(lab_report, interview_result)
    logger.info(f"Formulated {len(queries)} sub-queries: {queries}")

    # ── Step 2: Vector retrieval ──────────────────────────────────────────────
    candidates = retrieve_passages(queries, cluster_filter=cluster_hint)

    if not candidates:
        ThoughtStream.emit(
            agent="The Researcher",
            step="retrieval_empty",
            summary="No passages retrieved — Vector Search may be empty or unavailable",
            patient_id=patient_id,
        )
        return ResearchResult(
            patient_id  = patient_id,
            sub_queries = queries,
            passages    = [],
        )

    ThoughtStream.emit(
        agent="The Researcher",
        step="retrieval",
        summary=f"Retrieved {len(candidates)} candidate passages from Vector Search",
        patient_id=patient_id,
    )

    # ── Step 3: Re-ranking ────────────────────────────────────────────────────
    primary_query = queries[0]
    top_passages  = rerank(primary_query, candidates, top_k=10)

    # Deduplicate by DOI
    seen_dois: set[str] = set()
    deduped: list[RetrievedPassage] = []
    for p in top_passages:
        doi_key = p.doi or p.chunk_id
        if doi_key not in seen_dois:
            seen_dois.add(doi_key)
            deduped.append(p)

    unique_dois   = [p.doi for p in deduped if p.doi]
    cluster_tags  = list({p.cluster_tag.value for p in deduped if p.cluster_tag})

    ThoughtStream.emit(
        agent="The Researcher",
        step="reranking",
        summary=(
            f"Top {len(deduped)} passages retrieved. "
            f"DOIs: {unique_dois[:3]}{'...' if len(unique_dois) > 3 else ''}. "
            f"Cluster tags: {cluster_tags}."
        ),
        patient_id=patient_id,
    )

    return ResearchResult(
        patient_id  = patient_id,
        sub_queries = queries,
        passages    = deduped,
    )
