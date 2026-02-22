"""
Layman's Compass — The Translator, Step 5.3.

Generates a patient-facing plain-English summary.
Reading level target: Flesch-Kincaid Grade 8 or below.

Verified with textstat. Auto-regenerates if grade > 8.
Always closes with the standard disclaimer.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL    = os.environ.get("VLLM_TEXT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
MAX_FK_GRADE  = 8.0
DISCLAIMER    = (
    "\n\n---\n**Important:** Only a doctor can diagnose you — "
    "this report is a tool to help your doctor act faster."
)

LAYMAN_SYSTEM_PROMPT = """You are explaining a patient's lab patterns in plain English.

CRITICAL RULES:
1. You are NOT diagnosing the patient. Do not name any disease as their diagnosis.
2. Use simple everyday words. Avoid medical jargon. Target a Grade 8 reading level.
3. Use analogies (e.g., "Think of this marker like a fire alarm in your body").
4. Be warm and empathetic. Reassure the patient that these findings help their doctor.
5. Keep it under 300 words.
6. End with: "Only a doctor can diagnose you — this report is a tool to help your doctor act faster."
"""


def generate_layman_compass(
    router_output:    Optional[object] = None,
    interview_result: Optional[object] = None,
    lab_report:       Optional[object] = None,
    max_attempts:     int = 3,
) -> tuple[str, float]:
    """
    Generate patient-facing Compass text.

    Returns (text, fk_grade_level).
    Retries with stricter prompt if grade > 8.
    Falls back to template if vLLM unavailable.
    """
    from nlp.shared.azure_client import get_nlp_backend

    for attempt in range(max_attempts):
        if get_nlp_backend("layman") == "azure":
            text = _call_azure_layman(
                router_output, interview_result, lab_report,
                simplify_more=(attempt > 0)
            )
        else:
            text = _call_vllm_layman(
                router_output, interview_result, lab_report,
                simplify_more=(attempt > 0)
            )
        if not text:
            break

        grade = _check_reading_level(text)
        if grade <= MAX_FK_GRADE:
            return text + DISCLAIMER, grade

        logger.info(f"FK grade {grade:.1f} > {MAX_FK_GRADE}. Retrying with simpler language...")

    # Template fallback
    text  = _template_compass(router_output, interview_result, lab_report)
    grade = _check_reading_level(text)
    return text + DISCLAIMER, grade


def _call_azure_layman(router_output, interview_result, lab_report, simplify_more=False) -> Optional[str]:
    """Generate layman text using Azure OpenAI instead of vLLM Mistral."""
    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    prompt = _build_layman_prompt(router_output, interview_result, lab_report)
    if simplify_more:
        prompt = "Use only very simple words. Imagine explaining to a 12-year-old.\n\n" + prompt
    return client.chat(
        deployment="nano",
        messages=[
            {"role": "system", "content": LAYMAN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )


def _call_vllm_layman(router_output, interview_result, lab_report, simplify_more=False) -> Optional[str]:
    try:
        import requests
        prompt = _build_layman_prompt(router_output, interview_result, lab_report)
        if simplify_more:
            prompt = "Use only very simple words. Imagine explaining to a 12-year-old.\n\n" + prompt

        response = requests.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json={
                "model":    VLLM_MODEL,
                "messages": [
                    {"role": "system", "content": LAYMAN_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.3,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"vLLM Layman generation failed: {e}")
        return None


def _build_layman_prompt(router_output, interview_result, lab_report) -> str:
    parts = ["Explain the following findings in simple, kind language:\n"]

    if interview_result and interview_result.symptoms:
        top_syms = [s.entity for s in interview_result.symptoms[:4]]
        parts.append(f"Main concerns reported: {', '.join(top_syms)}")

    if lab_report:
        fp = lab_report.bio_fingerprint
        if fp.sustained_abnormalities:
            parts.append(
                f"Lab pattern: {', '.join(fp.sustained_abnormalities)} "
                f"have been consistently outside the normal range."
            )
        if fp.NLR:
            nlr = fp.NLR[-1].value
            if nlr > 3:
                parts.append(
                    f"An inflammation marker (NLR={nlr:.1f}) is elevated above normal (normal <3.0)."
                )

    if router_output:
        parts.append(
            f"These patterns suggest the body may be under {router_output.cluster.value} stress "
            f"({router_output.cluster_alignment_score:.0%} pattern match). "
            f"A {router_output.routing_recommendation} could help investigate further."
        )

    return "\n".join(parts)


def _template_compass(router_output, interview_result, lab_report) -> str:
    """Simple template for when vLLM is not available."""
    parts = ["## Your Health Summary\n"]

    if interview_result and interview_result.symptoms:
        top_syms = [s.entity for s in interview_result.symptoms[:4]]
        parts.append(
            f"You shared some health concerns, including: **{', '.join(top_syms)}**. "
            f"These have been noted carefully."
        )

    if lab_report and lab_report.bio_fingerprint.sustained_abnormalities:
        ab = lab_report.bio_fingerprint.sustained_abnormalities
        parts.append(
            f"\nYour blood tests show that **{', '.join(ab)}** "
            f"{'has' if len(ab) == 1 else 'have'} been outside the normal range "
            f"on multiple visits. Think of these like a check engine light — "
            f"it doesn't tell us exactly what's wrong, but it tells a doctor where to look."
        )

    if router_output:
        routing = router_output.routing_recommendation
        score   = router_output.cluster_alignment_score
        parts.append(
            f"\nYour overall pattern ({score:.0%} match) suggests "
            f"seeing a **{routing}** for a closer look."
        )

    return "\n".join(parts)


def _check_reading_level(text: str) -> float:
    """Return Flesch-Kincaid grade level. Returns 0 if textstat unavailable."""
    try:
        import textstat
        return textstat.flesch_kincaid_grade(text)
    except ImportError:
        return 0.0
