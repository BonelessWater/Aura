"""
Phase 3 backend tests: TanStack Query health-check endpoint behaviour.

All tests use ASGITransport (no mocks, no live server required).
"""

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health must respond 200 so the frontend polling succeeds."""
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_sessions_is_integer(client):
    """sessions_active must be an integer (Zustand polling cares about type)."""
    resp = await client.get("/health")
    body = resp.json()
    assert isinstance(body["sessions_active"], int)


@pytest.mark.asyncio
async def test_consecutive_health_calls_consistent(client):
    """Two back-to-back calls must return identical status and vllm values."""
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    b1, b2 = r1.json(), r2.json()
    assert b1["status"] == b2["status"]
    assert b1["vllm"] == b2["vllm"]
