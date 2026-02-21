"""
Aura FastAPI Backend
====================
Run from the repo root:

    uvicorn backend.main:app --reload

Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import databricks_available, get_settings
from backend.session import active_count, evict_stale_sessions
from backend.thought_stream_patch import apply_patch

# Apply ThoughtStream patch before any NLP modules are imported by the routers.
apply_patch()

from backend.routers import (  # noqa: E402 — must come after patch
    extract,
    interview,
    jobs,
    moderate,
    pipeline,
    research,
    route,
    stream,
    translate,
)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Background task: evict stale sessions every 10 minutes.
    async def _gc():
        while True:
            await asyncio.sleep(600)
            evict_stale_sessions(settings.session_ttl_seconds)

    gc_task = asyncio.create_task(_gc())
    yield
    gc_task.cancel()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Aura NLP API",
    description=(
        "Privacy-first, local multi-agent RAG backend for Aura. "
        "Exposes the 6-phase NLP pipeline via HTTP. "
        "This service does not diagnose — all outputs are alignment scores and routing flags."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(extract.router, tags=["Pipeline"])
app.include_router(interview.router, tags=["Pipeline"])
app.include_router(research.router, tags=["Pipeline"])
app.include_router(route.router, tags=["Pipeline"])
app.include_router(translate.router, tags=["Pipeline"])
app.include_router(moderate.router, tags=["Moderation"])
app.include_router(pipeline.router, tags=["Pipeline"])
app.include_router(stream.router, tags=["Streaming"])
app.include_router(jobs.router, tags=["Jobs"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
async def health():
    vllm_url = os.environ.get("VLLM_BASE_URL", "")
    return {
        "status": "ok",
        "databricks": databricks_available(),
        "vllm": bool(vllm_url),
        "sessions_active": active_count(),
    }
