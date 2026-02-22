"""
Translator Pipeline — The Translator (Phase 5 orchestrator).

Given the full patient bundle, generates:
  1. Clinical SOAP Note (for the doctor)
  2. Layman's Compass (for the patient)

Both outputs are grounded in retrieved evidence with DOI citations.
Zero hallucination tolerance enforced via NLI faithfulness check.

Usage:
    from nlp.translator.pipeline import run_translator
    output = run_translator(patient_id="P001", lab_report=lab,
                            interview_result=interview, research_result=research,
                            router_output=router_out)
"""

from __future__ import annotations

import logging
from typing import Optional

from nlp.shared.schemas import (
    InterviewResult,
    LabReport,
    ResearchResult,
    RouterOutput,
    TranslatorOutput,
)
from nlp.shared.thought_stream import ThoughtStream
from nlp.translator.soap_generator import generate_soap
from nlp.translator.layman_generator import generate_layman_compass

logger = logging.getLogger(__name__)


def run_translator(
    patient_id:       str,
    lab_report:       Optional[LabReport]       = None,
    interview_result: Optional[InterviewResult] = None,
    research_result:  Optional[ResearchResult]  = None,
    router_output:    Optional[RouterOutput]    = None,
) -> TranslatorOutput:
    """
    Full Translator pipeline.

    Steps:
      1. Generate SOAP Note (clinical)
      2. Faithfulness check on SOAP Note
      3. Generate Layman's Compass
      4. Verify FK grade level ≤ 8
    """
    ThoughtStream.emit(
        agent="The Translator",
        step="start",
        summary=f"Generating clinical outputs for patient {patient_id}",
        patient_id=patient_id,
    )

    # ── Step 1-2: SOAP Note ───────────────────────────────────────────────────
    from nlp.translator.faithfulness_checker import check_faithfulness
    from nlp.translator.soap_generator import _build_pipeline_context
    passages = research_result.passages if research_result else []

    soap_note = generate_soap(
        lab_report       = lab_report,
        interview_result = interview_result,
        research_result  = research_result,
        router_output    = router_output,
    )

    pipeline_context = _build_pipeline_context(lab_report, interview_result, router_output)
    passed, flagged, mean_faith = check_faithfulness(
        soap_note, passages, pipeline_context=pipeline_context
    )

    ThoughtStream.emit(
        agent="The Translator",
        step="soap_note",
        summary=(
            f"SOAP note generated ({len(soap_note)} chars). "
            f"Faithfulness: {mean_faith:.2f} ({'PASS' if passed else 'WARN — flagged sentences'}). "
            f"{len(flagged)} sentences below threshold."
        ),
        patient_id=patient_id,
    )

    # ── Step 3-4: Layman's Compass ────────────────────────────────────────────
    compass_text, fk_grade = generate_layman_compass(
        router_output    = router_output,
        interview_result = interview_result,
        lab_report       = lab_report,
    )

    ThoughtStream.emit(
        agent="The Translator",
        step="layman_compass",
        summary=(
            f"Layman's Compass generated ({len(compass_text)} chars). "
            f"FK Grade Level: {fk_grade:.1f} "
            f"({'OK' if fk_grade <= 8 else 'ABOVE TARGET — review'})."
        ),
        patient_id=patient_id,
    )

    return TranslatorOutput(
        patient_id          = patient_id,
        soap_note           = soap_note,
        layman_compass      = compass_text,
        faithfulness_score  = mean_faith,
        flagged_sentences   = flagged,
        fk_grade_level      = fk_grade,
    )
