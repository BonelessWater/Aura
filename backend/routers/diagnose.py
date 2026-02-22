"""
Diagnose Router — proxies clinical text to the remote GPU inference server
running OpenBioLLM-8B with a fine-tuned LoRA adapter.

The inference server URL is configured via INFERENCE_SERVER_URL env var.
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

INFERENCE_SERVER_URL = os.environ.get(
    "INFERENCE_SERVER_URL", "http://localhost:8099"
)
INFERENCE_TIMEOUT = float(os.environ.get("INFERENCE_TIMEOUT", "30"))


class DiagnoseRequest(BaseModel):
    text: str


class DiagnoseResponse(BaseModel):
    diagnosis: str
    inference_time: float


class BatchDiagnoseRequest(BaseModel):
    texts: list[str]


class BatchDiagnoseResponse(BaseModel):
    results: list[DiagnoseResponse]
    total_time: float


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest):
    """Send clinical text to the remote inference server for diagnosis."""
    try:
        async with httpx.AsyncClient(timeout=INFERENCE_TIMEOUT) as client:
            resp = await client.post(
                f"{INFERENCE_SERVER_URL}/diagnose",
                json={"text": req.text},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Inference server unreachable at {INFERENCE_SERVER_URL}",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Inference server error: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text[:500],
        )
    except Exception as e:
        logger.error("Inference request failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/diagnose/batch", response_model=BatchDiagnoseResponse)
async def diagnose_batch(req: BatchDiagnoseRequest):
    """Send multiple clinical texts for batch diagnosis."""
    if not req.texts:
        raise HTTPException(status_code=400, detail="Empty texts list")
    try:
        async with httpx.AsyncClient(timeout=INFERENCE_TIMEOUT * len(req.texts)) as client:
            resp = await client.post(
                f"{INFERENCE_SERVER_URL}/diagnose/batch",
                json={"texts": req.texts},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Inference server unreachable at {INFERENCE_SERVER_URL}",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Inference server batch error: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text[:500],
        )
    except Exception as e:
        logger.error("Batch inference request failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/diagnose/health")
async def inference_health():
    """Check if the remote inference server is up and model is loaded."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{INFERENCE_SERVER_URL}/health")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}
