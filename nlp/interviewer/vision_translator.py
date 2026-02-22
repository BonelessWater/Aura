"""
Vision-to-Text Translator — The Interviewer, Step 5 (Phase 6).

Calls a local LLaVA-Med instance (via vLLM) to generate clinical
keywords from patient-uploaded photos or video frames.

Requires: vLLM running on Ubuntu with LLaVA-Med loaded.
Set VLLM_BASE_URL env var (default: http://localhost:8000)
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from nlp.interviewer.cluster_mapper import tag_cluster_signal
from nlp.shared.schemas import Cluster

logger = logging.getLogger(__name__)

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL    = os.environ.get("VLLM_VISION_MODEL", "llava-med")

VISION_SYSTEM_PROMPT = """You are a clinical documentation assistant.
Describe the following image using precise medical terminology only.
Focus on: skin findings (color, texture, distribution pattern),
joint changes (swelling, erythema, deformity), visible edema,
rash morphology, nail changes, mucosal findings.
Output ONLY a comma-separated list of clinical observation keywords.
Do not speculate on any diagnosis. Do not use lay language.
Do not include any introductory text."""


def _call_azure_vision(image_b64: str) -> Optional[str]:
    """Call Azure OpenAI GPT-4o vision instead of vLLM LLaVA-Med."""
    from nlp.shared.azure_client import get_azure_nlp_client

    client = get_azure_nlp_client()
    return client.chat_with_image(
        deployment="4o",
        system_prompt=VISION_SYSTEM_PROMPT,
        image_b64=image_b64,
        user_text="Describe clinical findings only.",
        temperature=0.1,
        max_tokens=256,
    )


def image_to_clinical_keywords(
    image_path: str | Path,
    max_keywords: int = 20,
) -> list[str]:
    """
    Send an image to a vision model and return a list of clinical keywords.

    Uses Azure OpenAI GPT-4o when AURA_NLP_BACKEND=azure, otherwise vLLM LLaVA-Med.

    Args:
        image_path: Path to a JPEG/PNG image file
        max_keywords: Maximum number of keywords to return

    Returns:
        List of clinical observation strings, each tagged with cluster signal
    """
    from nlp.shared.azure_client import get_nlp_backend

    image_b64 = _encode_image(image_path)

    if get_nlp_backend("vision") == "azure":
        raw_output = _call_azure_vision(image_b64)
    else:
        raw_output = _call_vllm(image_b64)

    if not raw_output:
        return []

    keywords = _parse_keywords(raw_output)
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


def _call_vllm(image_b64: str) -> Optional[str]:
    """POST to vLLM OpenAI-compatible API."""
    try:
        import requests
        response = requests.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json={
                "model": VLLM_MODEL,
                "messages": [
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
                "max_tokens": 256,
                "temperature": 0.1,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"vLLM vision call failed: {e}")
        return None


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
