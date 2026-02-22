"""
Phase 2 OpenAPI tests.

All tests fetch the real /openapi.json from the real FastAPI app running
in-process via ASGITransport. No live server required.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_openapi_spec_accessible(real_app_client: AsyncClient):
    """GET /openapi.json returns valid JSON with an 'openapi' version key."""
    response = await real_app_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data, "Missing 'openapi' key in spec"


@pytest.mark.asyncio
async def test_spec_contains_all_endpoints(real_app_client: AsyncClient):
    """All 10 required endpoint paths are present in the spec."""
    response = await real_app_client.get("/openapi.json")
    paths = response.json().get("paths", {})

    required = [
        "/extract",
        "/interview",
        "/research",
        "/route",
        "/translate",
        "/moderate",
        "/pipeline/full",
        "/stream/{patient_id}",
        "/jobs/{job_id}",
        "/health",
    ]
    for path in required:
        assert path in paths, f"Missing endpoint in OpenAPI spec: {path}"


@pytest.mark.asyncio
async def test_spec_defines_schemas(real_app_client: AsyncClient):
    """components.schemas contains at least 5 schema definitions."""
    response = await real_app_client.get("/openapi.json")
    schemas = response.json().get("components", {}).get("schemas", {})
    assert len(schemas) >= 5, (
        f"Expected at least 5 schema definitions, got {len(schemas)}: {list(schemas)}"
    )


@pytest.mark.asyncio
async def test_extract_endpoint_accepts_multipart(real_app_client: AsyncClient):
    """POST /extract declares multipart/form-data as its request body content type."""
    response = await real_app_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    post_body = (
        paths.get("/extract", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
    )
    assert "multipart/form-data" in post_body, (
        "/extract POST does not declare multipart/form-data"
    )


@pytest.mark.asyncio
async def test_pipeline_endpoint_accepts_multipart(real_app_client: AsyncClient):
    """POST /pipeline/full declares multipart/form-data as its request body content type."""
    response = await real_app_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    post_body = (
        paths.get("/pipeline/full", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
    )
    assert "multipart/form-data" in post_body, (
        "/pipeline/full POST does not declare multipart/form-data"
    )


@pytest.mark.asyncio
async def test_interview_endpoint_accepts_multipart(real_app_client: AsyncClient):
    """POST /interview declares multipart/form-data as its request body content type."""
    response = await real_app_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    post_body = (
        paths.get("/interview", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
    )
    assert "multipart/form-data" in post_body, (
        "/interview POST does not declare multipart/form-data"
    )
