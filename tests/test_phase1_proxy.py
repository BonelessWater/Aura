"""
Phase 1 proxy tests.

All tests hit the real running backend directly via httpx (not through the
Vite proxy, which only runs during `pnpm dev`). The proxy rewrite test is
skipped when the Vite dev server is not running.

Tests that need the backend running are skipped automatically when it's down.
"""
from __future__ import annotations

import logging

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app

logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"
VITE_URL = "http://localhost:5173"

# ---------------------------------------------------------------------------
# Connectivity guards
# ---------------------------------------------------------------------------

def _backend_up() -> bool:
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=2)
        return r.status_code == 200
    except httpx.ConnectError:
        return False


def _vite_up() -> bool:
    try:
        r = httpx.get(f"{VITE_URL}/api/health", timeout=2)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.ReadError):
        return False


# ---------------------------------------------------------------------------
# Tests against the real ASGI app (in-process, no live server needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_returns_ok(real_app_client: AsyncClient):
    """GET /health returns 200 with status ok."""
    response = await real_app_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_includes_required_fields(real_app_client: AsyncClient):
    """Health response contains all four required fields."""
    response = await real_app_client.get("/health")
    data = response.json()
    for field in ("status", "databricks", "vllm", "sessions_active"):
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_cors_headers_present(real_app_client: AsyncClient):
    """OPTIONS /health returns CORS allow-origin header."""
    response = await real_app_client.options(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    assert "access-control-allow-origin" in headers_lower, (
        "CORS header 'access-control-allow-origin' missing from OPTIONS response"
    )


@pytest.mark.skipif(not _vite_up(), reason="Vite dev server not running")
def test_proxy_rewrite_strips_prefix():
    """
    GET http://localhost:5173/api/health reaches backend /health
    and returns the same body as a direct call to the backend.
    """
    direct = httpx.get(f"{BACKEND_URL}/health", timeout=5).json()
    proxied = httpx.get(f"{VITE_URL}/api/health", timeout=5).json()
    assert proxied["status"] == direct["status"]
    assert set(proxied.keys()) == set(direct.keys())
