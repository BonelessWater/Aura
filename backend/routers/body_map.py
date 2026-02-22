"""
Body Map endpoint -- returns body-region severity data for the 3D model.

Uses patient session data (symptoms + lab markers) to produce a list of
affected body regions with severity levels (mild / moderate / severe).

GET /body-map/{patient_id}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Canonical body regions (must match frontend BodyModel + notebooks VALID_BODY_REGIONS) ──

VALID_BODY_REGIONS = {
    "head", "neck", "chest", "upper_back", "lower_back", "abdomen",
    "left_shoulder", "right_shoulder", "left_upper_arm", "right_upper_arm",
    "left_forearm", "right_forearm", "left_hand", "right_hand",
    "left_hip", "right_hip", "left_upper_leg", "right_upper_leg",
    "left_knee", "right_knee", "left_lower_leg", "right_lower_leg",
    "left_foot", "right_foot", "whole_body",
}

# Map bone anchors for each region (used by the frontend for click targets)
REGION_BONE_ANCHOR = {
    "head": "Head", "neck": "Neck",
    "chest": "Spine2", "upper_back": "Spine2", "abdomen": "Spine",
    "lower_back": "Hips",
    "left_shoulder": "LeftShoulder", "right_shoulder": "RightShoulder",
    "left_upper_arm": "LeftArm", "right_upper_arm": "RightArm",
    "left_forearm": "LeftForeArm", "right_forearm": "RightForeArm",
    "left_hand": "LeftHand", "right_hand": "RightHand",
    "left_hip": "LeftUpLeg", "right_hip": "RightUpLeg",
    "left_upper_leg": "LeftUpLeg", "right_upper_leg": "RightUpLeg",
    "left_knee": "LeftLeg", "right_knee": "RightLeg",
    "left_lower_leg": "LeftLeg", "right_lower_leg": "RightLeg",
    "left_foot": "LeftFoot", "right_foot": "RightFoot",
    "whole_body": "Spine1",
}


# ── Response schema ─────────────────────────────────────────────────────────

class BodyRegionResult(BaseModel):
    body_region: str
    severity: str  # mild | moderate | severe
    label: str
    status: str
    explanation: str
    bone_name: str
    offset: list[float] = Field(default_factory=lambda: [0, 0, 0])
    radius: float = 0.04


class BodyMapResponse(BaseModel):
    patient_id: str
    regions: list[BodyRegionResult]


# ── LLM prompt for body-region extraction from session data ──────────────────

BODY_MAP_SYSTEM_PROMPT = (
    "You are a medical body-map analyzer. Given a patient's symptoms and lab markers, "
    "identify which body regions are affected and assign a severity level.\n\n"
    "For each affected region, output:\n"
    "- body_region: MUST be one of these exact values:\n"
    "  head, neck, chest, upper_back, lower_back, abdomen,\n"
    "  left_shoulder, right_shoulder, left_upper_arm, right_upper_arm,\n"
    "  left_forearm, right_forearm, left_hand, right_hand,\n"
    "  left_hip, right_hip, left_upper_leg, right_upper_leg,\n"
    "  left_knee, right_knee, left_lower_leg, right_lower_leg,\n"
    "  left_foot, right_foot, whole_body\n"
    "- severity: 'mild', 'moderate', or 'severe'\n"
    "- label: short patient-friendly label (e.g. 'Right Knee -- Joint Pain')\n"
    "- status: brief status indicator (e.g. 'Reported symptom', '3 markers flagged', '95% match')\n"
    "- explanation: 2-3 sentence patient-friendly explanation of why this region is flagged\n\n"
    "Reply with ONLY a JSON array. No other text.\n"
    "If no body regions are affected, return: []\n"
)


def _build_patient_context(session) -> str:
    """Build a text summary of the patient's session data for the LLM."""
    parts = []

    if session.interview_result:
        ir = session.interview_result
        parts.append("REPORTED SYMPTOMS:")
        for s in ir.symptoms:
            line = f"  - {s.entity}"
            if s.location:
                line += f" (location: {s.location})"
            if s.severity:
                line += f" [severity: {s.severity}]"
            if s.duration_months:
                line += f" [{s.duration_months} months]"
            parts.append(line)
        if ir.visual_keywords:
            parts.append(f"  Visual keywords: {', '.join(ir.visual_keywords)}")

    if session.lab_report:
        lr = session.lab_report
        flagged = []
        for timeline in lr.markers:
            if timeline.values:
                latest = timeline.values[-1]
                if latest.flag and latest.flag.value != "NORMAL":
                    flagged.append(
                        f"  - {timeline.display_name}: {latest.value} {latest.unit} "
                        f"[{latest.flag.value}]"
                    )
        if flagged:
            parts.append("\nFLAGGED LAB MARKERS:")
            parts.extend(flagged)

        fp = lr.bio_fingerprint
        if fp.sustained_abnormalities:
            parts.append(f"\nSustained abnormalities: {', '.join(fp.sustained_abnormalities)}")

    if session.router_output:
        ro = session.router_output
        parts.append(f"\nROUTER ANALYSIS:")
        parts.append(f"  Cluster: {ro.cluster.value} ({ro.cluster_alignment_score:.0%} alignment)")
        for dc in ro.disease_candidates[:3]:
            parts.append(
                f"  - {dc.disease}: {dc.disease_alignment_score:.0%} "
                f"({dc.criteria_count} criteria met)"
            )

    return "\n".join(parts) if parts else "No patient data available."


