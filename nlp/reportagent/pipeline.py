"""
Report Agent Pipeline Orchestrator.

End-to-end flow:
  1. Hydrate PatientBundle from Databricks (data_hydrator)
  2. Run Researcher (RAG retrieval + MedCPT reranking)
  3. Retrieval quality gate (CRAG-inspired confidence check)
  4. Run Router (cluster alignment + disease scoring)
  5. Run Report Agent (PydanticAI -- autonomous report generation)

All pipeline steps except #5 are deterministic Python.
The agent adds autonomous reasoning only at the synthesis step.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from nlp.reportagent.agent import REPORT_MODEL, MAX_TOOL_CALLS, ReportDeps, report_agent
from nlp.reportagent.data_hydrator import hydrate_patient
from nlp.reportagent.retrieval_gate import assess_retrieval_quality
from nlp.reportagent.schemas import MedicalResearchReport
from nlp.shared.schemas import PatientBundle
from nlp.shared.thought_stream import ThoughtStream

logger = logging.getLogger(__name__)


async def generate_report(person_id: str) -> MedicalResearchReport:
    """
    End-to-end report generation for a person_id.

    Args:
        person_id: The patient identifier to generate a report for.

    Returns:
        A validated MedicalResearchReport.

    Raises:
        ValueError: If person_id format is invalid.
        RuntimeError: If patient data not found in Databricks.
    """
    from nlp.shared.databricks_client import get_client

    # Phase 1: Hydrate
    ThoughtStream.emit(
        agent="Report Agent", step="hydrate",
        summary=f"Loading patient data for {person_id} from Databricks",
        patient_id=person_id,
    )
    bundle = await asyncio.to_thread(hydrate_patient, person_id)

    # Phase 2: Research (reuse existing pipeline)
    ThoughtStream.emit(
        agent="Report Agent", step="research",
        summary="Running RAG retrieval against PubMed vector index",
        patient_id=person_id,
    )
    from nlp.researcher.pipeline import run_researcher
    research_result = await asyncio.to_thread(
        run_researcher, person_id, bundle.lab_report, bundle.interview_result, None,
    )
    bundle.research_result = research_result

    # Phase 3: Retrieval quality gate
    quality = assess_retrieval_quality(research_result)
    ThoughtStream.emit(
        agent="Report Agent", step="quality_gate",
        summary=(
            f"Retrieval confidence: {quality['confidence']:.2f} ({quality['tier']}). "
            f"Action: {quality['action']}. {quality['passage_count']} passages."
        ),
        patient_id=person_id,
    )

    if quality["action"] == "widen_search":
        # Re-run without cluster filter to broaden results
        ThoughtStream.emit(
            agent="Report Agent", step="widen_search",
            summary="Low confidence -- re-running search without cluster filter",
            patient_id=person_id,
        )
        wider_result = await asyncio.to_thread(
            run_researcher, person_id, bundle.lab_report, bundle.interview_result, None,
        )
        # Merge: keep originals + add new unique passages
        seen = {p.chunk_id for p in research_result.passages}
        for p in wider_result.passages:
            if p.chunk_id not in seen:
                research_result.passages.append(p)
                seen.add(p.chunk_id)
        bundle.research_result = research_result

    # Phase 4: Route (reuse existing pipeline)
    ThoughtStream.emit(
        agent="Report Agent", step="route",
        summary="Scoring cluster alignment and disease candidates",
        patient_id=person_id,
    )
    from nlp.router.pipeline import run_router
    router_output = await asyncio.to_thread(
        run_router, person_id,
        bundle.lab_report, bundle.interview_result, bundle.research_result,
        [], 40, "U",    # no medications, default age/sex
    )
    bundle.router_output = router_output

    # Phase 5: Agentic report generation
    ThoughtStream.emit(
        agent="Report Agent", step="generate",
        summary="Agent is analyzing data and generating research report",
        patient_id=person_id,
    )
    deps = ReportDeps(
        patient_id=person_id,
        bundle=bundle,
        databricks=get_client(),
    )

    result = await report_agent.run(
        user_prompt=_build_agent_prompt(bundle, quality),
        deps=deps,
        model=REPORT_MODEL,
    )

    report = result.output

    # Phase 6: Hardening -- enrich QualityMetrics
    report = _apply_hardening(report, result, bundle, quality, deps, person_id)

    # Phase 7: Delta storage (best-effort)
    _store_to_delta(report, get_client(), person_id)

    ThoughtStream.emit(
        agent="Report Agent", step="complete",
        summary=(
            f"Report generated: "
            f"{len(report.highlighted_lab_panels)} highlighted panels, "
            f"{len(report.bibliography)} citations, "
            f"quality={quality['tier']}, "
            f"faithfulness={report.quality_metrics.faithfulness_score:.2f}"
        ),
        patient_id=person_id,
    )

    return report


def _apply_hardening(report, result, bundle, quality, deps, person_id):
    """
    Post-generation quality enrichment.

    1. Faithfulness check (reuse nlp/translator/faithfulness_checker.py)
    2. FK grade level on executive summary
    3. Token tracking from PydanticAI result.usage()
    4. Passage count reconciliation
    """
    # -- Faithfulness check --
    try:
        from nlp.translator.faithfulness_checker import check_faithfulness

        passages = bundle.research_result.passages if bundle.research_result else []
        text_to_check = (
            report.executive_summary
            + " " + report.key_findings.content
            + " " + report.bio_fingerprint_summary
        )
        _passed, _flagged, mean_score = check_faithfulness(text_to_check, passages)
        report.quality_metrics.faithfulness_score = mean_score
        logger.info(
            "Faithfulness check for %s: score=%.3f passed=%s flagged=%d",
            person_id, mean_score, _passed, len(_flagged),
        )
    except Exception as e:
        logger.warning("Faithfulness check failed for %s: %s", person_id, e)

    # -- FK grade level on executive summary --
    try:
        import textstat
        fk = textstat.flesch_kincaid_grade(report.executive_summary)
        report.quality_metrics.fk_grade_level = round(fk, 1)
        logger.info("FK grade level for %s: %.1f", person_id, fk)
    except ImportError:
        logger.warning("textstat not installed, skipping FK grade level check")
    except Exception as e:
        logger.warning("FK grade level check failed for %s: %s", person_id, e)

    # -- Token tracking from PydanticAI --
    try:
        usage = result.usage()
        total_tokens = (usage.request_tokens or 0) + (usage.response_tokens or 0)
        report.quality_metrics.total_tokens = total_tokens
        logger.info("Token usage for %s: %d total", person_id, total_tokens)
    except Exception as e:
        logger.warning("Token tracking failed for %s: %s", person_id, e)

    # -- Tool call count --
    report.quality_metrics.tool_calls_used = deps.tool_call_count

    # -- Passage counts --
    passages = bundle.research_result.passages if bundle.research_result else []
    report.quality_metrics.passages_retrieved = len(passages)
    report.quality_metrics.retrieval_confidence = quality["confidence"]

    # Count unique DOIs cited in bibliography
    cited_dois = {c.doi for c in report.bibliography if c.doi}
    report.quality_metrics.passages_cited = len(cited_dois)

    # -- Generated timestamp --
    report.generated_at = datetime.now(timezone.utc).isoformat()

    return report


def _store_to_delta(report, db, person_id):
    """
    Store report to aura.reports.generated Delta table for audit trail.
    Best-effort -- failures are logged but do not block report return.
    """
    try:
        import json
        report_json = json.dumps(report.model_dump(mode="json"))
        sql = (
            "INSERT INTO aura.reports.generated "
            "(patient_id, generated_at, report_json) "
            f"VALUES ('{person_id}', '{report.generated_at}', '{report_json}')"
        )
        db.run_sql(sql, desc=f"store report for {person_id}")
        logger.info("Report stored in Delta for %s", person_id)
    except Exception as e:
        logger.warning(
            "Failed to store report in Delta for %s: %s", person_id, e
        )


def _build_agent_prompt(bundle: PatientBundle, quality: dict) -> str:
    """
    Serialize the PatientBundle into a structured prompt for the agent.

    Follows token-budget discipline from Medical-Graph-RAG:
    ~30% lab data, ~30% research evidence, ~20% router scores, ~20% metadata.

    Places highest-relevance passages first and last to avoid
    lost-in-the-middle effect (MedRAG finding).
    """
    parts = [f"Generate a MedicalResearchReport for patient {bundle.patient_id}.\n"]
    parts.append(f"Retrieval confidence: {quality['confidence']:.2f} ({quality['tier']})")
    parts.append("")

    # Lab data (~30% of prompt budget)
    if bundle.lab_report:
        fp = bundle.lab_report.bio_fingerprint
        parts.append("== BIO-FINGERPRINT ==")
        for ratio_name in ["NLR", "PLR", "MLR", "SII", "CRP_Albumin", "C3_C4"]:
            ratio_data = getattr(fp, ratio_name, [])
            if ratio_data:
                latest = ratio_data[-1]
                parts.append(f"  {ratio_name}: {latest.value:.2f} (flag: {latest.flag})")
        if fp.sustained_abnormalities:
            parts.append(f"  Sustained abnormalities: {', '.join(fp.sustained_abnormalities)}")
        if fp.morphological_shifts:
            parts.append(f"  Morphological shifts: {', '.join(fp.morphological_shifts)}")

        parts.append(f"\n== LAB MARKERS ({len(bundle.lab_report.markers)} timelines) ==")
        for m in bundle.lab_report.markers[:12]:
            latest = m.values[-1] if m.values else None
            if latest:
                parts.append(
                    f"  {m.display_name}: {latest.value} {latest.unit} "
                    f"[{latest.flag.value}] trend={m.trend.value if m.trend else 'unknown'}"
                )

    # Router scores (~20%)
    if bundle.router_output:
        ro = bundle.router_output
        parts.append(f"\n== CLUSTER ALIGNMENT ==")
        parts.append(f"  Cluster: {ro.cluster.value} at {ro.cluster_alignment_score:.0%}")
        parts.append(f"  Routing recommendation: {ro.routing_recommendation}")
        parts.append("  Disease candidates:")
        for dc in ro.disease_candidates[:5]:
            parts.append(
                f"    {dc.disease}: {dc.disease_alignment_score:.0%} "
                f"({dc.criteria_count} criteria met)"
            )

    # Research passages (~30%, ordered by relevance, best first and last)
    if bundle.research_result and bundle.research_result.passages:
        passages = bundle.research_result.passages
        parts.append(f"\n== RESEARCH EVIDENCE ({len(passages)} passages) ==")

        # Reorder: best first, worst middle, second-best last (anti-lost-in-middle)
        if len(passages) > 2:
            reordered = [passages[0]] + passages[2:] + [passages[1]]
        else:
            reordered = passages

        for i, p in enumerate(reordered):
            doi_str = f"doi:{p.doi}" if p.doi else "no-DOI"
            parts.append(
                f"  [{i+1}] [{p.score:.3f}] {p.text[:400]}... "
                f"({p.journal or 'unknown'}, {p.year or '?'}) {doi_str}"
            )

    return "\n".join(parts)
