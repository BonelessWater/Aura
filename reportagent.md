# Report Agent -- Agentic Architecture Plan

## Prime Directive: Copy-Then-Edit from Reference Repos

We are built on the shoulders of giants. Six reference repos are cloned in `.research-refs/`. **NEVER write code from scratch when a reference implementation exists.**

When building a component:

1. **FIND** the closest implementation in `.research-refs/` (e.g. CRAG logic from `RAG_Techniques/`, scoring from `pubmed-rag/`, RRF from `MedRAG/`)
2. **COPY** the source file to our target location using `cp`
3. **READ** the copied file in its new location
4. **EDIT** only what needs to change (imports, schemas, Databricks integration, naming)

This prevents transcription errors, preserves battle-tested logic, and keeps us honest about provenance. If you are typing 50+ lines of new logic and a reference exists, you are doing it wrong.

**Reference map:**

| Component | Copy from | Key file(s) |
|-----------|-----------|-------------|
| CRAG confidence gate | `RAG_Techniques/` | `all_rag_techniques_runnable_scripts/crag.py` |
| Self-RAG validation | `RAG_Techniques/` | `all_rag_techniques_runnable_scripts/self_rag.py` |
| RRF fusion (future) | `MedRAG/` | `src/utils.py` (merge function) |
| Multi-factor scoring | `pubmed-rag/` | `PubMed_RAG_Data_Scientist_Example.ipynb` |
| Report template | `pubmed-rag/` | 11-section template in notebook |
| PydanticAI agent patterns | `pydantic-ai/` | `examples/pydantic_ai_examples/` |
| Confidence routing | `Multi-Agent-Medical-Assistant/` | `agents/agent_decision.py` |
| Evidence grounding | `Medical-Graph-RAG/` | `nano_graphrag/_op.py` |

---

## Goal

Build an agentic report generation system that takes a `person_id`, pulls their data from Databricks, runs RAG against the PubMed vector index, and produces a presentation-ready medical research report. The agent autonomously decides what additional research to pull, which lab panels to highlight, and how to structure the final output.

---

## Architecture Decision: PydanticAI

