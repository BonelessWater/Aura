"""
Vision-to-Text Translator — The Interviewer, Step 5 (Phase 6).

Calls Azure OpenAI multimodal chat to generate clinical
keywords from patient-uploaded photos or video frames.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

from nlp.interviewer.cluster_mapper import tag_cluster_signal
from nlp.shared.schemas import Cluster
from nlp.shared.azure_openai_client import chat_completion, read_env

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """You are a clinical documentation assistant.
Describe the following image using precise medical terminology only.
Focus on: skin findings (color, texture, distribution pattern),
joint changes (swelling, erythema, deformity), visible edema,
rash morphology, nail changes, mucosal findings.
Output ONLY a comma-separated list of clinical observation keywords.
Do not speculate on any diagnosis. Do not use lay language.
Do not include any introductory text."""


def image_to_clinical_keywords(
    image_path: str | Path,
    max_keywords: int = 20,
) -> list[str]:
    """
    Send an image to LLaVA-Med and return a list of clinical keywords.

    Args:
        image_path: Path to a JPEG/PNG image file
        max_keywords: Maximum number of keywords to return

    Returns:
        List of clinical observation strings, each tagged with cluster signal
    """
    image_b64 = _encode_image(image_path)
    raw_output = _call_azure_vision(image_b64)
    if not raw_output:
        return []

    keywords = _parse_keywords(raw_output)
    # Strip any diagnostic language that slipped through
    keywords = _strip_diagnostic_language(keywords)
    return keywords[:max_keywords]


def video_to_clinical_keywords(
    video_path: str | Path,
    fps_sample: float = 0.5,   # 1 frame per 2 seconds
    max_keywords: int = 30,
) -> list[str]:
    """
    Sample frames from a video and aggregate clinical keywords across frames.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError("opencv-python required: pip install opencv-python")

    video_path = Path(video_path)
    cap        = cv2.VideoCapture(str(video_path))
    fps        = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = int(fps / fps_sample)

    all_keywords: set[str] = set()
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_num % frame_interval == 0:
            # Convert frame to JPEG bytes
            import cv2, tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(tmp.name, frame)
            try:
                kws = image_to_clinical_keywords(tmp.name)
                all_keywords.update(kws)
            finally:
                Path(tmp.name).unlink(missing_ok=True)
        frame_num += 1

    cap.release()
    return list(all_keywords)[:max_keywords]


def tag_keywords_with_cluster(keywords: list[str]) -> list[dict]:
    """
    Tag each keyword with its likely cluster signal.

    Returns list of {keyword, cluster, confidence}
    """
    tagged = []
    for kw in keywords:
        cluster, conf = tag_cluster_signal(kw)
        tagged.append({
            "keyword":    kw,
            "cluster":    cluster.value if cluster else None,
            "confidence": conf,
        })
    return tagged


def _encode_image(path: str | Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_azure_vision(image_b64: str) -> Optional[str]:
    """POST to Azure OpenAI Chat Completions (vision-capable deployment)."""
    return chat_completion(
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                    {"type": "text", "text": "Describe clinical findings only."},
                ],
            },
        ],
        deployment=(
            read_env("AZURE_OPENAI_DEPLOYMENT_VISION")
            or read_env("AZURE_OPENAI_DEPLOYMENT_GPT4O")
        ),
        max_tokens=256,
        temperature=0.1,
        timeout=30,
    )


def _parse_keywords(raw: str) -> list[str]:
    # Split on commas, newlines, semicolons
    import re
    parts = re.split(r"[,;\n]+", raw)
    return [p.strip().lower() for p in parts if p.strip()]


_DIAGNOSTIC_TERMS = {
    "lupus", "sle", "rheumatoid arthritis", "crohn", "colitis",
    "hashimoto", "graves", "psoriatic", "ankylosing",
    "diagnosis", "diagnose", "likely", "consistent with", "suggestive of",
    "patient has", "indicating",
}


def _strip_diagnostic_language(keywords: list[str]) -> list[str]:
    """Remove any keywords that contain diagnostic language."""
    clean = []
    for kw in keywords:
        kw_lower = kw.lower()
        if not any(term in kw_lower for term in _DIAGNOSTIC_TERMS):
            clean.append(kw)
    return clean
