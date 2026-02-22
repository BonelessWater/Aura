"""
SOAP Note Generator — The Translator, Step 5.2.

Generates a clinical SOAP note from the patient bundle.
Uses Mistral-7B-Instruct via local vLLM server.

Zero diagnostic language. Every claim requires an inline DOI citation.
Assessments are framed as "X% Cluster Alignment" — never diagnoses.

Set VLLM_BASE_URL env var (default: http://localhost:8000).
Falls back to a template-based note if vLLM is unavailable.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from nlp.shared.schemas import InterviewResult, LabReport, ResearchResult, RouterOutput

logger = logging.getLogger(__name__)

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL    = os.environ.get("VLLM_TEXT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

SOAP_SYSTEM_PROMPT = """You are generating a clinical SOAP note for specialist referral.

CRITICAL RULES:
1. This is NOT a diagnosis. It is a High Probability Flag for specialist referral.
2. Use clinical tone. Every factual claim requires an inline DOI citation.
3. Frame ALL assessments as "X% Cluster Alignment" — never "patient has [disease]".
4. Do not speculate beyond the provided evidence and data.
5. Use format: [claim] [Author et al., Year](doi:XXXXX)

Required sections: Subjective, Objective, Assessment, Plan."""


def generate_soap(
    lab_report:       Optional[LabReport]       = None,
    interview_result: Optional[InterviewResult] = None,
    research_result:  Optional[ResearchResult]  = None,
    router_output:    Optional[RouterOutput]    = None,
    max_attempts:     int = 2,
) -> str:
    """
    Generate a clinical SOAP note.

    Tries vLLM first; falls back to structured template.
    """
    from nlp.translator.faithfulness_checker import check_faithfulness

    passages = research_result.passages if research_result else []

    # Build pipeline context so the faithfulness checker knows about
    # router scores, interview symptoms, and lab data referenced in the note
    pipeline_context = _build_pipeline_context(lab_report, interview_result, router_output)

    from nlp.shared.azure_client import get_nlp_backend

    for attempt in range(max_attempts):
        if get_nlp_backend("soap") == "azure":
            raw = _call_azure_soap(lab_report, interview_result, router_output, passages)
        else:
            raw = _call_vllm_soap(lab_report, interview_result, router_output, passages)
        if not raw:
            break  # LLM unavailable — use template

        # Faithfulness check
        passed, flagged, mean_score = check_faithfulness(
            raw, passages, pipeline_context=pipeline_context
        )
        if passed:
            return raw
        logger.warning(
            f"SOAP faithfulness check failed (attempt {attempt+1}): "
            f"{len(flagged)} flagged sentences. Retrying..."
        )

    # Fallback: structured template
    return _template_soap(lab_report, interview_result, router_output, passages)


def _build_pipeline_context(
    lab_report:       Optional[LabReport],
    interview_result: Optional[InterviewResult],
    router_output:    Optional[RouterOutput],
) -> str:
    """Build a plain-text summary of pipeline data for the faithfulness checker."""
    parts = []

    if interview_result and interview_result.symptoms:
        syms = [f"{s.entity} ({s.severity or 'unspecified'}, "
                f"{s.duration_months or '?'} months)" for s in interview_result.symptoms[:6]]
        parts.append(f"Reported symptoms: {'; '.join(syms)}.")

    if lab_report:
        fp = lab_report.bio_fingerprint
        if fp.sustained_abnormalities:
            parts.append(f"Sustained abnormalities: {', '.join(fp.sustained_abnormalities)}.")
        if fp.morphological_shifts:
            parts.append(f"Morphological shifts: {', '.join(fp.morphological_shifts)}.")
        if fp.NLR:
            parts.append(f"NLR: {fp.NLR[-1].value:.2f} ({fp.NLR[-1].flag or 'normal'}).")
        if fp.C3_C4:
            parts.append(f"C3/C4: {fp.C3_C4[-1].value:.2f} ({fp.C3_C4[-1].flag or 'normal'}).")

    if router_output:
        parts.append(
            f"Cluster alignment: {router_output.cluster.value} "
            f"at {router_output.cluster_alignment_score:.0%}."
        )
        for dc in router_output.disease_candidates[:3]:
            parts.append(
                f"Disease flag: {dc.disease} at {dc.disease_alignment_score:.0%} "
                f"alignment ({dc.criteria_count} criteria met)."
            )
        parts.append(f"Routing recommendation: {router_output.routing_recommendation}.")

    return " ".join(parts)


def _call_azure_soap(lab_report, interview_result, router_output, passages) -> Optional[str]:
    """Generate SOAP note using Azure OpenAI instead of vLLM Mistral."""
    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    user_content = _build_soap_prompt(lab_report, interview_result, router_output, passages)
    return client.chat(
        deployment="mini",
        messages=[
            {"role": "system", "content": SOAP_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=1200,
    )


def _call_vllm_soap(
    lab_report:       Optional[LabReport],
    interview_result: Optional[InterviewResult],
    router_output:    Optional[RouterOutput],
    passages:         list,
) -> Optional[str]:
    """Call vLLM to generate the SOAP note."""
    try:
        import requests
        user_content = _build_soap_prompt(lab_report, interview_result, router_output, passages)
        response = requests.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json={
                "model":    VLLM_MODEL,
                "messages": [
                    {"role": "system", "content": SOAP_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                "max_tokens": 1200,
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"vLLM SOAP generation failed: {e}")
        return None


def _build_soap_prompt(lab_report, interview_result, router_output, passages) -> str:
    parts = ["Generate a clinical SOAP note based on the following patient data:\n"]

    if interview_result and interview_result.symptoms:
        syms = [f"{s.entity} ({s.severity or 'unspecified severity'}, "
                f"{s.duration_months or '?'} months)" for s in interview_result.symptoms[:6]]
        parts.append(f"SYMPTOMS: {'; '.join(syms)}")

    if lab_report:
        fp = lab_report.bio_fingerprint
        parts.append(f"SUSTAINED ABNORMALITIES: {', '.join(fp.sustained_abnormalities) or 'none'}")
        parts.append(f"MORPHOLOGICAL SHIFTS: {', '.join(fp.morphological_shifts) or 'none'}")
        if fp.NLR:
            parts.append(f"NLR: {fp.NLR[-1].value:.2f} ({fp.NLR[-1].flag or 'normal'})")

    if router_output:
        parts.append(
            f"CLUSTER ALIGNMENT: {router_output.cluster.value} "
            f"{router_output.cluster_alignment_score:.0%}"
        )
        if router_output.disease_candidates:
            top = router_output.disease_candidates[0]
            parts.append(
                f"TOP DISEASE FLAG: {top.disease} at {top.disease_alignment_score:.0%}"
            )

    if passages:
        parts.append("\nEVIDENCE PASSAGES (cite these using their DOIs):")
        for p in passages[:5]:
            doi_str = f"(doi:{p.doi})" if p.doi else "(no DOI)"
            parts.append(f"- {p.text[:200]}... {doi_str}")

    return "\n".join(parts)


def _template_soap(lab_report, interview_result, router_output, passages) -> str:
    """Structured template fallback when vLLM is unavailable."""
    lines = ["## SOAP NOTE\n"]

    # Subjective
    lines.append("### S — Subjective")
    if interview_result and interview_result.symptoms:
        top_syms = [s.entity for s in interview_result.symptoms[:5]]
        lines.append(f"Patient reports: {', '.join(top_syms)}.")
    else:
        lines.append("Patient narrative not available.")

    # Objective
    lines.append("\n### O — Objective")
    if lab_report:
        fp = lab_report.bio_fingerprint
        if fp.NLR:
            lines.append(f"- NLR: {fp.NLR[-1].value:.2f} (ref: <3.0)")
        if fp.sustained_abnormalities:
            lines.append(f"- Sustained abnormalities: {', '.join(fp.sustained_abnormalities)}")
        if fp.morphological_shifts:
            lines.append(f"- Morphological shifts: {', '.join(fp.morphological_shifts)}")
    else:
        lines.append("Lab data not available.")

    # Assessment
    lines.append("\n### A — Assessment")
    if router_output:
        lines.append(
            f"Data indicates **{router_output.cluster_alignment_score:.0%} "
            f"{router_output.cluster.value} Cluster Alignment**."
        )
        for dc in router_output.disease_candidates[:2]:
            lines.append(
                f"- {dc.disease}: {dc.disease_alignment_score:.0%} alignment "
                f"({dc.criteria_count} criteria met)"
            )
    else:
        lines.append("Cluster alignment scoring not yet complete.")

    # Plan
    lines.append("\n### P — Plan")
    routing = router_output.routing_recommendation if router_output else "Internal Medicine"
    lines.append(f"Referral recommended to: **{routing}**.")
    if passages:
        lines.append("Supporting evidence:")
        for p in passages[:3]:
            if p.doi:
                lines.append(f"  - doi:{p.doi}")

    lines.append("\n---")
    lines.append("*This report is a data-backed High Probability Flag for specialist referral. "
                 "It is not a diagnosis. Only a qualified physician can diagnose.*")
    return "\n".join(lines)
