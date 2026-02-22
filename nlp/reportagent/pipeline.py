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

    ThoughtStream.emit(
        agent="Report Agent", step="complete",
        summary=(
            f"Report generated: "
            f"{len(report.highlighted_lab_panels)} highlighted panels, "
            f"{len(report.bibliography)} citations, "
            f"quality={quality['tier']}"
        ),
        patient_id=person_id,
    )

    return report


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
