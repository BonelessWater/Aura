"""
Shared test fixtures for the Aura test suite.

Provides backend test infrastructure (ASGI client, store cleanup, SSE helpers)
and report agent fixtures (requires_databricks, requires_llm, requires_backend,
DEMO_CASES).
"""

import json
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.session import _sessions
from backend.utils.background import _jobs


# ── Report agent demo cases ──────────────────────────────────────────────────

DEMO_CASES = {
    "systemic": "harvard_08670",
    "gi":       "nhanes_90119",
    "nuanced":  "nhanes_73741",
    "healthy":  "nhanes_79163",
}


# ── Startup verification ─────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def verify_backend_startup():
    """Confirm backend imports resolve and app initializes."""
    assert app is not None, "FastAPI app failed to initialize"


# ── App client ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def real_app_client() -> AsyncIterator[AsyncClient]:
    """Real ASGI client running the real FastAPI app in-process."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ── Store cleanup ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_stores():
    """Clear session and job stores before each test."""
    _sessions.clear()
    _jobs.clear()
    yield
    _sessions.clear()
    _jobs.clear()


# ── Sample files ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf() -> Path:
    """A real (minimal) PDF file for upload tests."""
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF\n"
    )
    tmp = Path(tempfile.mktemp(suffix=".pdf"))
    tmp.write_bytes(pdf_bytes)
    yield tmp
    tmp.unlink(missing_ok=True)


# ── LLM availability ─────────────────────────────────────────────────────────

@pytest.fixture
def llm_available():
    """Skip test if no LLM backend (Azure OpenAI or vLLM) is configured."""
    has_azure = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
    if not has_azure and not has_vllm:
        pytest.skip(
            "No LLM backend configured (need AZURE_OPENAI_ENDPOINT or AURA_VLLM_BASE_URL)"
        )


# ── Report agent environment fixtures ────────────────────────────────────────

@pytest.fixture(scope="session")
def requires_databricks():
    if not os.environ.get("DATABRICKS_HOST"):
        pytest.skip("Databricks not configured")


@pytest.fixture(scope="session")
def requires_llm():
    has_azure = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
    if not (has_azure or has_anthropic or has_vllm):
        pytest.skip("No LLM backend configured")


@pytest.fixture(scope="session")
def requires_backend():
    """Skip test if FastAPI backend is not running."""
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2)
        if r.status_code != 200:
            pytest.skip("Backend not healthy")
    except Exception:
        pytest.skip("Backend not running")


# ── SSE helper ────────────────────────────────────────────────────────────────

async def read_sse_events(
    client: AsyncClient,
    patient_id: str,
    timeout: float = 10.0,
) -> AsyncIterator[dict]:
    """
    Connect to the real SSE endpoint and yield parsed event dicts.
    """
    async with client.stream(
        "GET",
        f"/stream/{patient_id}",
        timeout=timeout,
    ) as response:
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", 1)
                for line in raw_event.split("\n"):
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