**Framework**: [PydanticAI](https://github.com/pydantic/pydantic-ai) (~15k stars, MIT, v1.0+)

**Why PydanticAI over alternatives:**

| Criterion | PydanticAI | CrewAI | LangGraph |
|-----------|-----------|--------|-----------|
| Schema compatibility | Native (same team as Pydantic) | `output_pydantic` adapter | BaseModel state support |
| FastAPI integration | Identical patterns (DI, async) | No native SSE | Documented but heavier |
| Deterministic pipeline fit | Wraps only LLM steps | Forces all steps into LLM agents | Forces graph abstraction |
| SSE streaming | `agent.run_stream()` + partial output | Not native | Via `astream_events()` |
| Dependency footprint | 1 package | 1 package + hidden deps | LangChain ecosystem |
| Learning curve | Minimal (FastAPI devs know it) | New abstractions (Crew/Task/Agent) | Graph state model |

**Key insight**: Our Extractor, Interviewer, Researcher, and Router are deterministic Python code -- not LLM reasoning. Only the report generation step benefits from agentic behavior. PydanticAI lets us surgically add agency where it helps without rewriting the existing pipeline.

### Confirmed by Code Review of PydanticAI Source

Reference: `.research-refs/pydantic-ai/`

1. **Agent parameterization**: `Agent[DepsType, OutputType]` -- our `ReportDeps` and `MedicalResearchReport` slot in directly. Source: `pydantic_ai_slim/pydantic_ai/agent/wrapper.py`.
2. **Tool registration**: `@agent.tool` with `RunContext[DepsType]` as first param -- identical to FastAPI's `Depends` pattern. Source: `pydantic_ai_slim/pydantic_ai/tools.py`.
3. **Output validation**: `@agent.output_validator` can raise `ModelRetry` to force the LLM to regenerate with feedback. Critical for ensuring no diagnostic language leaks into reports. Source: `pydantic_ai_slim/pydantic_ai/exceptions.py`.
4. **Streaming**: `agent.run_stream()` yields partial structured output via `response.stream_output()`. Integrates with our SSE/ThoughtStream. Source: `pydantic_ai_slim/pydantic_ai/result.py`.
5. **Dynamic system prompts**: `@agent.instructions` decorator accepts `RunContext` -- we can inject patient-specific context at runtime without string formatting. Source: `examples/pydantic_ai_examples/data_analyst.py`.
6. **Multi-agent composition**: Child agents can be called from within tools with `usage=ctx.usage` for cumulative token tracking. Source: `examples/pydantic_ai_examples/question_graph.py`.

---

## Lessons from Reference Implementations

Six open-source repositories were cloned and studied (`.research-refs/`). Key architectural patterns extracted:

### From google/pubmed-rag (Production at Princess Maxima Center for Pediatric Oncology)

Reference: `.research-refs/pubmed-rag/PubMed_RAG_Data_Scientist_Example.ipynb`

1. **Two-phase analysis**: Phase 1 ranks and filters articles (cheap). Phase 2 does deep LLM analysis only on selected articles (expensive). Reduces token cost while maintaining quality. We should run our existing MedCPT reranking first, then only pass top-10 to the agent.

2. **Dynamic multi-factor article scoring** (15+ configurable criteria):
   - `journal_impact` (25 pts, logarithmic SJR normalization via Scimago)
   - `year_penalty` (-5 pts per year old)
   - `event_match` (15 pts per matching medical concept)
   - `disease_match` (70 pts boolean)
   - `treatment_shown` (80 pts boolean)
   - `clinical_trial` (50 pts boolean)
   - `review_article` (-5 pts penalty)
   We should adopt a simplified version of this scoring for our retrieved passages (journal impact + recency + concept match).

3. **LLM as metadata extractor**: Use LLM to extract structured metadata (title, journal, year, paper_type, key_findings) from retrieved articles, then score algorithmically. Separate extraction from scoring. This is a key pattern: the agent should NOT score articles itself -- it should extract features and let a deterministic scorer rank them.

4. **Temperature discipline**: temperature=0 for extraction/classification, 0.3 for synthesis/report generation. Our agent should use 0.3 for report writing, tools should use 0 for data queries.

5. **11-section report template**: Executive Summary, Key Findings by Concept, Methodological Landscape, Temporal Trends, Cross-Study Patterns, Controversies, Knowledge Gaps, Practical Applications, Quality Assessment, Synthesis, Bibliography. We should adopt a similar comprehensive structure adapted for autoimmune screening.

6. **Persona-driven analysis**: Same literature analyzed from different perspectives (clinician, researcher, patient). Our report could include both a clinical section (for doctors) and a patient-accessible section (reusing our existing Layman's Compass pattern).

7. **Streaming generation**: Report generated via `generate_content_stream()` with token-by-token delivery. Prevents timeouts on long reports and gives users real-time feedback. Map this to PydanticAI's `agent.run_stream()`.

### From Medical-Graph-RAG (ACL 2025)

Reference: `.research-refs/Medical-Graph-RAG/nano_graphrag/_op.py`

1. **Two-stage response generation**: First generate response from self-context (entities within same knowledge subgraph), then refine with cross-references from other layers (adding citations). Adopt this for our report: first draft from patient data + initial RAG, then refine with additional evidence via tool calls.

2. **Dual-mode retrieval (Local + Global)**:
   - Local mode: Entity-centric. Vector search for top-k entities, expand via 1-hop graph neighbors, rank by node degree. Good for specific queries ("what does elevated NLR mean?").
   - Global mode: Community-centric. Map-reduce over community summaries. Good for overview queries ("what autoimmune conditions match this profile?").
   Our agent should formulate both targeted queries (specific biomarker + condition) and broad queries (cluster-level patterns).

3. **Token-budget allocation**: 33% for text chunks, 40% for entity/relationship context, 27% for community summaries. Prevents "lost-in-the-middle" by ensuring diverse context types. We should structure our agent prompt with similar budget discipline.

4. **Evidence grounding format**: `[Data: Entities (id1, id2); Relationships (id3)]` -- every claim tagged with source IDs. We should adopt inline DOI citation format: `[claim] [Author et al., Year](doi:XXXXX)`.

5. **Embedding-based entity merging**: Cosine similarity > 0.6 triggers node merge (handles "HTN" vs "hypertension"). Relevant for our query expansion -- map common abbreviations to LOINC display names before retrieval.

### From Multi-Agent-Medical-Assistant (LangGraph)

Reference: `.research-refs/Multi-Agent-Medical-Assistant/agents/agent_decision.py`

1. **Confidence-based routing**: Calculate retrieval confidence as average of top-3 document `combined_score` values. If below threshold (0.40), automatically hand off to secondary search. We should implement this in our agent: if initial RAG confidence is low, the `pull_additional_research` tool fires automatically rather than waiting for the agent to decide.

2. **Insufficient info detection**: Check response text for phrases like "I don't have enough information" and set `insufficient_info=True` to trigger follow-up retrieval. Build this into our output validator.

3. **Prompt-based guardrails** (no external dependency): LLM checks both input safety and output safety via system prompt rules. Our report agent should validate that output contains no diagnostic language ("patient has X"), only alignment scores ("X% cluster alignment"). Implement as `@agent.output_validator`.

4. **Per-component temperature strategy**:
   - Decision/routing: 0.1 (deterministic)
   - Response generation: 0.3 (factual + natural)
   - Conversation: 0.7 (engaging)
   - Semantic chunking: 0.0 (precise)
   Our report agent should use 0.3 for synthesis. Tool calls for data retrieval should be deterministic (no LLM temperature needed -- they're Python functions).

5. **Hybrid retrieval (BM25 + dense vectors)**: Qdrant HYBRID mode combines sparse keyword search with dense embedding search. Combined score = `(original_score + rerank_score) / 2`. We should explore adding BM25 to our Databricks Vector Search pipeline.

### From MedRAG (Stanford/NCBI)

Reference: `.research-refs/MedRAG/src/utils.py`, `.research-refs/MedRAG/src/medrag.py`

1. **Reciprocal Rank Fusion (RRF)**: Combine BM25 + MedCPT + Contriever results using `score = 1 / (rrf_k + rank + 1)` with `rrf_k=100`. Significantly outperforms any single retriever (up to 18% accuracy gain). We should add BM25 alongside our existing MedCPT semantic search.

2. **MedCPT dual-model architecture**: MedRAG uses separate encoders -- `ncbi/MedCPT-Query-Encoder` for queries and `ncbi/MedCPT-Article-Encoder` for documents. Both use CLS pooling (not MEAN). Aura currently uses `pritamdeka/S-PubMedBert-MS-MARCO` with default MEAN pooling. Switching to MedCPT's asymmetric encoders could improve retrieval quality by 15-25% on biomedical queries.

3. **Multi-corpus retrieval**: Search PubMed abstracts + StatPearls clinical guidelines + medical textbooks simultaneously. Diversifies evidence quality. StatPearls is particularly valuable for clinical decision support (9.3K curated articles, ~119 tokens/chunk). Consider adding StatPearls as a second corpus for the report agent.

4. **Iterative query generation (i-MedRAG)**: Agent generates 3 follow-up queries per round, accumulates context over up to 4 rounds. Structured as multi-turn conversation history. We should let our agent do up to 3 rounds of follow-up research, tracked via tool call count.

5. **Token-aware context truncation**: Count tokens per model, truncate retrieved context to fit within window while preserving highest-scored passages. Prevents "lost-in-the-middle" degradation where models attend less to middle context. Place highest-relevance passages first and last in the prompt.

6. **Chunk size findings**: MedRAG uses 1000-token chunks with 200-token overlap for research articles (vs our 256/32). Larger chunks preserve more clinical narrative context. For report generation, consider expanding chunk retrieval to include +/- 1 neighbor of each retrieved chunk.

### From RAG_Techniques (24.5k stars, 30+ patterns)

Reference: `.research-refs/RAG_Techniques/all_rag_techniques_runnable_scripts/`

1. **Corrective RAG (CRAG)** (`crag.py`): Three-tier confidence thresholds:
   - Score > 0.7: Use retrieved documents directly
   - Score 0.3-0.7: Supplement with additional sources
   - Score < 0.3: Fall back to web search or alternative corpus
   Build this into the agent's retrieval loop. Map to our pipeline: high confidence = use top-10, medium = trigger `pull_additional_research`, low = widen search to full corpus without cluster filter.

2. **Self-RAG** (`self_rag.py`): Five-stage verification pipeline:
   1. Retrieval decision (is external evidence needed?)
   2. Relevance evaluation (score each document)
   3. Response generation (from relevant context)
   4. Support assessment (is response grounded in sources? Fully/Partially/No)
   5. Utility evaluation (1-5 scale)
   Our output validator should implement stages 4 and 5: check that every section's claims have DOI citations (support) and rate overall report utility.

3. **Fusion retrieval** (`fusion_retrieval.py`): `combined_score = alpha * vector_score + (1 - alpha) * bm25_score`. Recommended alpha values for medical domain:
   - Diagnosis queries: alpha=0.7 (favor semantic)
   - Medication queries: alpha=0.5 (balanced)
   - Lab value queries: alpha=0.3 (favor keyword/exact match)
   Our `pull_additional_research` tool should accept an optional `retrieval_mode` parameter.

4. **Contextual compression** (`contextual_compression.py`): After retrieval, use LLM to extract only query-relevant segments from each passage. Reduces noise and token usage. Particularly valuable for medical records where passages may contain tangential clinical details. Implement as a post-retrieval step before passing context to the report agent.

5. **Query decomposition** (`query_transformations.py`): Three complementary strategies:
   - Query rewriting (vague -> specific)
   - Step-back prompting (specific -> general background)
   - Sub-query decomposition (complex -> 2-4 simpler queries)
   Our existing `formulate_queries()` in `retriever.py` already does sub-query decomposition for lab + symptom data. For the report agent, add step-back queries for each disease candidate to retrieve background context.

---

## System Design

### Data Flow

```
person_id
    |
    v
[Data Hydration Layer]  -- new code
    |  Queries Databricks tables:
    |    - aura.patients.lab_timeseries
    |    - aura.features.bio_fingerprint (Feature Store)
    |    - core_matrix (demographics, diagnosis cluster)
    |    - autoantibody_panel (if available)
    |
    v
PatientBundle (hydrated from DB, not from PDF upload)
    |
    v
[Existing Pipeline]  -- reuse as-is
    |  run_researcher() -- RAG retrieval + MedCPT reranking
    |  run_router()     -- cluster alignment + disease scoring
    |
    v
[Retrieval Quality Gate]  -- new, inspired by CRAG
    |  Calculate confidence = mean(top-3 passage scores)
    |  If confidence < 0.40: widen search (remove cluster filter, expand queries)
    |  If confidence < 0.20: flag as low-evidence report
    |
    v
[Report Agent]  -- new PydanticAI agent
    |  Tools (7):
    |    - pull_additional_research(query, mode)  -- follow-up RAG with fusion retrieval
    |    - get_lab_panel_detail(marker)            -- drill into specific biomarker timelines
    |    - get_demo_case_context(case_id)          -- load reference case for comparison
    |    - get_population_baseline(marker)         -- NHANES reference ranges
    |    - score_passage_relevance(passage_ids)    -- multi-factor article scoring
    |    - expand_medical_query(query)             -- synonym/LOINC expansion
    |    - compress_context(passages, focus)       -- extract relevant segments
    |
    |  Output Validators:
    |    - No diagnostic language check (alignment scores only)
    |    - DOI citation completeness check (every claim needs a source)
    |    - FK grade level check on executive summary (<= 10)
    |
    |  Autonomy (max 5 tool calls per run):
    |    - Decides which lab panels are clinically significant
    |    - Decides if additional research queries are needed (CRAG routing)
    |    - Decides which demo case is most comparable
    |    - Structures the report sections based on findings
    |
    v
MedicalResearchReport (Pydantic model, validated)
    |
    v
[Report Formatter]  -- renders to markdown/HTML
```

### Where It Lives

```
nlp/
  reportagent/
    __init__.py
    schemas.py          -- MedicalResearchReport and section models
    agent.py            -- PydanticAI agent definition + tools + output validators
    data_hydrator.py    -- Databricks queries to build PatientBundle from person_id
    retrieval_gate.py   -- CRAG-inspired confidence check on initial retrieval
    formatter.py        -- Render report to markdown / HTML
    pipeline.py         -- Orchestrator: hydrate -> research -> route -> gate -> agent -> format

backend/
  routers/
    report.py           -- POST /report/{person_id} endpoint

tests/
  test_report_data_hydrator.py  -- data hydration against real Databricks
  test_report_agent.py          -- agent integration tests with demo cases
  test_report_endpoint.py       -- FastAPI endpoint tests
  test_retrieval_gate.py        -- CRAG confidence routing tests
```

---

## Schemas

### New: `nlp/reportagent/schemas.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from nlp.shared.schemas import Cluster, DiseaseCandidate


class LabPanelSummary(BaseModel):
    """Agent-selected lab panel highlights."""
    marker_name:        str
    latest_value:       float
    unit:               str
    reference_range:    str                   # e.g. "3.5-5.0"
    flag:               str                   # HIGH / LOW / NORMAL
    trend:              Optional[str] = None  # stable / escalating / resolving
    clinical_note:      str                   # agent-written interpretation
    z_score:            Optional[float] = None


class EvidenceCitation(BaseModel):
    """A single research finding with provenance."""
    claim:              str
    doi:                Optional[str] = None
    journal:            Optional[str] = None
    year:               Optional[int] = None
    relevance_score:    float
    passage_excerpt:    str                   # supporting text (truncated)


class DemoCaseComparison(BaseModel):
    """Comparison to a known reference case."""
    case_id:            str
    case_label:         str                   # e.g. "Case 1: Systemic"
    similarity_notes:   str                   # agent-written comparison
    shared_markers:     list[str] = Field(default_factory=list)
    divergent_markers:  list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    """One section of the generated report."""
    heading:            str
    content:            str                   # markdown body
    citations:          list[EvidenceCitation] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    """Report quality metadata for audit trail."""
    retrieval_confidence:   float             # mean top-3 passage scores
    faithfulness_score:     float             # NLI grounding check
    fk_grade_level:         Optional[float] = None  # executive summary readability
    tool_calls_used:        int               # how many agent tool calls
    total_tokens:           int               # LLM token consumption
    passages_retrieved:     int               # total passages considered
    passages_cited:         int               # passages actually cited in report


class MedicalResearchReport(BaseModel):
    """The final agentic report output -- validated, structured, presentation-ready."""
    patient_id:                str
    generated_at:              str            # ISO 8601 timestamp

    # Core findings
    executive_summary:         str            # 2-3 sentence overview (FK grade <= 10)
    cluster_alignment:         Cluster
    cluster_alignment_score:   float
    disease_candidates:        list[DiseaseCandidate]

    # Lab analysis (agent-selected highlights)
    highlighted_lab_panels:    list[LabPanelSummary]
    bio_fingerprint_summary:   str            # agent-written narrative of key ratios

    # Research synthesis (inspired by google/pubmed-rag 11-section template)
    key_findings:              ReportSection   # findings organized by medical concept
    cross_study_patterns:      ReportSection   # patterns appearing across multiple studies
    knowledge_gaps:            ReportSection   # what the evidence does NOT cover
    evidence_quality:          ReportSection   # study types, sample sizes, journal quality

    # Comparison
    demo_case_comparison:      Optional[DemoCaseComparison] = None

    # Full bibliography
    bibliography:              list[EvidenceCitation] = Field(default_factory=list)

    # Quality and audit
    quality_metrics:           QualityMetrics
    methodology_note:          str            # how the report was generated

    # Legal
    disclaimer:                str = (
        "This report is a data-backed High Probability Flag for specialist referral. "
        "It is not a diagnosis. Only a qualified physician can diagnose."
    )
```

---

## Agent Definition

### `nlp/reportagent/agent.py`

```python
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
    "AURA_REPORT_MODEL", "anthropic:claude-sonnet-4-20250514"
)
MAX_TOOL_CALLS = int(os.environ.get("AURA_REPORT_MAX_TOOLS", "5"))


@dataclass
class ReportDeps:
    """Runtime dependencies injected into the agent (FastAPI-style DI)."""
    patient_id:     str
    bundle:         PatientBundle
    databricks:     Any                       # DatabricksClient singleton
    tool_call_count: int = 0                  # tracks autonomy budget
    cache:          dict = field(default_factory=dict)  # memoize tool results


report_agent = Agent(
    model=REPORT_MODEL,
    output_type=MedicalResearchReport,
    deps_type=ReportDeps,
    retries=2,                                # retry on schema validation failure
)
```

### Dynamic System Prompt

```python
@report_agent.instructions
async def build_system_prompt(ctx: RunContext[ReportDeps]) -> str:
    """
    Inject patient-specific context into the system prompt.
    Uses PydanticAI's dynamic instructions pattern (not string formatting).
    """
    bundle = ctx.deps.bundle
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
```

### Tools

```python
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
```

### Output Validators

```python
@report_agent.output_validator
async def validate_no_diagnostic_language(
    ctx: RunContext[ReportDeps],
    output: MedicalResearchReport,
) -> MedicalResearchReport:
    """
    Ensure the report contains no diagnostic language.
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
    """
    Ensure every research finding section has at least one DOI citation.
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
```

---

## Retrieval Quality Gate

### `nlp/reportagent/retrieval_gate.py`

Inspired by CRAG (Corrective RAG) and Multi-Agent-Medical-Assistant confidence routing.

```python
import logging
from nlp.shared.schemas import ResearchResult

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE = 0.70
MEDIUM_CONFIDENCE = 0.40
LOW_CONFIDENCE = 0.20


def assess_retrieval_quality(research_result: ResearchResult) -> dict:
    """
    Evaluate retrieval quality using CRAG-inspired three-tier thresholds.

    Returns:
        {
            "confidence": float,
            "tier": "high" | "medium" | "low",
            "action": "proceed" | "supplement" | "widen_search",
            "passage_count": int,
        }
    """
    if not research_result.passages:
        return {
            "confidence": 0.0,
            "tier": "low",
            "action": "widen_search",
            "passage_count": 0,
        }

    # Average of top-3 passage scores (Multi-Agent-Medical-Assistant pattern)
    top_scores = [p.score for p in research_result.passages[:3]]
    confidence = sum(top_scores) / len(top_scores)

    if confidence >= HIGH_CONFIDENCE:
        tier, action = "high", "proceed"
    elif confidence >= MEDIUM_CONFIDENCE:
        tier, action = "medium", "supplement"
    else:
        tier, action = "low", "widen_search"

    logger.info(
        "Retrieval quality gate: confidence=%.3f tier=%s action=%s passages=%d",
        confidence, tier, action, len(research_result.passages),
    )

    return {
        "confidence": confidence,
        "tier": tier,
        "action": action,
        "passage_count": len(research_result.passages),
    }
```

---

## Data Hydration

### `nlp/reportagent/data_hydrator.py`

Builds a `PatientBundle` from a `person_id` by querying Databricks -- no PDF upload needed.

```python
def hydrate_patient(person_id: str) -> PatientBundle:
    """
    Query Databricks to build a full PatientBundle for report generation.

    Tables queried:
      - aura.patients.lab_timeseries   -> MarkerTimeline list
      - aura.features.bio_fingerprint  -> BioFingerprint
      - core_matrix                    -> demographics, diagnosis cluster
      - autoantibody_panel             -> ANA, RF, anti-CCP, C3, C4 (if available)

    Raises:
        RuntimeError: If person_id not found in any table.
    """
```

Steps:
1. Validate `person_id` format (alphanumeric + underscore only -- SQL injection prevention)
2. Query `lab_timeseries` for all rows matching `person_id`, group by LOINC code into `MarkerTimeline` objects, compute trends
3. Query Feature Store for `bio_fingerprint` (NLR, PLR, MLR, SII, CRP/Albumin, C3/C4 ratios)
4. Build `LabReport` from the above
5. Query `core_matrix` for demographics -- used by Router for age/sex-adjusted scoring
6. Return `PatientBundle(patient_id=person_id, lab_report=lab_report)`

---

## Pipeline Orchestrator

### `nlp/reportagent/pipeline.py`

```python
import asyncio
import logging
from datetime import datetime, timezone

from nlp.reportagent.agent import report_agent, ReportDeps
from nlp.reportagent.data_hydrator import hydrate_patient
from nlp.reportagent.retrieval_gate import assess_retrieval_quality
from nlp.reportagent.schemas import MedicalResearchReport
from nlp.shared.databricks_client import get_client
from nlp.shared.schemas import PatientBundle
from nlp.shared.thought_stream import ThoughtStream

logger = logging.getLogger(__name__)


async def generate_report(person_id: str) -> MedicalResearchReport:
    """
    End-to-end report generation for a person_id.

    Flow:
      1. Hydrate PatientBundle from Databricks
      2. Run Researcher (RAG retrieval + MedCPT reranking)
      3. Retrieval quality gate (CRAG-inspired confidence check)
      4. Run Router (cluster alignment + disease scoring)
      5. Run Report Agent (PydanticAI -- autonomous report generation)
    """

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
    )

    ThoughtStream.emit(
        agent="Report Agent", step="complete",
        summary=(
            f"Report generated: "
            f"{len(result.data.highlighted_lab_panels)} highlighted panels, "
            f"{len(result.data.bibliography)} citations, "
            f"quality={quality['tier']}"
        ),
        patient_id=person_id,
    )

    return result.data


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
```

---

## Backend Endpoint

### `backend/routers/report.py`

```python
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.config import Settings, databricks_available, get_settings
from backend.session import get_or_create_session, push_event
from backend.utils.background import create_job, get_job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/report/{person_id}")
async def generate_report_endpoint(
    person_id: str,
    settings: Settings = Depends(get_settings),
):
    """
    Generate a medical research report for a person_id.
    Returns a job_id for async polling via GET /jobs/{job_id}.
    Stream progress via GET /stream/{person_id}.
    """
    if not databricks_available():
        raise HTTPException(
            status_code=503,
            detail="Databricks is required for report generation.",
        )

    job = create_job(person_id)
    get_or_create_session(person_id)

    asyncio.create_task(_run_report(job.job_id, person_id))

    return {"person_id": person_id, "job_id": job.job_id, "status": "queued"}


async def _run_report(job_id: str, person_id: str):
    job = get_job(job_id)
    job.status = "running"

    try:
        from nlp.reportagent.pipeline import generate_report
        report = await generate_report(person_id)

        job.result = report.model_dump(mode="json")
        job.status = "done"
        push_event(person_id, {"type": "done", "job_id": job_id})

    except Exception as exc:
        logger.error(
            "Report generation failed for person_id=%s: %s",
            person_id, exc, exc_info=True,
        )
        job.error = str(exc)
        job.status = "error"
        push_event(
            person_id,
            {"type": "error", "job_id": job_id, "detail": str(exc)},
        )
```

---

## Report Formatter

### `nlp/reportagent/formatter.py`

Renders `MedicalResearchReport` into presentation-ready markdown.
Follows google/pubmed-rag's section template adapted for autoimmune screening.
All citations use clickable DOI links: `[doi:XXXXX](https://doi.org/XXXXX)`.

```python
def render_markdown(report: MedicalResearchReport) -> str:
    """Render the report as presentation-ready markdown."""
    lines = []

    # Header
    lines.append("# Medical Research Report")
    lines.append(f"**Patient ID**: {report.patient_id}")
    lines.append(f"**Generated**: {report.generated_at}")
    lines.append(f"**Retrieval Confidence**: {report.quality_metrics.retrieval_confidence:.2f}")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append(report.executive_summary)
    lines.append("")

    # 2. Cluster Alignment
    lines.append("## 2. Cluster Alignment")
    lines.append(
        f"**{report.cluster_alignment.value}** cluster at "
        f"**{report.cluster_alignment_score:.0%}** alignment."
    )
    if report.disease_candidates:
        lines.append("")
        lines.append("| Disease | Alignment | Criteria Met |")
        lines.append("|---------|-----------|-------------|")
        for dc in report.disease_candidates:
            lines.append(
                f"| {dc.disease} | {dc.disease_alignment_score:.0%} | "
                f"{dc.criteria_count} |"
            )
    lines.append("")

    # 3. Key Lab Panel Findings
    lines.append("## 3. Key Lab Panel Findings")
    for panel in report.highlighted_lab_panels:
        lines.append(f"### {panel.marker_name}")
        lines.append(f"- **Value**: {panel.latest_value} {panel.unit} ({panel.flag})")
        lines.append(f"- **Reference Range**: {panel.reference_range}")
        if panel.trend:
            lines.append(f"- **Trend**: {panel.trend}")
        if panel.z_score is not None:
            lines.append(f"- **NHANES Z-Score**: {panel.z_score:.2f}")
        lines.append(f"- **Interpretation**: {panel.clinical_note}")
        lines.append("")

    # 4. Bio-Fingerprint Analysis
    lines.append("## 4. Bio-Fingerprint Analysis")
    lines.append(report.bio_fingerprint_summary)
    lines.append("")

    # 5-8. Research sections
    _render_section(lines, "5", report.key_findings)
    _render_section(lines, "6", report.cross_study_patterns)
    _render_section(lines, "7", report.knowledge_gaps)
    _render_section(lines, "8", report.evidence_quality)

    # 9. Reference Case Comparison
    if report.demo_case_comparison:
        dcc = report.demo_case_comparison
        lines.append("## 9. Reference Case Comparison")
        lines.append(f"**Compared to**: {dcc.case_label} (`{dcc.case_id}`)")
        lines.append("")
        lines.append(dcc.similarity_notes)
        if dcc.shared_markers:
            lines.append(f"- **Shared signals**: {', '.join(dcc.shared_markers)}")
        if dcc.divergent_markers:
            lines.append(f"- **Divergent signals**: {', '.join(dcc.divergent_markers)}")
        lines.append("")

    # 10. Bibliography
    if report.bibliography:
        lines.append("## 10. Bibliography")
        lines.append("")
        for i, c in enumerate(report.bibliography, 1):
            doi_link = f"[doi:{c.doi}](https://doi.org/{c.doi})" if c.doi else "no DOI"
            lines.append(
                f"{i}. {c.claim} -- {c.journal or 'unknown'}, {c.year or '?'}. "
                f"{doi_link} (relevance: {c.relevance_score:.2f})"
            )
        lines.append("")

    # 11. Methodology
    lines.append("## 11. Methodology")
    lines.append(report.methodology_note)
    lines.append("")
    lines.append(
        f"*Passages retrieved: {report.quality_metrics.passages_retrieved}. "
        f"Passages cited: {report.quality_metrics.passages_cited}. "
        f"Tool calls: {report.quality_metrics.tool_calls_used}. "
        f"Tokens used: {report.quality_metrics.total_tokens}.*"
    )
    lines.append("")

    # Disclaimer
    lines.append("---")
    lines.append(f"*{report.disclaimer}*")

    return "\n".join(lines)


def _render_section(lines: list[str], number: str, section):
    """Render a ReportSection with numbered heading and citations."""
    lines.append(f"## {number}. {section.heading}")
    lines.append(section.content)
    if section.citations:
        lines.append("")
        lines.append("**References:**")
        for c in section.citations:
            doi_link = f"[doi:{c.doi}](https://doi.org/{c.doi})" if c.doi else "no DOI"
            lines.append(f"- {c.claim} -- {c.journal or 'unknown'}, {c.year or '?'}. {doi_link}")
    lines.append("")
```

---

## Implementation Order (3 Parallel Terminals)

Three Claude terminals run in parallel: **Bob**, **Joe**, and **Blue**.
Each terminal owns specific files. No two terminals edit the same file.
Sync points are marked with WAIT -- the terminal pauses until the dependency is committed.

### Terminal Ownership (no conflicts)

| Terminal | Owns these files |
|----------|-----------------|
| **Bob** (critical path) | `schemas.py`, `agent.py`, `pipeline.py`, Phase 4 hardening |
| **Joe** (data layer) | `data_hydrator.py`, `retrieval_gate.py`, all test files |
| **Blue** (output layer) | `formatter.py`, `backend/routers/report.py`, `backend/main.py` edit, Delta storage |

### Execution Timeline

```
Time    Bob (critical path)         Joe (data layer)             Blue (output layer)
----    -------------------         ----------------             -------------------
T0      pip install pydantic-ai     Create __init__.py           (idle -- wait for schemas)
        Create schemas.py           Create tests/regressions/
                                    Create tests/conftest.py
                                    (fixtures for report agent)

T1      COMMIT: "schemas.py"        WAIT for schemas.py          WAIT for schemas.py
        ---- sync point ----        ---- sync point ----         ---- sync point ----

T2      Start agent.py              data_hydrator.py             formatter.py
        (imports schemas,           (imports schemas,            (imports schemas only,
         reads pydantic-ai           queries Databricks,          renders markdown,
         examples for patterns)      builds PatientBundle)        11-section template)

T3      agent.py continued          retrieval_gate.py            formatter.py continued
        (tools, validators,         (CRAG confidence gate,       (DOI link rendering,
         dynamic instructions)       copy from RAG_Techniques)    bibliography section)

T4      COMMIT: "agent.py"          COMMIT: "hydrator + gate"    COMMIT: "formatter.py"
        ---- sync point ----        ---- sync point ----         ---- sync point ----

T5      pipeline.py                 Phase 1 tests:               backend/routers/report.py
        (orchestrator, needs         test_report_phase1_          (FastAPI endpoint,
         agent + hydrator + gate)    foundation.py                needs pipeline import
                                    (15 tests: schemas,           but can stub the import
                                     hydrator, gate)              and wire routing)

T6      pipeline.py continued       Run Phase 1 tests            Register router in
        (_build_agent_prompt,       Fix any failures              backend/main.py
         quality gate logic,
         ThoughtStream events)

T7      COMMIT: "pipeline.py"       COMMIT: "Phase 1 tests"      WAIT for pipeline.py
        ---- sync point ----        ---- sync point ----         ---- sync point ----

T8      Phase 4: faithfulness       Phase 2 tests:               COMMIT: "endpoint + router"
        (reuse translator/           test_report_phase2_          Phase 3 tests:
         faithfulness_checker.py)    agent.py                     test_report_phase3_
                                    (13 tests: agent,             api_formatter.py
                                     tools, validators)           (10 tests: formatter,
                                                                   endpoint, SSE)

T9      Phase 4: FK grade level     Run Phase 2 tests            Run Phase 3 tests
        Phase 4: token tracking     Fix any failures             Fix any failures

T10     Phase 4: Delta storage      Phase 4 tests:               (idle or help debug)
        (write to aura.reports.      test_report_phase4_
         generated)                  hardening.py
                                    (9 tests)

T11     COMMIT: "Phase 4"           Run Phase 4 tests            Run end-to-end checklist
                                    Run all 4 demo cases
```

### Phase 1: Foundation

**Bob** creates the shared schemas first (everything depends on this):
1. `pip install pydantic-ai` -- add to `requirements.txt`
2. Create `nlp/reportagent/__init__.py`
3. Create `nlp/reportagent/schemas.py` -- all report Pydantic models
4. COMMIT and push so Joe and Blue can start

**Joe** creates the data layer (after schemas exist):
1. Create `nlp/reportagent/data_hydrator.py` -- Databricks queries to build PatientBundle from person_id
2. Create `nlp/reportagent/retrieval_gate.py` -- CRAG-inspired confidence check (copy from `RAG_Techniques/crag.py`)
3. Create `tests/conftest.py` additions (requires_databricks, requires_llm, requires_backend, DEMO_CASES)
4. Create `tests/test_report_phase1_foundation.py` -- 15 tests
5. Run tests, fix failures
6. COMMIT

**Blue** creates the formatter (after schemas exist, no other deps):
1. Create `nlp/reportagent/formatter.py` -- markdown renderer (11-section template, copy structure from `pubmed-rag/`)
2. COMMIT

### Phase 2: Agent

**Bob** creates the agent and pipeline (after hydrator + gate exist):
1. Create `nlp/reportagent/agent.py` -- PydanticAI agent with tools, output validators, dynamic instructions (copy patterns from `pydantic-ai/examples/`)
2. Create `nlp/reportagent/pipeline.py` -- orchestrator: hydrate -> research -> gate -> agent -> format
3. COMMIT

**Joe** writes and runs Phase 2 tests (after pipeline exists):
1. Create `tests/test_report_phase2_agent.py` -- 13 tests
2. Run tests against real Databricks + real LLM
3. Fix failures, COMMIT

**Blue** creates the API endpoint (after pipeline exists):
1. Create `backend/routers/report.py` -- POST /report/{person_id}
2. Register router in `backend/main.py`
3. COMMIT

### Phase 3: API + Formatter

**Joe** writes and runs Phase 3 tests (after endpoint exists):
1. Create `tests/test_report_phase3_api_formatter.py` -- 10 tests
2. Run tests, fix failures, COMMIT

**Blue** is available to help debug or work on any blocked items.

### Phase 4: Hardening

**Bob** adds quality checks to the pipeline:
1. Add faithfulness checking (reuse `nlp/translator/faithfulness_checker.py`)
2. Add FK grade level check on executive summary
3. Add token tracking to QualityMetrics (via `result.usage()` from PydanticAI)
4. Add Delta storage for report versioning (`aura.reports.generated`)
5. COMMIT

**Joe** writes and runs Phase 4 tests:
1. Create `tests/test_report_phase4_hardening.py` -- 9 tests
2. Run all 4 demo cases, verify quality
3. Run full end-to-end verification checklist
4. COMMIT

**Blue** runs final verification:
1. Run `pytest tests/test_report_phase*.py -v` -- all green
2. Spot-check markdown output for all 4 demo cases
3. Verify Delta table has stored reports

### Phase 5: Retrieval Improvements (Future -- deferred)
1. Add BM25 alongside vector search (RRF fusion, inspired by MedRAG)
2. Consider MedCPT dual-encoder switch (Query-Encoder + Article-Encoder)
3. Add contextual compression for retrieved passages
4. Add StatPearls as second corpus for clinical guidelines
5. Implement i-MedRAG iterative multi-round retrieval

---

## Dependencies

**New packages:**
- `pydantic-ai>=1.0` -- agent framework
- `anthropic` -- LLM provider (or configure for local vLLM)

**Existing packages (no changes):**
- `pydantic`, `pydantic-settings` -- already in use
- `databricks-sdk`, `databricks-vectorsearch` -- already in use
- `sentence-transformers`, `transformers` -- already in use for embeddings/reranking
- `fastapi`, `sse-starlette` -- already in use

---

## LLM Configuration

The report agent needs a capable model for structured output generation.

```python
# Primary: Claude via Azure (paulbobev account)
# Fallback: GPT model via sw Azure account
AURA_REPORT_MODEL = os.environ.get("AURA_REPORT_MODEL", "azure:claude-sonnet")

# Azure configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # paulbobev deployment
AZURE_OPENAI_API_KEY  = os.environ.get("AZURE_OPENAI_API_KEY")
```

Priority:
1. **Claude** (via paulbobev Azure) -- best structured output quality, primary choice
2. **GPT-4o** (via sw Azure account) -- fallback if Claude unavailable
3. **Local vLLM** (Mistral-7B-Instruct) -- already deployed, zero API cost, lowest quality

PydanticAI handles model switching transparently via the model string.

**Temperature strategy** (from Multi-Agent-Medical-Assistant):
- Agent report generation: 0.3 (factual + natural)
- Tool calls: N/A (Python functions, no LLM)

---

## Testing Protocol

### Core Anti-Pattern: NO MOCKED TESTS

This is a hard rule. Mocked tests verify assumptions, not reality. They pass
when the real system is broken and give false confidence.

**What this means in practice:**

- Tests hit the REAL Databricks tables, REAL Vector Search endpoint, REAL LLM API.
- Tests construct REAL `PatientBundle` objects from REAL database queries.
- Tests call the REAL PydanticAI agent with REAL tool execution.
- No `unittest.mock.patch` on internal code. No fake LLM responses. No stubbed
  Databricks clients.

**The only acceptable skip:**

```python
import os
import pytest

@pytest.fixture
def requires_databricks():
    if not os.environ.get("DATABRICKS_HOST"):
        pytest.skip("Databricks not configured")

@pytest.fixture
def requires_llm():
    has_azure = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
    if not (has_azure or has_anthropic or has_vllm):
        pytest.skip("No LLM backend configured")
```

### Bug-Driven Testing Protocol

Bugs found during development are treated as test opportunities, not annoyances.

**Process:**

1. A bug is discovered (hydrator returns wrong schema, agent outputs diagnostic
   language, retrieval gate miscalculates confidence, etc.)
2. BEFORE fixing the bug, write a test that reproduces it. The test MUST FAIL.
3. Fix the bug.
4. Confirm the test now passes.
5. The test lives permanently in `tests/regressions/`. It is never deleted.

**Naming convention:**

```
tests/regressions/test_regression_phase<N>_<short_description>.py
```

Examples:
- `test_regression_phase1_hydrator_missing_bio_fingerprint.py`
- `test_regression_phase2_agent_says_patient_has_lupus.py`
- `test_regression_phase2_retrieval_gate_divides_by_zero_on_empty.py`

**Each regression test file contains:**
- A docstring explaining what the bug was and when it was found
- The exact steps to reproduce
- The fix summary (one line)

```python
"""
Regression: Phase 1 -- Data hydrator returned None for bio_fingerprint when
patient had lab values but no computed ratios in Feature Store.
Found: During Phase 1 development.
Fix: Added fallback to compute ratios from raw markers when Feature Store
     entry is missing.
"""
```

These tests accumulate over time and form a living record of every edge case
the system has encountered. They run with the rest of the suite on every
`pytest` invocation.

### Test Infrastructure

**File:** `tests/conftest.py` (additions for report agent -- extend existing conftest)

```python
import os
import pytest

DEMO_CASES = {
    "systemic":  "harvard_08670",
    "gi":        "nhanes_90119",
    "nuanced":   "nhanes_73741",
    "healthy":   "nhanes_79163",
}


@pytest.fixture
def requires_databricks():
    if not os.environ.get("DATABRICKS_HOST"):
        pytest.skip("Databricks not configured")


@pytest.fixture
def requires_llm():
    has_azure = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
    if not (has_azure or has_anthropic or has_vllm):
        pytest.skip("No LLM backend configured")


@pytest.fixture
def requires_backend():
    """Skip test if FastAPI backend is not running."""
    import httpx
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2)
        if r.status_code != 200:
            pytest.skip("Backend not healthy")
    except httpx.ConnectError:
        pytest.skip("Backend not running")
```

### Test directory structure

```
tests/
  test_report_phase1_foundation.py      -- schemas, hydrator, retrieval gate
  test_report_phase2_agent.py           -- agent, tools, validators, pipeline
  test_report_phase3_api_formatter.py   -- endpoint, markdown renderer
  test_report_phase4_hardening.py       -- faithfulness, FK grade, token tracking
  regressions/
    (bug-driven tests added during development)
```

No phase begins until the previous phase's tests pass.

---

### Phase 1 Tests: Foundation

**File:** `tests/test_report_phase1_foundation.py`

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_report_schemas_import` | `from nlp.reportagent.schemas import MedicalResearchReport, QualityMetrics, ...` resolves | No ImportError |
| 2 | `test_medical_research_report_validates` | Construct `MedicalResearchReport` with all required fields | Pydantic validation passes |
| 3 | `test_lab_panel_summary_validates` | Construct `LabPanelSummary` with sample data | Pydantic validation passes |
| 4 | `test_evidence_citation_validates` | Construct `EvidenceCitation` with DOI and without | Both valid |
| 5 | `test_quality_metrics_validates` | Construct `QualityMetrics` with sample data | Pydantic validation passes |
| 6 | `test_hydrate_patient_returns_bundle` | Call `hydrate_patient("harvard_08670")` against real Databricks | Returns `PatientBundle` with non-None `lab_report` |
| 7 | `test_hydrate_patient_has_markers` | Hydrated bundle has `lab_report.markers` with at least 1 entry | `len(markers) >= 1` |
| 8 | `test_hydrate_patient_has_bio_fingerprint` | Hydrated bundle has `lab_report.bio_fingerprint` | `bio_fingerprint` is not None |
| 9 | `test_hydrate_patient_invalid_id_raises` | Call `hydrate_patient("NONEXISTENT_999")` | Raises `RuntimeError` |
| 10 | `test_hydrate_patient_rejects_sql_injection` | Call `hydrate_patient("'; DROP TABLE--")` | Raises `ValueError` (format validation) |
| 11 | `test_retrieval_gate_high_confidence` | 3 passages scored 0.85, 0.80, 0.75 | tier="high", action="proceed" |
| 12 | `test_retrieval_gate_medium_confidence` | 3 passages scored 0.55, 0.50, 0.45 | tier="medium", action="supplement" |
| 13 | `test_retrieval_gate_low_confidence` | 2 passages scored 0.15, 0.10 | tier="low", action="widen_search" |
| 14 | `test_retrieval_gate_empty_passages` | Empty passage list | confidence=0.0, action="widen_search" |
| 15 | `test_retrieval_gate_single_passage` | 1 passage scored 0.90 | tier="high" (average of 1 score) |

Tests 6-10 require `requires_databricks` fixture. Tests 11-15 are pure logic (no external deps).

**Phase 1 Done Gate:**
- `python -c "from nlp.reportagent.schemas import MedicalResearchReport"` succeeds
- `pytest tests/test_report_phase1_foundation.py` -- all tests green (skip Databricks tests if unavailable)
- Hydration tested with at least 1 demo case against real Databricks

---

### Phase 2 Tests: Agent

**File:** `tests/test_report_phase2_agent.py`

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_agent_imports` | `from nlp.reportagent.agent import report_agent, ReportDeps` resolves | No ImportError |
| 2 | `test_agent_has_tools_registered` | `report_agent` has tools: `pull_additional_research`, `get_lab_panel_detail`, `get_demo_case_context`, `get_population_baseline` | All 4 tool names present |
| 3 | `test_agent_has_output_validators` | Agent has at least 2 output validators registered | `len(validators) >= 2` |
| 4 | `test_report_systemic_case` | `generate_report("harvard_08670")` produces valid `MedicalResearchReport` | Schema validates, `patient_id` matches, `cluster_alignment` not None |
| 5 | `test_report_systemic_has_lab_panels` | Systemic case report has at least 1 highlighted lab panel | `len(highlighted_lab_panels) >= 1` |
| 6 | `test_report_systemic_has_citations` | Key findings section has at least 1 DOI citation | DOI list is non-empty |
| 7 | `test_report_healthy_case_low_alignment` | Healthy case report has cluster_alignment_score < 0.5 | Score below threshold |
| 8 | `test_report_no_diagnostic_language` | Report text does not contain "patient has", "diagnosed with", "suffering from" | No forbidden phrases found |
| 9 | `test_report_has_bibliography` | Report has at least 1 bibliography entry | `len(bibliography) >= 1` |
| 10 | `test_report_quality_metrics_populated` | QualityMetrics has retrieval_confidence >= 0, tool_calls_used >= 0, total_tokens > 0 | All metrics populated |
| 11 | `test_report_tool_call_budget_enforced` | Agent does not exceed MAX_TOOL_CALLS (5) | `quality_metrics.tool_calls_used <= 5` |
| 12 | `test_report_executive_summary_nonempty` | Executive summary is a non-empty string | `len(executive_summary) > 10` |
| 13 | `test_pipeline_imports` | `from nlp.reportagent.pipeline import generate_report` resolves | No ImportError |

Tests 4-12 require both `requires_databricks` and `requires_llm` fixtures.

**Phase 2 Done Gate:**
- `pytest tests/test_report_phase2_agent.py` -- all tests green (skip if no Databricks/LLM)
- At least `harvard_08670` (systemic) produces a valid report
- Report contains zero diagnostic language (output validator enforced)

---

### Phase 3 Tests: API + Formatter

**File:** `tests/test_report_phase3_api_formatter.py`

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_formatter_imports` | `from nlp.reportagent.formatter import render_markdown` resolves | No ImportError |
| 2 | `test_render_markdown_produces_string` | Pass a sample `MedicalResearchReport` to `render_markdown()` | Returns non-empty string |
| 3 | `test_render_markdown_has_all_sections` | Output contains all 11 section headings | All `## N.` headings present |
| 4 | `test_render_markdown_has_disclaimer` | Output contains disclaimer text | Disclaimer string present |
| 5 | `test_render_markdown_doi_links_clickable` | DOIs rendered as `[doi:X](https://doi.org/X)` | Regex matches clickable link format |
| 6 | `test_endpoint_returns_job_id` | `POST /report/{person_id}` returns `job_id` and `status: "queued"` | HTTP 200, both fields present |
| 7 | `test_endpoint_requires_databricks` | `POST /report/{person_id}` without Databricks returns 503 | HTTP 503 |
| 8 | `test_endpoint_job_reaches_terminal` | Poll `GET /jobs/{job_id}` until done or error (timeout 120s) | Status is terminal |
| 9 | `test_endpoint_result_is_valid_report` | When done, `job.result` deserializes to `MedicalResearchReport` | Schema validates |
| 10 | `test_endpoint_sse_emits_events` | SSE stream emits at least 1 "Report Agent" event during generation | Event with `agent="Report Agent"` received |

Tests 6-10 require `requires_backend`, `requires_databricks`, and `requires_llm` fixtures.

**Phase 3 Done Gate:**
- `pytest tests/test_report_phase3_api_formatter.py` -- all tests green
- `POST /report/harvard_08670` returns a job, job completes, result is valid markdown
- Markdown output has all 11 sections with clickable DOI links

---

### Phase 4 Tests: Hardening

**File:** `tests/test_report_phase4_hardening.py`

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_faithfulness_check_runs` | Report pipeline runs faithfulness checker on generated text | `quality_metrics.faithfulness_score > 0.0` |
| 2 | `test_fk_grade_level_computed` | Executive summary has FK grade level computed | `quality_metrics.fk_grade_level` is not None |
| 3 | `test_fk_grade_level_within_range` | FK grade level is between 1 and 16 | `1 <= fk <= 16` |
| 4 | `test_token_tracking_populated` | `quality_metrics.total_tokens > 0` after generation | Tokens tracked |
| 5 | `test_passages_cited_vs_retrieved` | `passages_cited <= passages_retrieved` | Logical constraint holds |
| 6 | `test_report_stored_in_delta` | After generation, report exists in `aura.reports.generated` | Query returns 1 row for patient_id |
| 7 | `test_all_demo_cases_produce_reports` | Run all 4 demo cases, all produce valid reports | 4/4 valid `MedicalResearchReport` objects |
| 8 | `test_gi_case_cluster_is_gi` | GI demo case has `cluster_alignment == Cluster.GI` | Cluster matches |
| 9 | `test_systemic_case_cluster_is_systemic` | Systemic demo case has `cluster_alignment == Cluster.SYSTEMIC` | Cluster matches |

Tests 1-9 require `requires_databricks` and `requires_llm`. Test 6 also requires write access to Delta.

**Phase 4 Done Gate:**
- `pytest tests/test_report_phase4_hardening.py` -- all tests green
- All 4 demo cases produce valid reports with quality metrics populated
- Reports are stored in `aura.reports.generated` Delta table
- No report contains diagnostic language

---

### End-to-End Verification Checklist

After all 4 phases are complete, run the full verification:

- [ ] `pytest tests/test_report_phase*.py -v` -- all tests green
- [ ] `pytest tests/regressions/ -v` -- all regression tests green (if any)
- [ ] Run `generate_report("harvard_08670")` -- systemic case produces valid report
- [ ] Run `generate_report("nhanes_90119")` -- GI case produces valid report
- [ ] Run `generate_report("nhanes_73741")` -- nuanced case produces valid report
- [ ] Run `generate_report("nhanes_79163")` -- healthy case produces valid report with low alignment
- [ ] `POST /report/harvard_08670` via API -- returns job, job completes, valid result
- [ ] SSE stream shows "Report Agent" events during generation
- [ ] No report contains "patient has", "diagnosed with", "suffering from"
- [ ] Every key_findings section has at least 1 DOI citation
- [ ] Markdown output has all 11 sections with clickable DOI links
- [ ] Reports stored in `aura.reports.generated` Delta table
- [ ] Quality metrics populated: retrieval_confidence, faithfulness_score, fk_grade_level, total_tokens
- [ ] Tool call budget not exceeded (max 5 per report)

### Rollback Plan

Each phase is an atomic commit. If a phase introduces a regression:

1. `git revert <phase-commit>` to undo the phase
2. The previous phase's tests still pass (they are independent)
3. Fix the issue on a branch, re-run the failed phase's tests
4. Merge when green

No phase modifies another phase's test files. Tests are additive only.

---

## Security Considerations

1. **SQL injection**: Validate `person_id` format (alphanumeric + underscore only) before any Databricks query. Use parameterized queries where the SDK supports it.
2. **Prompt injection**: Patient data is serialized by our code, not raw user input. The agent prompt is constructed programmatically via `_build_agent_prompt()`.
3. **PHI handling**: Reports contain patient identifiers. Output should not be cached in shared storage without access controls. The FastAPI session store auto-evicts after TTL.
4. **Cost guardrails**: `MAX_TOOL_CALLS=5` caps agent autonomy. `retries=2` limits regeneration attempts. Token usage logged in `QualityMetrics`.
5. **Diagnostic language guardrail**: `@agent.output_validator` rejects any output containing diagnostic phrases. This is a hard gate, not advisory.

---

## Reference Repositories

All cloned to `.research-refs/` for code reference during implementation:

| Repository | Stars | Primary Value |
|-----------|-------|---------------|
| [pydantic-ai](https://github.com/pydantic/pydantic-ai) | ~15k | Agent framework (our chosen framework) |
| [google/pubmed-rag](https://github.com/google/pubmed-rag) | Google | Production report template, multi-factor scoring |
| [Medical-Graph-RAG](https://github.com/ImprintLab/Medical-Graph-RAG) | ACL 2025 | Dual-mode retrieval, evidence grounding |
| [Multi-Agent-Medical-Assistant](https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant) | Growing | Confidence routing, guardrails, hybrid retrieval |
| [MedRAG](https://github.com/Teddy-XiongGZ/MedRAG) | ~700 | RRF fusion, MedCPT dual-encoder, multi-corpus |
| [RAG_Techniques](https://github.com/NirDiamant/RAG_Techniques) | ~24.5k | CRAG, Self-RAG, fusion retrieval patterns |

---

## Resolved Decisions

1. **Model choice**: Claude via Azure (paulbobev account). Fallback: GPT model via sw account. Update `AURA_REPORT_MODEL` accordingly.
2. **Report versioning**: Yes. Store generated reports in `aura.reports.generated` Delta table for audit trail.
3. **Frontend integration**: No frontend for now. Output is markdown, PDF generation deferred to a later sprint.
4. **Agent autonomy**: Max 3 follow-up research rounds (matches i-MedRAG's validated pattern).
5. **BM25 index**: Deferred -- not enough time this sprint. Revisit when time allows.
6. **Journal impact data (Scimago SJR)**: Deferred -- too much GPU use.
7. **Graph RAG layer (Neo4j)**: Deferred -- too much GPU use + Neo4j dependency.

## Remaining Open Questions

1. **Multi-corpus (Phase 5)**: Should we add StatPearls as a second corpus for clinical guidelines alongside PubMed?
2. **Azure endpoint details**: Confirm Claude deployment name and endpoint URL on paulbobev Azure account.