async def _extract_body_regions_llm(patient_context: str) -> list[dict]:
    """Call LLM to extract body regions from patient context."""
    try:
        from openai import AzureOpenAI

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT41_MINI", "gpt-4.1-mini")
        api_version = os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview")

        if not endpoint or not api_key:
            logger.warning("Azure OpenAI credentials not set, falling back to heuristic")
            return []

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=deployment,
            messages=[
                {"role": "system", "content": BODY_MAP_SYSTEM_PROMPT},
                {"role": "user", "content": f"Patient data:\n{patient_context}"},
            ],
            temperature=0,
            max_tokens=800,
        )

        reply = response.choices[0].message.content.strip()

        # Strip markdown fences
        if reply.startswith("```"):
            reply = reply.split("\n", 1)[1] if "\n" in reply else reply[3:]
            if reply.endswith("```"):
                reply = reply[:-3].strip()

        data = json.loads(reply)
        if not isinstance(data, list):
            logger.warning("LLM returned non-array for body map: %s", reply[:200])
            return []

        # Validate regions
        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue
            region = item.get("body_region", "")
            if region not in VALID_BODY_REGIONS:
                logger.warning("LLM returned invalid body_region: %r", region)
                continue
            severity = item.get("severity", "mild")
            if severity not in ("mild", "moderate", "severe"):
                severity = "moderate"
            validated.append({
                "body_region": region,
                "severity": severity,
                "label": item.get("label", region.replace("_", " ").title()),
                "status": item.get("status", "Detected"),
                "explanation": item.get("explanation", ""),
            })
        return validated

    except Exception as exc:
        logger.error("LLM body-map extraction failed: %s", exc, exc_info=True)
        return []


def _heuristic_body_regions(session) -> list[dict]:
    """Fallback: derive body regions from symptom entities without LLM."""
    from notebooks.extract_body_pain import normalize_body_region

    regions: dict[str, dict] = {}

    if session.interview_result:
        for s in session.interview_result.symptoms:
            # Try to map entity or location to a body region
            region_id = None
            if s.location:
                region_id = normalize_body_region(s.location)
            if not region_id:
                region_id = normalize_body_region(s.entity)
            if not region_id:
                continue

            # Map severity
            sev = "moderate"
            if s.severity:
                sl = s.severity.lower()
                if sl in ("mild", "slight", "minor"):
                    sev = "mild"
                elif sl in ("severe", "intense", "acute", "debilitating"):
                    sev = "severe"

            if region_id not in regions or _sev_rank(sev) > _sev_rank(regions[region_id]["severity"]):
                regions[region_id] = {
                    "body_region": region_id,
                    "severity": sev,
                    "label": f"{region_id.replace('_', ' ').title()} -- {s.entity}",
                    "status": "Reported symptom",
                    "explanation": f"You reported {s.entity}.",
                }

    return list(regions.values())


def _sev_rank(sev: str) -> int:
    return {"mild": 1, "moderate": 2, "severe": 3}.get(sev, 0)


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/body-map/{patient_id}")
async def get_body_map(patient_id: str):
    """
    Return body-region severity data for the 3D body model.

    Reads the patient session (symptoms, labs, router output) and uses
    an LLM to determine which body regions to highlight and at what severity.
    Falls back to a heuristic mapper if the LLM is unavailable.
    """
    session = get_session(patient_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"No session found for patient_id '{patient_id}'. Run the pipeline first.",
        )

    patient_context = _build_patient_context(session)

    # Try LLM extraction first, fall back to heuristic
    raw_regions = await _extract_body_regions_llm(patient_context)
    if not raw_regions:
        raw_regions = _heuristic_body_regions(session)

    # Enrich with bone anchors and default geometry
    results = []
    for r in raw_regions:
        region_id = r["body_region"]
        bone_name = REGION_BONE_ANCHOR.get(region_id, "Spine1")

        # Default offsets and radii per region type
        offset = [0.0, 0.0, 0.0]
        radius = 0.04
        if region_id == "head":
            offset = [0, 0.06, 0.08]
            radius = 0.06
        elif region_id == "chest":
            offset = [0, 0.05, 0.08]
            radius = 0.07
        elif region_id in ("left_hand", "right_hand"):
            radius = 0.03
        elif region_id in ("left_knee", "right_knee"):
            offset = [0, 0.02, 0.02]
        elif region_id == "whole_body":
            radius = 0.09

        results.append(BodyRegionResult(
            body_region=region_id,
            severity=r["severity"],
            label=r["label"],
            status=r["status"],
            explanation=r["explanation"],
            bone_name=bone_name,
            offset=offset,
            radius=radius,
        ))

    return BodyMapResponse(patient_id=patient_id, regions=results)
