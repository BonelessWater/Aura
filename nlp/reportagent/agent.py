"""
PydanticAI agent for medical research report generation.

Follows patterns from:
  - .research-refs/pydantic-ai/examples/pydantic_ai_examples/bank_support.py
    (dataclass deps, @agent.instructions, @agent.tool with RunContext)
  - .research-refs/pydantic-ai/examples/pydantic_ai_examples/data_analyst.py
    (ModelRetry for tool validation, tool call budgeting)

The agent autonomously decides which lab panels to highlight, whether to
pull additional research, and how to structure the report. All other
pipeline steps (extraction, research, routing) are deterministic Python.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, ModelRetry, RunContext

from nlp.reportagent.schemas import MedicalResearchReport
from nlp.shared.schemas import PatientBundle

logger = logging.getLogger(__name__)

REPORT_MODEL = os.environ.get(
    "AURA_REPORT_MODEL", "azure:claude-sonnet"
)
MAX_TOOL_CALLS = int(os.environ.get("AURA_REPORT_MAX_TOOLS", "5"))


@dataclass
class ReportDeps:
    """Runtime dependencies injected into the agent (FastAPI-style DI).

    Pattern from bank_support.py: SupportDependencies(customer_id, db).
    """
    patient_id:      str
    bundle:          PatientBundle
    databricks:      Any                       # DatabricksClient singleton
    tool_call_count: int = 0                   # tracks autonomy budget
    cache:           dict = field(default_factory=dict)  # memoize tool results


report_agent = Agent(
    output_type=MedicalResearchReport,
    deps_type=ReportDeps,
    retries=2,
)


# ── Dynamic system prompt ────────────────────────────────────────────────────
# Pattern from bank_support.py: @support_agent.instructions with RunContext


@report_agent.instructions
async def build_system_prompt(ctx: RunContext[ReportDeps]) -> str:
    """Inject patient-specific context into the system prompt at runtime."""
    patient_id = ctx.deps.patient_id

    prompt_parts = [
        "You are a medical research report generator for the Aura autoimmune screening platform.",
        "",
        "RULES:",
        "1. This is NOT a diagnosis. Frame everything as alignment scores and probability flags.",
        "2. Every factual claim requires a DOI citation from the retrieved evidence.",
        "3. Do not speculate beyond the provided data and evidence.",
        "4. Highlight the 3-5 most clinically significant lab panels with interpretation.",
        "5. Compare to the most relevant demo case if the patient's profile is similar.",
        "6. Write the executive summary at a Flesch-Kincaid grade level <= 10.",
        "7. Use pull_additional_research if initial evidence is insufficient for a finding.",
        "8. Use get_lab_panel_detail to drill into any biomarker that appears clinically significant.",
        f"9. You have a budget of {MAX_TOOL_CALLS} tool calls. Use them wisely.",
        "",
        "REPORT STRUCTURE (required sections):",
        "- executive_summary: 2-3 sentences, plain language, no jargon",
        "- key_findings: organized by medical concept, each with DOI citations",
        "- cross_study_patterns: patterns appearing across multiple PubMed studies",
        "- knowledge_gaps: what the evidence does NOT cover for this patient's profile",
        "- evidence_quality: assess study types, sample sizes, journal quality",
        "- highlighted_lab_panels: 3-5 most clinically significant biomarkers",
        "- bio_fingerprint_summary: narrative of NLR, PLR, MLR, SII, CRP/Alb, C3/C4 ratios",
        "- bibliography: all cited passages with DOIs",
        "",
        "DEMO CASES FOR COMPARISON:",
        "  harvard_08670 (Systemic -- lupus/RA profile)",
        "  nhanes_90119  (GI -- inflammatory bowel profile)",
        "  nhanes_73741  (Nuanced -- mixed signals)",
        "  nhanes_79163  (Healthy -- normal baselines)",
        "",
        f"PATIENT: {patient_id}",
    ]

    return "\n".join(prompt_parts)


# ── Tools ─────────────────────────────────────────────────────────────────────
# Pattern from bank_support.py: @agent.tool with RunContext[DepsType]
# Budget enforcement from data_analyst.py: ModelRetry on invalid refs


@report_agent.tool
async def pull_additional_research(
    ctx: RunContext[ReportDeps],
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """Run a targeted follow-up RAG query against the PubMed vector index.

    Use when initial evidence is insufficient for a specific claim.
    Formulate a focused biomedical query (e.g. "elevated NLR ratio systemic lupus erythematosus").

    Args:
        query: A focused biomedical search query.
        max_results: Number of top passages to return (default 5).
    """
    if ctx.deps.tool_call_count >= MAX_TOOL_CALLS:
        return [{"warning": "Tool call budget exhausted. Use existing evidence."}]
    ctx.deps.tool_call_count += 1

    cache_key = f"research:{query}"
    if cache_key in ctx.deps.cache:
        return ctx.deps.cache[cache_key]

    from nlp.researcher.retriever import retrieve_passages
    from nlp.researcher.reranker import rerank

    passages = retrieve_passages([query], top_k=20)
    reranked = rerank(query, passages, top_k=max_results)
    result = [p.model_dump() for p in reranked]
    ctx.deps.cache[cache_key] = result
    return result


@report_agent.tool
async def get_lab_panel_detail(
    ctx: RunContext[ReportDeps],
    marker_name: str,
) -> dict:
    """Get full timeline detail for a specific biomarker from the patient's lab report.

    Use to drill into a marker that appears clinically significant.
    Returns all historical values, trends, and reference ranges.

    Args:
        marker_name: Display name of the biomarker (e.g. "CRP", "ANA", "WBC").
    """
    bundle = ctx.deps.bundle
    if not bundle.lab_report:
        return {"error": "No lab report available"}

    for timeline in bundle.lab_report.markers:
        if marker_name.lower() in timeline.display_name.lower():
            return timeline.model_dump()
    return {"error": f"Marker '{marker_name}' not found in lab report"}


@report_agent.tool
async def get_demo_case_context(
    ctx: RunContext[ReportDeps],
    case_id: str,
) -> dict:
    """Load a reference demo case for comparison.

    Available cases:
      harvard_08670 (systemic), nhanes_90119 (GI),
      nhanes_73741 (nuanced), nhanes_79163 (healthy).

    Args:
        case_id: The patient_id of the demo case to load.
    """
    valid_cases = {"harvard_08670", "nhanes_90119", "nhanes_73741", "nhanes_79163"}
    if case_id not in valid_cases:
        return {"error": f"Invalid case_id. Choose from: {valid_cases}"}

    if ctx.deps.tool_call_count >= MAX_TOOL_CALLS:
        return {"warning": "Tool call budget exhausted."}
    ctx.deps.tool_call_count += 1

    cache_key = f"demo:{case_id}"
    if cache_key in ctx.deps.cache:
        return ctx.deps.cache[cache_key]

    db = ctx.deps.databricks
    rows = db.run_sql(
        f"SELECT * FROM aura.patients.lab_timeseries "
        f"WHERE patient_id = '{case_id}' LIMIT 100"
    )
    result = {"case_id": case_id, "lab_rows": rows} if rows else {"error": f"Case {case_id} not found"}
    ctx.deps.cache[cache_key] = result
    return result


@report_agent.tool
async def get_population_baseline(
    ctx: RunContext[ReportDeps],
    marker_name: str,
) -> dict:
    """Get NHANES population baseline statistics for a biomarker.

    Use to contextualize whether a patient's value is unusual relative
    to the general population.

    Args:
        marker_name: The biomarker name (e.g. "NLR", "CRP", "Hemoglobin").
    """
    cache_key = f"baseline:{marker_name}"
    if cache_key in ctx.deps.cache:
        return ctx.deps.cache[cache_key]

    db = ctx.deps.databricks
    rows = db.run_sql(
        f"SELECT percentile_25, median, percentile_75, mean, std_dev "
        f"FROM aura.reference.nhanes_baselines "
        f"WHERE marker_name = '{marker_name}' LIMIT 1"
    )
    if not rows:
        return {"error": f"No NHANES baseline for '{marker_name}'"}
    cols = ["percentile_25", "median", "percentile_75", "mean", "std_dev"]
    result = dict(zip(cols, rows[0]))
    ctx.deps.cache[cache_key] = result
    return result


# ── Output validators ─────────────────────────────────────────────────────────
# Pattern: ModelRetry from data_analyst.py for structured feedback to the LLM


@report_agent.output_validator
async def validate_no_diagnostic_language(
    ctx: RunContext[ReportDeps],
    output: MedicalResearchReport,
) -> MedicalResearchReport:
    """Ensure the report contains no diagnostic language.

    Inspired by Multi-Agent-Medical-Assistant guardrails pattern.
    """
    forbidden_phrases = [
        "patient has", "diagnosed with", "suffering from",
        "confirmed diagnosis", "definitive diagnosis",
    ]
    text_to_check = (
        output.executive_summary
        + output.key_findings.content
        + output.bio_fingerprint_summary
    )
    for phrase in forbidden_phrases:
        if phrase.lower() in text_to_check.lower():
            raise ModelRetry(
                f"Report contains diagnostic language: '{phrase}'. "
                "Rewrite using alignment scores and probability flags only. "
                "Example: 'X% Systemic Cluster Alignment' instead of 'patient has lupus'."
            )
    return output


@report_agent.output_validator
async def validate_citations_present(
    ctx: RunContext[ReportDeps],
    output: MedicalResearchReport,
) -> MedicalResearchReport:
    """Ensure every research finding section has at least one DOI citation.

    Inspired by Self-RAG support assessment pattern.
    """
    for section_name in ["key_findings", "cross_study_patterns", "evidence_quality"]:
        section = getattr(output, section_name)
        if section.citations:
            dois = [c.doi for c in section.citations if c.doi]
            if not dois:
                raise ModelRetry(
                    f"Section '{section.heading}' has citations but none with DOIs. "
                    "Every citation must include a DOI from the retrieved PubMed evidence."
                )
    return output
