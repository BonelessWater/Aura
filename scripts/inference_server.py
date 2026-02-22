"""
Aura Inference Server — persistent FastAPI wrapper for OpenBioLLM-8B.

Keeps the model loaded in VRAM and exposes HTTP endpoints for diagnosis
inference. Designed to run on the GPU server (AMD Radeon RX 9070 XT / ROCm).

Usage (from WSL on the GPU server):
    source ~/venv_rocm/bin/activate
    cd /mnt/c/Users/hackathon/Aura
    python scripts/inference_server.py --port 8099

Endpoints:
    POST /diagnose       - Single clinical text -> diagnosis
    POST /diagnose/batch - List of clinical texts -> list of diagnoses
    GET  /health         - Health check (model loaded, GPU info)
"""

import argparse
import logging
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("aura_inference_server")

app = FastAPI(title="Aura Inference Server", version="1.0.0")

# Global model state -- loaded once at startup
_model = None
_tokenizer = None


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


@app.on_event("startup")
async def startup_load_model():
    global _model, _tokenizer
    from scripts.run_diagnosis_inference import load_model
    logger.info("Loading model at startup...")
    _model, _tokenizer = load_model()
    logger.info("Model loaded and ready for inference.")


@app.get("/health")
async def health():
    import torch
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    mem_used = torch.cuda.memory_allocated(0) / 1e9 if torch.cuda.is_available() else 0
    mem_total = torch.cuda.get_device_properties(0).total_mem / 1e9 if torch.cuda.is_available() else 0
    return {
        "status": "ok",
        "gpu": gpu_name,
        "vram_used_gb": round(mem_used, 2),
        "vram_total_gb": round(mem_total, 2),
    }


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest):
    if _model is None or _tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    from scripts.run_diagnosis_inference import predict

    t0 = time.time()
    diagnosis = predict(_model, _tokenizer, req.text)
    elapsed = time.time() - t0

    logger.info("Diagnosis: %s (%.2fs)", diagnosis, elapsed)
    return DiagnoseResponse(diagnosis=diagnosis, inference_time=round(elapsed, 3))


@app.post("/diagnose/batch", response_model=BatchDiagnoseResponse)
async def diagnose_batch(req: BatchDiagnoseRequest):
    if _model is None or _tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not req.texts:
        raise HTTPException(status_code=400, detail="Empty texts list")

    from scripts.run_diagnosis_inference import predict

    results = []
    t0 = time.time()
    for text in req.texts:
        t_start = time.time()
        diagnosis = predict(_model, _tokenizer, text)
        elapsed = time.time() - t_start
        results.append(DiagnoseResponse(diagnosis=diagnosis, inference_time=round(elapsed, 3)))

    total = time.time() - t0
    logger.info("Batch: %d cases in %.2fs", len(req.texts), total)
    return BatchDiagnoseResponse(results=results, total_time=round(total, 3))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aura Inference Server")
    parser.add_argument("--port", type=int, default=8099, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting Aura Inference Server on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port)
