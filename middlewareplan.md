# Aura Middleware Integration Plan

## Overview

This plan connects the React 18 + Vite frontend to the FastAPI backend through a
tested, incremental middleware stack. Each phase is a standalone deliverable with
its own test suite. No phase begins until the previous phase's tests pass.

**Stack summary:**

| Layer              | Package                          | Size      |
|--------------------|----------------------------------|-----------|
| Type safety        | `openapi-typescript` + `openapi-fetch` | ~5 kB     |
| Server state       | `@tanstack/react-query` v5       | ~13 kB    |
| Client state       | `zustand`                        | ~1.2 kB   |
| SSE streaming      | `@microsoft/fetch-event-source`  | ~2 kB     |
| Dev proxy          | Vite `server.proxy`              | 0 kB      |
| **Total addition** |                                  | **~21 kB**|

---

## Core Anti-Pattern: NO MOCKED TESTS

This is a hard rule for the entire plan. Mocked tests verify assumptions, not
reality. They pass when the real system is broken and give false confidence.

**What this means in practice:**

- Backend tests hit the REAL FastAPI app via `httpx.AsyncClient(app=app)` --
  the actual ASGI app, not a fake.
- Backend tests call the REAL session store, REAL file handling, REAL routers.
- Frontend tests hit the REAL running backend through the REAL Vite proxy.
  If the backend is not running, tests are SKIPPED, not faked with MSW/mocks.
- No `unittest.mock.patch` on internal code. No MSW handlers faking API
  responses. No fake timers simulating SSE events.

**The only acceptable skip:**

```python
import httpx
import pytest

BACKEND_UP = False
try:
    r = httpx.get("http://localhost:8000/health", timeout=2)
    BACKEND_UP = r.status_code == 200
except httpx.ConnectError:
    pass

@pytest.mark.skipif(not BACKEND_UP, reason="Backend not running")
def test_something_real():
    ...
```

---

## Bug-Driven Testing Protocol

Bugs found during development are treated as test opportunities, not annoyances.

**Process:**

1. A bug is discovered (upload fails silently, SSE drops events, polling
   continues after done, etc.)
2. BEFORE fixing the bug, write a test that reproduces it. The test MUST FAIL.
3. Fix the bug.
4. Confirm the test now passes.
5. The test lives permanently in `tests/regressions/`. It is never deleted.

**Naming convention:**

```
tests/regressions/test_regression_<phase>_<short_description>.py
```

Examples:
- `test_regression_phase4_upload_silently_drops_zero_byte_file.py`
- `test_regression_phase6_sse_hangs_when_session_evicted.py`
- `test_regression_phase5_polling_continues_after_done_status.py`

**Each regression test file contains:**
- A docstring explaining what the bug was and when it was found
- The exact steps to reproduce
- The fix summary (one line)

```python
"""
Regression: Phase 4 -- Upload silently accepted a 0-byte PDF without error.
Found: During Phase 4 development.
Fix: Added `file.size < 1024` check in validateAndAddFile() and backend
     extract router now validates file content length > 0.
"""
```

These tests accumulate over time and form a living record of every edge case
the system has encountered. They run with the rest of the suite on every
`pytest` invocation.

---

## Phase 0: Infrastructure Verification + Test Scaffolding

**Goal:** Verify the backend starts, create test infrastructure, and fix missing
project configuration so every subsequent phase has a working foundation.

The `nlp/` package already exists (commit `4da49ae`) with full implementations
of all pipeline functions and Pydantic schemas. Phase 0 does NOT create stubs --
it verifies everything works and sets up the test scaffolding.

### 0.1 Actual NLP schema shapes (reference for all subsequent phases)

The frontend must consume the ACTUAL data shapes from `nlp/shared/schemas.py`.
These are the real types the backend returns -- the frontend must map to these,
not invent its own:

**LabReport:**
```
patient_id: str
markers: list[MarkerTimeline]       -- NOT "biomarkers"
  MarkerTimeline:
    loinc_code: Optional[str]
    display_name: str               -- e.g. "CRP", "WBC"
    values: list[MarkerValue]
      MarkerValue:
        loinc_code: Optional[str]
        display_name: str
        date: str
        value: float
        unit: str
        ref_range_low: Optional[float]
        ref_range_high: Optional[float]
        flag: MarkerFlag (HIGH | LOW | NORMAL)
        z_score_nhanes: Optional[float]
    trend: Optional[Trend] (STABLE | ESCALATING | RESOLVING)
bio_fingerprint: BioFingerprint
  NLR, PLR, MLR, SII, CRP_Albumin, C3_C4: list[RatioTimepoint]
    RatioTimepoint: { date: str, value: float, flag: Optional[str] }
  ANA_titer_trend: Optional[Trend]
  sustained_abnormalities: list[str]
  morphological_shifts: list[str]
thought_stream_event: Optional[ThoughtStreamEvent]
```

**InterviewResult:**
```
patient_id: str
raw_text: str                       -- NOT "raw_narrative"
symptoms: list[SymptomEntity]
  SymptomEntity:
    entity: str                     -- NOT "term"
    location: Optional[str]
    duration_months: Optional[int]  -- NOT "duration: str"
    severity: Optional[str]
    onset: Optional[str]
    cluster_signal: Optional[Cluster] (SYSTEMIC | GI | ENDOCRINE)
    snomed_concept: Optional[str]
visual_keywords: list[str]          -- NOT "vision_findings"
thought_stream_event: Optional[ThoughtStreamEvent]
```

**ResearchResult:**
```
patient_id: str
sub_queries: list[str]              -- NOT "articles"
passages: list[RetrievedPassage]    -- NOT "guidelines"
  RetrievedPassage:
    chunk_id: str
    doi: Optional[str]
    journal: Optional[str]
    year: Optional[int]
    section: Optional[str]
    cluster_tag: Optional[Cluster]
    text: str
    score: float
thought_stream_event: Optional[ThoughtStreamEvent]
```

**RouterOutput:**
```
patient_id: str
cluster: Cluster (SYSTEMIC | GI | ENDOCRINE)
cluster_alignment_score: float
routing_recommendation: str
disease_candidates: list[DiseaseCandidate]   -- NOT "conditions"
  DiseaseCandidate:
    disease: str                              -- NOT "condition"
    disease_alignment_score: float            -- NOT "probability"
    supporting_dois: list[str]
    criteria_met: list[str]
    criteria_count: int
    criteria_cap_applied: bool
    drug_induced_flag: bool
thought_stream_event: Optional[ThoughtStreamEvent]
```

**TranslatorOutput:**
```
patient_id: str
soap_note: str                      -- single string, NOT list[SOAPSection]
layman_compass: str                 -- single string, NOT LaymansCompass object
faithfulness_score: float
flagged_sentences: list[str]
fk_grade_level: Optional[float]
thought_stream_event: Optional[ThoughtStreamEvent]
```

**ModerationResult:**
```
post_id: str
text: str
action: ModerationAction (SUPPRESS | FLAG | ALLOW | DISCLAIMER)  -- NOT "flagged: bool"
confidence: float
extracted_drugs: list[str]
extracted_dosages: list[str]
reason: Optional[str]
thought_stream_event: Optional[ThoughtStreamEvent]
```

### 0.2 Bug fix: Health endpoint env var mismatch

The health endpoint in `backend/main.py` checks `os.environ.get("VLLM_BASE_URL")`
to report vLLM availability, but `backend/config.py` uses `env_prefix = "AURA_"`,
meaning the Settings class reads `AURA_VLLM_BASE_URL`. These are different
environment variables. The health endpoint will always report `vllm: false` even
when `AURA_VLLM_BASE_URL` is set.

**Fix:** Change the health endpoint to use `settings.vllm_base_url` (which is
already loaded from the correct `AURA_VLLM_BASE_URL` env var) instead of reading
`os.environ` directly:

```python
# backend/main.py -- health endpoint fix
from backend.config import settings

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "databricks": bool(settings.write_to_databricks),
        "vllm": bool(settings.vllm_base_url),
        "sessions_active": active_count(),
    }
```

The `llm_available` test fixture in `tests/conftest.py` should also check BOTH
env vars for compatibility:
```python
has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
```
(This is already correct in the conftest.py defined in Phase 0.)

### 0.3 What to build

1. **Backend Python dependencies** -- `requirements.txt` lists only data science
   packages. The FastAPI backend needs its own dependency file:

   Create `backend/requirements.txt`:
   ```
   fastapi>=0.110
   uvicorn[standard]>=0.29
   pydantic>=2.0
   pydantic-settings>=2.0
   aiofiles>=23.0
   sse-starlette>=1.6
   python-multipart>=0.0.9
   httpx>=0.27
   pytest>=8.0
   pytest-asyncio>=0.23
   ```

2. **TypeScript configuration** -- No `tsconfig.json` exists. Multiple phases
   use `npx tsc --noEmit` as a done gate. Create a minimal config:

   Create `tsconfig.json`:
   ```json
   {
     "compilerOptions": {
       "target": "ES2020",
       "module": "ESNext",
       "moduleResolution": "bundler",
       "jsx": "react-jsx",
       "strict": true,
       "noEmit": true,
       "skipLibCheck": true,
       "esModuleInterop": true,
       "baseUrl": ".",
       "paths": { "@/*": ["./src/*"] }
     },
     "include": ["src"]
   }
   ```

3. **Test infrastructure** -- Create `tests/conftest.py` with all shared fixtures
   (needed from Phase 0 onward, not Phase 8):

   ```python
   import json
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


   # -- startup verification --

   @pytest.fixture(scope="session", autouse=True)
   def verify_backend_startup():
       """Confirm backend imports resolve and app initializes."""
       assert app is not None, "FastAPI app failed to initialize"


   # -- app client --

   @pytest_asyncio.fixture
   async def real_app_client() -> AsyncIterator[AsyncClient]:
       """Real ASGI client running the real FastAPI app in-process."""
       transport = ASGITransport(app=app)
       async with AsyncClient(transport=transport, base_url="http://test") as client:
           yield client


   # -- store cleanup --

   @pytest.fixture(autouse=True)
   def clean_stores():
       """Clear session and job stores before each test."""
       _sessions.clear()
       _jobs.clear()
       yield
       _sessions.clear()
       _jobs.clear()


   # -- sample files --

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


   # -- LLM availability --

   @pytest.fixture
   def llm_available():
       """Skip test if no LLM backend (Azure OpenAI or vLLM) is configured."""
       import os
       has_azure = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
       has_vllm = bool(os.environ.get("AURA_VLLM_BASE_URL"))
       if not has_azure and not has_vllm:
           pytest.skip("No LLM backend configured (need AZURE_OPENAI_ENDPOINT or AURA_VLLM_BASE_URL)")


   # -- SSE helper --

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
   ```

4. **React dependency check** -- `package.json` lists `react` and `react-dom`
   as `peerDependencies` (optional), not `dependencies`. All hooks from Phase
   3 onward require React. Verify that `pnpm` resolves React correctly. If
   `import React from 'react'` fails in a test file, move React and
   React-DOM to `dependencies`:

   ```bash
   pnpm add react@18.3.1 react-dom@18.3.1
   ```

5. **pnpm test script** -- `package.json` has no test script. Add one so
   frontend tests are runnable:

   Add to `package.json` scripts:
   ```json
   "test": "vitest run",
   "test:watch": "vitest"
   ```

5. **Environment file** -- Create `.env.example` documenting required variables
   (the actual `.env` with credentials must NEVER be committed):

   ```
   # LLM Backend (at least one required for full pipeline)
   AZURE_OPENAI_ENDPOINT=
   AZURE_OPENAI_API_KEY=
   AZURE_OPENAI_DEPLOYMENT_GPT4O=
   AURA_VLLM_BASE_URL=

   # Databricks (optional -- research phase skipped without it)
   DATABRICKS_HOST=

   # Backend settings
   AURA_WRITE_TO_DATABRICKS=false
   AURA_SESSION_TTL_SECONDS=3600
   AURA_MAX_UPLOAD_SIZE_MB=50
   ```

### 0.4 Files created / modified

| File | Action |
|------|--------|
| `backend/main.py` | Edit: fix health endpoint to use `settings.vllm_base_url` instead of `os.environ["VLLM_BASE_URL"]` |
| `backend/requirements.txt` | Create: FastAPI + testing dependencies |
| `tsconfig.json` | Create: TypeScript configuration |
| `tests/conftest.py` | Create: all shared test fixtures |
| `package.json` | Edit: add `test` and `test:watch` scripts |
| `.env.example` | Create: document required environment variables |
| `.gitignore` | Edit: ensure `.env` is listed (never commit credentials) |

### 0.5 Test suite

**File:** `tests/test_phase0_bootstrap.py`

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_backend_imports_without_error` | `from backend.session import get_or_create_session` resolves | No ImportError |
| 2 | `test_nlp_schemas_import` | `from nlp.shared.schemas import LabReport, InterviewResult, ...` resolves | No ImportError |
| 3 | `test_thought_stream_import` | `from nlp.shared.thought_stream import ThoughtStream` resolves | No ImportError |
| 4 | `test_thought_stream_emit_returns_event` | `ThoughtStream.emit(agent="test", step="init", summary="ok")` returns event | Return has `agent`, `step`, `summary`, `timestamp` |
| 5 | `test_lab_report_has_markers_field` | `LabReport(patient_id="x")` has `markers` (list) not `biomarkers` | Field name is `markers` |
| 6 | `test_router_output_has_disease_candidates` | `RouterOutput(...)` has `disease_candidates` not `conditions` | Field name is `disease_candidates` |
| 7 | `test_translator_output_soap_is_string` | `TranslatorOutput(...)` has `soap_note` as `str` not `list` | `isinstance(output.soap_note, str)` |
| 8 | `test_moderation_result_uses_action_enum` | `ModerationResult(...)` has `action` (enum) not `flagged` (bool) | `action` is `ModerationAction` |
| 9 | `test_backend_app_starts` | `httpx.AsyncClient(transport=ASGITransport(app=app))` + `GET /health` returns 200 | HTTP 200 |
| 10 | `test_thought_stream_patch_applies` | Call `apply_patch()`, emit with `patient_id`, check session events | Event appears in session |
| 11 | `test_run_extractor_callable` | `run_extractor(patient_id, [], 40, "F", False)` returns `LabReport` | Returns LabReport instance |
| 12 | `test_run_moderator_callable` | `run_moderator("p1", "text", None, False)` returns `ModerationResult` | Returns ModerationResult instance |
| 13 | `test_health_vllm_uses_settings_not_environ` | Health endpoint reads `settings.vllm_base_url` (from `AURA_VLLM_BASE_URL`), not `os.environ["VLLM_BASE_URL"]` | Response `vllm` field reflects `settings.vllm_base_url` value |

### 0.6 Done gate

- `pip install -r backend/requirements.txt` succeeds
- `python -c "from backend.main import app"` succeeds
- `uvicorn backend.main:app` starts and `GET /health` returns 200
- `pytest tests/test_phase0_bootstrap.py` -- all 13 tests green
- `npx tsc --noEmit` completes (even if with warnings from existing code)

---

## Phase 1: Vite Dev Proxy + Health Check Smoke Test

**Goal:** Confirm the frontend dev server can reach the FastAPI backend through a
proxy so every subsequent phase has a working transport layer.

### 1.1 What to build

- Add `server.proxy` to `vite.config.ts` forwarding `/api/*` to `http://localhost:8000`
- Add an SSE-aware proxy entry for `/api/stream/*` with buffering disabled:

```typescript
// vite.config.ts server.proxy addition
server: {
  proxy: {
    '/api/stream': {
      target: 'http://localhost:8000',
      rewrite: (path) => path.replace(/^\/api/, ''),
      // SSE: disable response buffering so events stream immediately
      configure: (proxy) => {
        proxy.on('proxyRes', (proxyRes) => {
          proxyRes.headers['cache-control'] = 'no-cache';
          proxyRes.headers['x-accel-buffering'] = 'no';
        });
      },
    },
    '/api': {
      target: 'http://localhost:8000',
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
},
```

- Create `src/api/client.ts` exporting a single `fetchHealth()` function using
  raw `fetch` against `/api/health`
- Create a temporary `<DevHealthBadge />` component that calls `fetchHealth()`
  on mount and renders the JSON status (remove after Phase 1 verification)

### 1.2 Files created / modified

| File | Action |
|------|--------|
| `vite.config.ts` | Edit: add `server.proxy` block |
| `src/api/client.ts` | Create: `fetchHealth()` wrapper |
| `src/app/components/shared/DevHealthBadge.tsx` | Create: temporary smoke-test component |

### 1.3 Test suite

**File:** `tests/test_phase1_proxy.py`

All tests hit the real running backend. Skipped if backend is down.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_health_returns_ok` | `GET /health` returns 200 with `{"status": "ok"}` | HTTP 200, `status` field equals `"ok"` |
| 2 | `test_health_includes_required_fields` | Response contains `status`, `databricks`, `vllm`, `sessions_active` | All four keys present |
| 3 | `test_cors_headers_present` | `OPTIONS /health` returns CORS headers | `access-control-allow-origin` header present |
| 4 | `test_proxy_rewrite_strips_prefix` | `GET http://localhost:5173/api/health` reaches backend `/health` | Same response body as direct `GET http://localhost:8000/health` |

**Frontend test file:** `src/__tests__/phase1_health.test.ts`

Tests call the real backend through the real Vite proxy. Skipped if backend is
not running.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `fetchHealth resolves with status ok` | `fetchHealth()` hits real `/api/health` and returns `status: "ok"` |
| 2 | `fetchHealth throws on network error` | Stop backend, call `fetchHealth()`, confirm it throws |

### 1.4 Done gate

- `pytest tests/test_phase1_proxy.py` -- all 4 tests green (backend running)
- Frontend health badge renders `"ok"` in the browser
- Remove `DevHealthBadge` component after verification

---

## Phase 2: OpenAPI Type Generation

**Goal:** Generate TypeScript types from FastAPI's OpenAPI spec so every
subsequent API call is type-safe at compile time.

### 2.1 What to build

- Install `openapi-typescript` as a dev dependency
- Install `openapi-fetch` as a runtime dependency
- Add an npm script `gen:api` that runs:
  `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts`
- Generate `src/api/schema.d.ts` from the running backend
- Replace the raw `fetch` in `src/api/client.ts` with a typed `openapi-fetch`
  client instance
- Export typed helper functions: `apiClient.GET(...)`, `apiClient.POST(...)`

**Multipart FormData caveat:** `openapi-fetch` does not auto-build `FormData`
for multipart endpoints. Endpoints that accept `multipart/form-data` (`/extract`,
`/interview`, `/pipeline/full`) need a separate helper:

```typescript
// src/api/client.ts

import createClient from 'openapi-fetch';
import type { paths } from './schema';

// Typed JSON client -- used for all JSON endpoints
export const apiClient = createClient<paths>({ baseUrl: '/api' });

// Multipart helper -- used for /extract, /interview, /pipeline/full
// openapi-fetch cannot auto-build FormData, so we do it manually
// while keeping the return type from the generated schema.
export async function postMultipart<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type -- browser sets it with boundary
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}
```

This dual-client approach keeps JSON endpoints fully type-safe while giving
multipart endpoints a clean escape hatch.

### 2.2 Files created / modified

| File | Action |
|------|--------|
| `package.json` | Edit: add `openapi-typescript` (dev), `openapi-fetch` (runtime), `gen:api` script |
| `src/api/schema.d.ts` | Create: auto-generated (never hand-edit) |
| `src/api/client.ts` | Edit: replace raw fetch with `createClient<paths>()` + `postMultipart()` |

### 2.3 Test suite

**File:** `tests/test_phase2_openapi.py`

All tests fetch the real `/openapi.json` from the real backend.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_openapi_spec_accessible` | `GET /openapi.json` returns valid JSON | HTTP 200, JSON parseable, `"openapi"` key present |
| 2 | `test_spec_contains_all_endpoints` | Spec includes `/extract`, `/interview`, `/research`, `/route`, `/translate`, `/moderate`, `/pipeline/full`, `/stream/{patient_id}`, `/jobs/{job_id}`, `/health` | All 10 paths present in `paths` object |
| 3 | `test_spec_defines_schemas` | Spec's `components.schemas` is non-empty | At least 5 schema definitions exist |
| 4 | `test_extract_endpoint_accepts_multipart` | `/extract` POST consumes `multipart/form-data` | Request body content type is multipart |
| 5 | `test_pipeline_endpoint_accepts_multipart` | `/pipeline/full` POST consumes `multipart/form-data` | Request body content type is multipart |
| 6 | `test_interview_endpoint_accepts_multipart` | `/interview` POST consumes `multipart/form-data` | Request body content type is multipart |

**Frontend test file:** `src/__tests__/phase2_typed_client.test.ts`

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `typed client GET /health compiles and returns` | `apiClient.GET("/health")` hits real backend and returns typed response |
| 2 | `schema.d.ts contains paths type` | Import of `paths` from schema.d.ts does not error |
| 3 | `typed client rejects unknown endpoint at compile time` | `npx tsc --noEmit` fails if you call `apiClient.GET("/nonexistent")` |
| 4 | `postMultipart sends FormData and returns JSON` | Build FormData with a file, POST to `/extract`, confirm JSON response |

### 2.4 Done gate

- `pnpm run gen:api` completes without errors
- `src/api/schema.d.ts` exists and contains `paths` interface
- `npx tsc --noEmit` passes (no type errors in `client.ts`)
- `pytest tests/test_phase2_openapi.py` -- all 6 tests green

---

## Phase 3: TanStack Query + Zustand Setup

**Goal:** Install TanStack Query and Zustand, wrap the app in
`QueryClientProvider`, define the patient ID lifecycle, and wire the first
live query (health check).

### 3.1 Patient ID lifecycle

The patient ID is the key that ties frontend state to backend sessions. Its
lifecycle must be explicit:

1. **Generation:** `crypto.randomUUID()` on first visit (no backend call needed)
2. **Persistence:** Stored in Zustand with `persist` middleware backed by
   `localStorage`. Survives page refresh and tab close/reopen.
3. **Scope:** One patient ID per browser tab. Multiple tabs = independent
   sessions (each generates its own UUID on first visit).
4. **Reset:** User clicks "Start Over" -> `usePatientStore.getState().reset()`
   clears the UUID and all pipeline data. A new UUID is generated on the next
   intake start.
5. **Backend binding:** The patient ID is sent as a form field or JSON body
   field on every API call. The backend creates a `PatientSession` on first
   sight via `get_or_create_session()`.

```typescript
// src/api/hooks/usePatientStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PatientState {
  patientId: string | null;
  jobId: string | null;
  pipelineStatus: 'idle' | 'uploading' | 'processing' | 'done' | 'error';

  // Intake data (collected across wizard steps, sent on submit)
  pdfs: File[];                              // field name matches backend
  symptoms: string;
  selectedChips: string[];
  images: File[];                            // from StepVision photo capture
  patientAge: number;
  patientSex: string;
  medications: string;                       // comma-separated

  // Actions
  ensurePatientId: () => string;
  setJobId: (id: string) => void;
  setPipelineStatus: (status: PatientState['pipelineStatus']) => void;
  setPdfs: (files: File[]) => void;
  setSymptoms: (text: string) => void;
  toggleChip: (chip: string) => void;
  setImages: (files: File[]) => void;
  setPatientAge: (age: number) => void;
  setPatientSex: (sex: string) => void;
  setMedications: (meds: string) => void;
  reset: () => void;
}

const INITIAL = {
  patientId: null,
  jobId: null,
  pipelineStatus: 'idle' as const,
  pdfs: [] as File[],
  symptoms: '',
  selectedChips: [] as string[],
  images: [] as File[],
  patientAge: 40,
  patientSex: 'F',
  medications: '',
};

export const usePatientStore = create<PatientState>()(
  persist(
    (set, get) => ({
      ...INITIAL,
      ensurePatientId: () => {
        let id = get().patientId;
        if (!id) {
          id = crypto.randomUUID();
          set({ patientId: id });
        }
        return id;
      },
      setJobId: (id) => set({ jobId: id }),
      setPipelineStatus: (status) => set({ pipelineStatus: status }),
      setPdfs: (files) => set({ pdfs: files }),
      setSymptoms: (text) => set({ symptoms: text }),
      toggleChip: (chip) => set((s) => ({
        selectedChips: s.selectedChips.includes(chip)
          ? s.selectedChips.filter((c) => c !== chip)
          : [...s.selectedChips, chip],
      })),
      setImages: (files) => set({ images: files }),
      setPatientAge: (age) => set({ patientAge: age }),
      setPatientSex: (sex) => set({ patientSex: sex }),
      setMedications: (meds) => set({ medications: meds }),
      reset: () => set(INITIAL),
    }),
    {
      name: 'aura-patient',
      partialize: (state) => ({
        patientId: state.patientId,  // persist only the ID
      }),
    },
  ),
);
```

**Key design decisions:**
- `pdfs` not `files` -- matches the backend form field name exactly
- `images` not `visionFiles.images` -- no videos because `/pipeline/full`
  does not accept a `videos` field (only `/interview` does standalone)
- `medications` included -- backend accepts comma-separated string, `run_router`
  uses it for drug-induced flag checking
- `patientAge` and `patientSex` included -- backend defaults to 40/F but we
  should collect real values (see Phase 5 for UI)

### 3.2 What to build

- Install `@tanstack/react-query`, `@tanstack/react-query-devtools`, `zustand`
- Create `src/api/queryClient.ts` with sensible defaults:
  - `staleTime: 30_000` (30s)
  - `retry: 2`
  - `refetchOnWindowFocus: false` (medical context -- avoid surprise refetches)
- Wrap `<App />` in `<QueryClientProvider>`
- Create `src/api/hooks/usePatientStore.ts` (Zustand store as defined above)
- Create `src/api/hooks/useHealth.ts` -- a `useQuery` hook that calls
  `apiClient.GET("/health")` and returns typed health data
- Wire `useHealth` into the Navbar to show a connection indicator dot
  (green = ok, red = unreachable)

**Routing note:** All routes are defined in `src/app/routes.tsx` using
`createBrowserRouter`. Existing routes: `/` (Home), `/dashboard`
(ResultsDashboard), `/vault` (Vault), `/clinician/:id` and `/clinician`
(ClinicianPortal). No route changes needed in Phase 3. The `QueryClientProvider`
wraps at the `App.tsx` level, above the router.

### 3.3 Files created / modified

| File | Action |
|------|--------|
| `package.json` | Edit: add `@tanstack/react-query`, devtools, `zustand` |
| `src/api/queryClient.ts` | Create: QueryClient singleton with defaults |
| `src/api/hooks/usePatientStore.ts` | Create: Zustand patient state store with persist |
| `src/app/App.tsx` | Edit: wrap in `QueryClientProvider` |
| `src/api/hooks/useHealth.ts` | Create: typed health query hook |
| `src/app/components/layout/Navbar.tsx` | Edit: add connection indicator |

### 3.4 Test suite

**File:** `tests/test_phase3_query.py`

All tests hit the real backend.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_health_returns_200` | Backend health endpoint is reachable | HTTP 200 |
| 2 | `test_health_sessions_is_integer` | `sessions_active` field is an integer | Type check passes |
| 3 | `test_consecutive_health_calls_consistent` | Two rapid calls return same structure | Both responses have identical keys |

**Frontend test file:** `src/__tests__/phase3_useHealth.test.ts`

All tests hit real backend. Skipped if backend is down.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `useHealth returns data on success` | Hook calls real backend, resolves with `{ status: "ok", ... }` |
| 2 | `useHealth sets isError on failure` | Stop backend, hook sets `isError: true` |
| 3 | `useHealth does not refetch on window focus` | Verify QueryClient config has `refetchOnWindowFocus: false` |
| 4 | `QueryClientProvider is mounted` | App renders without provider errors against real backend |
| 5 | `patient store generates UUID on ensurePatientId` | Call `ensurePatientId()`, confirm it returns a valid UUID |
| 6 | `patient store persists patientId across remounts` | Write ID, unmount store, remount, ID still present |
| 7 | `patient store reset clears all fields` | Call `reset()`, confirm every field is back to initial |

### 3.5 Done gate

- Navbar connection dot is green when backend runs, red when stopped
- React Query DevTools panel opens in browser (dev mode only)
- Patient ID is generated and persists in localStorage
- `pytest tests/test_phase3_query.py` -- all 3 tests green
- Frontend tests pass against real backend

---

## Phase 4: File Upload Mutation (IntakeWizard -> /extract)

**Goal:** Replace the fake `setTimeout` file parsing in `IntakeWizard.tsx` with a
real multipart upload to `POST /extract`.

### 4.1 Backend form field mapping

The `/extract` endpoint accepts these form fields (not JSON body):

| Form field | Type | Default | Notes |
|------------|------|---------|-------|
| `patient_id` | `str` | required | UUID from Zustand |
| `patient_age` | `int` | `40` | collected in intake |
| `patient_sex` | `str` | `"F"` | collected in intake |
| `files` | `list[UploadFile]` | `[]` | **field name is `files`** |

The `useMutation` hook must build `FormData` with these exact field names.
Note: `/extract` uses field name `files`, but `/pipeline/full` uses `pdfs`.

### 4.2 Partial upload failure handling

When multiple files are uploaded and one fails:
- The backend's `save_uploads()` context manager saves all files to a temp dir
  before calling the extractor. If one file has bad content (not a valid PDF),
  the extractor should still process the others and include partial results.
- The frontend should show per-file status indicators:
  - Green checkmark: file processed successfully
  - Red X: file failed (with error message from backend)
  - Spinner: file still processing
- The upload mutation should NOT treat a partial failure as a full error. If
  the backend returns 200 with results, show results even if some files had
  issues. Only treat HTTP 4xx/5xx as a full error.

### 4.3 What to build

- Create `src/api/hooks/useExtract.ts` -- a `useMutation` hook that:
  - Accepts `{ patientId, files, age, sex }`
  - Builds `FormData` with field name `files` (matching backend)
  - POSTs to `/extract` via `postMultipart()`
  - Returns response containing `lab_report` (actual shape: `LabReport` with
    `markers: list[MarkerTimeline]`, `bio_fingerprint`, etc.)
- Modify `IntakeWizard.tsx`:
  - Replace `setTimeout` mock parsing with `useExtract.mutateAsync()`
  - Show upload progress via mutation state (`isPending`, `isError`)
  - Store uploaded files in Zustand via `setPdfs()`
- Modify `StepUpload.tsx`:
  - Update file status based on mutation lifecycle
  - Show real error messages from backend on failure

### 4.4 Files created / modified

| File | Action |
|------|--------|
| `src/api/hooks/useExtract.ts` | Create: extract mutation hook |
| `src/app/components/intake/IntakeWizard.tsx` | Edit: replace setTimeout with mutation |
| `src/app/components/intake/steps/StepUpload.tsx` | Edit: wire mutation status to UI |

### 4.5 Test suite

**File:** `tests/test_phase4_extract.py`

All tests use `httpx.AsyncClient(transport=ASGITransport(app=app))` which runs
the REAL FastAPI app in-process. Tests that exercise `run_extractor` end-to-end
are skipped if no LLM backend is configured.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_extract_requires_files` | `POST /extract` with no files returns 400 | HTTP 400, detail mentions "PDF" |
| 2 | `test_extract_accepts_pdf` | `POST /extract` with a real small PDF (real bytes, real multipart) | HTTP 200, response contains `patient_id` and `lab_report` |
| 3 | `test_extract_lab_report_has_markers` | Response `lab_report` has `markers` field (not `biomarkers`) | `markers` key exists |
| 4 | `test_extract_creates_session` | After a request, real session store has the patient_id | `get_session(patient_id)` returns non-None |
| 5 | `test_extract_session_persists_across_calls` | Two extract calls with same patient_id share one session | Session object is identical |
| 6 | `test_extract_rejects_empty_patient_id` | `POST /extract` with blank patient_id | HTTP 422 validation error |
| 7 | `test_extract_file_cleanup` | After request completes, temp files are deleted | No leftover temp dirs matching `aura_*` |

**Frontend test file:** `src/__tests__/phase4_useExtract.test.ts`

All tests hit real backend. Skipped if backend not running.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `upload a real PDF and get back a lab_report` | Upload a small real PDF, confirm response has `lab_report` with `markers` |
| 2 | `upload with no files shows 400 error in UI` | Trigger mutation with empty files, confirm `isError` is set |
| 3 | `patient store has pdfs after file selection` | Zustand store's `pdfs` array is populated |
| 4 | `upload progress shows isPending during flight` | Mutation is pending while real request is in-flight |

### 4.6 Done gate

- Upload a real PDF in the intake wizard and see real backend response
- `pytest tests/test_phase4_extract.py` -- all tests green
- Frontend tests pass against real backend
- TypeScript compiles without errors (`npx tsc --noEmit`)

---

## Phase 5: Intake Step Wiring + Full Pipeline Dispatch

**Goal:** Wire the remaining intake steps (StepSymptoms, StepVision) and add
patient demographics collection, then dispatch the full pipeline and poll for
job completion, replacing the hardcoded `setTimeout` steps in Processing.tsx.

### 5.1 Intake data flow

The intake wizard collects data across three steps plus demographics:

1. **StepUpload** -- PDF lab reports (files stored in Zustand as `pdfs`)
2. **StepSymptoms** -- free-text narrative + chip selections
3. **StepVision** -- photos of visible symptoms (images only, no video)

**Patient demographics:** The backend needs `patient_age` (int) and
`patient_sex` (str) for the extractor and router. Currently the intake wizard
has no UI for these. Options:
- Add age/sex fields to StepUpload (alongside file upload)
- Add a separate demographics step
- Collect inline as part of the hero or a pre-intake form

Decision: Add `patient_age` and `patient_sex` fields to the top of
`IntakeWizard` step 1, above the file upload area. Minimal UI: a number
input for age and a select for sex (M/F/Other).

**Medications:** The backend accepts a `medications` field (comma-separated
string). `run_router()` uses it for drug-induced flag checking. Add a
medications text input to StepSymptoms (alongside the symptom narrative).

**How this maps to `/pipeline/full`:**

All intake data is sent in one `POST /pipeline/full` multipart request:

| FormData field | Source | Notes |
|----------------|--------|-------|
| `patient_id` | Zustand `patientId` | UUID |
| `symptom_text` | Zustand `symptoms` | **required field (no default)** -- must always be included in FormData. Send `""` if user skipped symptoms. Omitting it entirely returns 422. |
| `patient_age` | Zustand `patientAge` | defaults to 40 |
| `patient_sex` | Zustand `patientSex` | defaults to "F" |
| `medications` | Zustand `medications` | comma-separated, defaults to "" |
| `pdfs` | Zustand `pdfs` | one `FormData.append` per file |
| `images` | Zustand `images` | one `FormData.append` per file |

**No `videos` field:** `/pipeline/full` does NOT accept videos. Only the
standalone `/interview` endpoint accepts `videos`. If video support is needed
later, it requires either modifying the backend or adding a separate
`/interview` call before the pipeline.

### 5.2 SSE event format (actual)

The backend emits **two types** of events on the same SSE stream. The frontend
must handle both:

**Type 1: Pipeline progress events** (from `_run_full_pipeline`):
```json
{"type": "progress", "phase": "extract", "detail": "Running biomarker extraction"}
{"type": "progress", "phase": "interview", "detail": "Interview complete"}
{"type": "done", "job_id": "abc-123"}
{"type": "error", "job_id": "abc-123", "detail": "Extractor failed: ..."}
```
Field is `phase` (not `agent`). Values are `"extract"`, `"interview"`,
`"research"`, `"route"`, `"translate"` (not `"extractor"`, `"interviewer"`, etc.)

**Note:** The standalone `/research` router also emits done/error events with an
extra `phase` field: `{"type": "done", "phase": "research", "job_id": "..."}`.
The frontend should tolerate `phase` appearing on terminal events -- the
`eventToStepIndex()` function already handles this because it checks `phase`
first regardless of `type`.

**Type 2: ThoughtStream events** (from monkey-patched `ThoughtStream.emit`):
```json
{"agent": "The Extractor", "step": "parse_pdf", "summary": "Parsing page 3 of 5", "patient_id": "...", "timestamp": "..."}
```
Field is `agent`. Values use title-case with "The " prefix:
`"The Extractor"`, `"The Interviewer"`, `"The Researcher"`,
`"The Router"`, `"The Translator"`, `"The Moderator"`.

**Mapping logic in Processing.tsx:**

```typescript
// Handle both event types
function eventToStepIndex(event: Record<string, unknown>): number {
  // Pipeline progress events use "phase"
  const phase = event.phase as string | undefined;
  if (phase) {
    switch (phase) {
      case 'extract': return 0;
      case 'interview': return 1;
      case 'research':
      case 'route': return 2;
      case 'translate': return 3;
      default: return -1;
    }
  }
  // ThoughtStream events use "agent" with "The " prefix and title case
  const agent = event.agent as string | undefined;
  if (agent) {
    switch (agent) {
      case 'The Extractor': return 0;
      case 'The Interviewer': return 1;
      case 'The Researcher':
      case 'The Router': return 2;
      case 'The Translator': return 3;
      default: return -1;
    }
  }
  return -1;
}

// Extract display text from either event type
function eventToLabel(event: Record<string, unknown>): string {
  return (event.detail as string) || (event.summary as string) || '';
}
```

Research and Route collapse into UI step 2 because they are both part of the
"analysis" phase from the user's perspective.

### 5.3 What to build

- Create `src/api/hooks/usePipeline.ts` -- a `useMutation` hook that:
  - Reads all intake data from Zustand store
  - Builds `FormData` with exact field names: `patient_id`, `symptom_text`,
    `patient_age`, `patient_sex`, `medications`, `pdfs`, `images`
  - POSTs to `/pipeline/full` via `postMultipart()`
  - Returns `{ patient_id, job_id, status: "queued" }`
  - Stores `jobId` in the patient store
- Create `src/api/hooks/useJobStatus.ts` -- a `useQuery` hook that:
  - Polls `GET /jobs/{job_id}` every 2 seconds while `status !== "done" && status !== "error"`
  - Uses `refetchInterval: (query) => query.state.data?.status === "done" ? false : 2000`
  - Returns typed `{ job_id, patient_id, status, result, error }`
- Modify `IntakeWizard.tsx`:
  - Add age/sex inputs to step 1 (above file upload)
  - StepSymptoms and StepVision write to Zustand instead of local state
  - **StepVision dispatch flow:** StepVision calls `onComplete` directly
    (bypassing `handleNext`), which propagates up to `Home.tsx`'s
    `handleIntakeComplete` -> `setView('processing')`. Do NOT dispatch
    the pipeline from IntakeWizard. Instead, dispatch it from
    `Processing.tsx` on mount (see below). IntakeWizard's only job is
    collecting data into Zustand.
- Modify `StepSymptoms.tsx`:
  - Read/write symptoms and chips from Zustand store
  - Add medications text input
- Modify `StepVision.tsx`:
  - Implement basic photo capture (file input with `accept="image/*"`)
  - Store captured files in Zustand via `setImages()`
  - Remove "Record Video" button (backend doesn't support it in pipeline mode)
- Modify `Processing.tsx`:
  - **On mount, dispatch the pipeline:** If no `jobId` exists in Zustand,
    call `usePipeline.mutateAsync()` to submit all intake data from the
    Zustand store. This is the single point where the pipeline is triggered.
    The flow is: StepVision `onComplete` -> Home `setView('processing')` ->
    Processing mounts -> dispatches pipeline -> stores `jobId` in Zustand.
    Guard against double-dispatch with a `useRef(dispatched)` flag.
  - If `jobId` already exists (page refresh during processing), resume
    polling without re-dispatching.
  - Replace hardcoded setTimeout steps with `useJobStatus` polling
  - Map backend events to 4-step progress UI via `eventToStepIndex()`
  - Call `onComplete()` when job status reaches `"done"`
  - Show error card when job status reaches `"error"`
- Modify `Home.tsx`:
  - Remove prop drilling for intake data, use Zustand throughout

### 5.4 Files created / modified

| File | Action |
|------|--------|
| `src/api/hooks/usePipeline.ts` | Create: pipeline dispatch mutation |
| `src/api/hooks/useJobStatus.ts` | Create: polling query hook |
| `src/app/components/intake/IntakeWizard.tsx` | Edit: add demographics, wire Zustand + pipeline |
| `src/app/components/intake/steps/StepSymptoms.tsx` | Edit: read/write Zustand, add medications |
| `src/app/components/intake/steps/StepVision.tsx` | Edit: implement capture, remove video button |
| `src/app/components/processing/Processing.tsx` | Edit: replace setTimeout with real polling + step mapping |
| `src/app/views/Home.tsx` | Edit: remove prop drilling, use Zustand |

### 5.5 Test suite

**File:** `tests/test_phase5_pipeline.py`

All tests use `httpx.AsyncClient(transport=ASGITransport(app=app))` running the
REAL FastAPI app. The pipeline dispatches a REAL background task.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_pipeline_requires_input` | `POST /pipeline/full` with no PDFs and empty symptom_text returns 400 | HTTP 400 |
| 2 | `test_pipeline_returns_job_id` | Valid request returns `job_id` and `status: "queued"` | HTTP 200, both fields present |
| 3 | `test_pipeline_creates_session` | Real session store has patient_id after dispatch | `get_session()` returns non-None |
| 4 | `test_pipeline_accepts_empty_symptom_text_with_pdfs` | POST with pdfs AND `symptom_text=""` (must be explicitly included -- omitting `symptom_text` entirely returns 422 because it has no default) | HTTP 200, not 422 |
| 5 | `test_pipeline_form_field_is_pdfs_not_files` | POST with field named `pdfs` | HTTP 200 |
| 6 | `test_pipeline_medications_parsed_as_csv` | POST with `medications="aspirin,ibuprofen"` | Session has medication list |
| 7 | `test_pipeline_omitting_symptom_text_returns_422` | POST with pdfs but NO `symptom_text` field at all | HTTP 422 (field is required, has no default) |
| 8 | `test_job_status_starts_queued` | `GET /jobs/{job_id}` immediately returns `"queued"` | `status == "queued"` |
| 9 | `test_job_status_transitions_to_terminal` | Poll real job until it reaches `"done"` or `"error"` (timeout 60s) | Status is terminal |
| 10 | `test_job_result_has_correct_keys` | When done, `result` has `lab_report`, `interview_result`, `research_result`, `router_output`, `translator_output` | All 5 keys present |
| 11 | `test_nonexistent_job_returns_404` | `GET /jobs/{random_uuid}` returns 404 | HTTP 404 |

**Frontend test file:** `src/__tests__/phase5_pipeline.test.ts`

All tests hit real backend. Skipped if backend not running.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `dispatch pipeline and get real job_id` | Mutation hits real endpoint, returns real job_id |
| 2 | `Zustand store has jobId after dispatch` | Patient store's `jobId` is set from real response |
| 3 | `poll real job until terminal status` | `useJobStatus` polls real endpoint, reaches done or error |
| 4 | `polling stops when status is done` | After done, no more requests |
| 5 | `polling stops when status is error` | After error, no more requests |
| 6 | `FormData uses field name pdfs not files` | Inspect FormData before sending |

### 5.6 Done gate

- Full intake flow works: Upload (with age/sex) -> Symptoms (with meds) -> Vision -> Processing
- Processing screen shows correct step labels based on real SSE events
- Error scenario works (submit bad data, see error card)
- `pytest tests/test_phase5_pipeline.py` -- all applicable tests green
- Frontend tests pass against real backend

---

## Phase 6: SSE Streaming (Real-Time Pipeline Progress)

**Goal:** Supplement job polling with real-time SSE events so the processing
screen updates instantly as each pipeline phase completes.

### 6.1 What to build

- Install `@microsoft/fetch-event-source`
- Create `src/api/hooks/usePipelineStream.ts`:
  - Connects to `GET /api/stream/{patient_id}` via `fetchEventSource`
  - Parses each SSE event and updates TanStack Query cache via
    `queryClient.setQueryData`
  - Handles BOTH event types (pipeline progress with `phase` field AND
    ThoughtStream events with `agent` field) using `eventToStepIndex()`
  - Aborts SSE connection on unmount or terminal event (`type === "done"` or
    `type === "error"`)
  - Pauses when browser tab is hidden (Page Visibility API)
- Modify `Processing.tsx`:
  - Use `usePipelineStream` alongside `useJobStatus` (SSE as primary, polling
    as fallback)
  - Update step labels from SSE `detail` (progress events) or `summary`
    (ThoughtStream events)
  - Show sub-label text under each step as events arrive

### 6.2 Files created / modified

| File | Action |
|------|--------|
| `package.json` | Edit: add `@microsoft/fetch-event-source` |
| `src/api/hooks/usePipelineStream.ts` | Create: SSE hook |
| `src/app/components/processing/Processing.tsx` | Edit: integrate SSE events |

### 6.3 Test suite

**File:** `tests/test_phase6_stream.py`

All tests use the REAL FastAPI app and REAL session store.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_stream_requires_session` | `GET /stream/{unknown_id}` returns 404 from real app | HTTP 404 |
| 2 | `test_stream_returns_event_source` | Create real session, `GET /stream/{id}` returns `text/event-stream` | Content-Type header correct |
| 3 | `test_stream_receives_pushed_events` | Push real events to real session via `push_event()`, read them back from SSE via `read_sse_events()` | Received events match pushed events exactly |
| 4 | `test_stream_terminates_on_done` | Push `{"type": "done"}` to real session, SSE stream closes | Connection terminates cleanly |
| 5 | `test_stream_terminates_on_error` | Push `{"type": "error"}` to real session, SSE stream closes | Connection terminates cleanly |
| 6 | `test_stream_event_format_progress` | Push `{"type": "progress", "phase": "extract", "detail": "..."}`, read from SSE | Parsed event has `phase` field |
| 7 | `test_stream_event_format_thought` | Push `{"agent": "extractor", "step": "...", "summary": "..."}`, read from SSE | Parsed event has `agent` field |

**Frontend test file:** `src/__tests__/phase6_stream.test.ts`

All tests connect to the real backend SSE endpoint. Skipped if backend not running.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `SSE connects to real /stream/{patientId}` | Connection opens without error |
| 2 | `SSE receives real progress events during pipeline` | Dispatch pipeline, confirm SSE delivers events |
| 3 | `SSE connection closes on done event` | After pipeline completes, EventSource is closed |
| 4 | `processing UI updates from real SSE detail text` | Step labels show real phase descriptions |

### 6.4 Done gate

- Processing screen updates in real time as each NLP phase emits events
- Steps show sub-labels from real `detail` and `summary` fields
- SSE connection closes cleanly when pipeline finishes
- Polling still works as fallback if SSE connection drops
- `pytest tests/test_phase6_stream.py` -- all 7 tests green
- Frontend tests pass against real backend

---

## Phase 7: Results Hydration + Clinician Lookup

**Goal:** Replace all hardcoded mock data in the results dashboard with real
pipeline output, and add a backend endpoint for the clinician portal to fetch
results by patient_id.

### 7.1 Clinician portal lookup endpoint

The frontend `ClinicianPortal.tsx` reads `patient_id` from `useParams()` and
needs to fetch the full pipeline results for that patient. Currently no backend
endpoint supports this. We add one:

```python
# backend/routers/results.py

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.session import get_session

router = APIRouter()


@router.get("/results/{patient_id}")
async def get_results(patient_id: str):
    """
    Fetch the full pipeline results for a patient.
    Used by the clinician portal and results dashboard.
    """
    session = get_session(patient_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    return {
        "patient_id": patient_id,
        "lab_report": session.lab_report.model_dump(mode="json") if session.lab_report else None,
        "interview_result": session.interview_result.model_dump(mode="json") if session.interview_result else None,
        "research_result": session.research_result.model_dump(mode="json") if session.research_result else None,
        "router_output": session.router_output.model_dump(mode="json") if session.router_output else None,
        "translator_output": session.translator_output.model_dump(mode="json") if session.translator_output else None,
    }
```

This endpoint is registered in `backend/main.py` alongside the other routers.
The route `/clinician/:id` already exists in `src/app/routes.tsx`.

### 7.2 Mapping real schemas to frontend UI

The frontend mock data has completely different shapes from the actual schemas.
Here is how each component maps to the real data:

**ResultsDashboard.tsx:**
- ArcGauge scores come from `router_output.disease_candidates[*].disease_alignment_score`
  (NOT `probability` -- that field doesn't exist)
- Condition names come from `router_output.disease_candidates[*].disease`
- Cluster type comes from `router_output.cluster` (enum: SYSTEMIC | GI | ENDOCRINE)
- CRP trend data comes from `lab_report.bio_fingerprint.CRP_Albumin` or
  individual `lab_report.markers` where `display_name` matches "CRP"
- Criteria checklist comes from `router_output.disease_candidates[*].criteria_met`

**SOAPNote.tsx:**
- SOAP content is `translator_output.soap_note` -- a SINGLE STRING (not 4
  separate sections). The frontend must parse the SOAP sections from this
  string, or display it as a single formatted block.
- Layman's explanation is `translator_output.layman_compass` -- also a SINGLE
  STRING (not an object with key_findings/recommended_actions)
- Faithfulness indicator: `translator_output.faithfulness_score`
- Reading level: `translator_output.fk_grade_level`

**ClinicianPortal.tsx:**
- Lab tables come from `lab_report.markers[*]` -- each MarkerTimeline has
  `display_name`, `values` (list of MarkerValue with value, unit, flag, date)
- Radar chart data comes from `router_output.disease_candidates` -- each has
  `disease`, `disease_alignment_score`, `criteria_met`, `criteria_count`
- SOAP sections from `translator_output.soap_note` (single string)

### 7.3 What to build

- Create `backend/routers/results.py` with `GET /results/{patient_id}` (above)
- Register the new router in `backend/main.py`
- Re-run `pnpm run gen:api` to pick up the new endpoint in TypeScript types
- Create `src/api/hooks/useResults.ts` -- a `useQuery` hook that:
  - Reads `patientId` from Zustand patient store (or from route param)
  - Fetches `GET /api/results/{patient_id}` via the typed client
  - Returns typed sub-objects matching the ACTUAL schema shapes
  - Uses `enabled: !!patientId && pipelineStatus === "done"` so it only fires
    when results are available
- Modify `ResultsDashboard.tsx`:
  - **Fix dual-context problem:** The component is used both as a child of
    `Home.tsx` (receives `onViewSOAP`, `onViewSpecialists`, `onViewCommunity`
    props) AND as a standalone route at `/dashboard` (receives NO props).
    Make all three callback props optional. When rendered standalone, manage
    modal state internally with local `useState` hooks and render the
    `SOAPNote`, `SpecialistMap`, and `Community` overlays inside the component
    itself (instead of relying on the parent).
  - Replace hardcoded mock scores with `router_output.disease_candidates`
  - Replace CRP chart with `lab_report.markers` / `lab_report.bio_fingerprint`
  - Show loading skeleton while results are fetching
  - Show error card if results are unavailable
- Modify `SOAPNote.tsx`:
  - Replace mock SOAP data with `translator_output.soap_note` (single string)
  - Replace mock layman's with `translator_output.layman_compass` (single string)
  - Show `faithfulness_score` and `fk_grade_level` indicators
  - **Fix hardcoded clinician link:** Footer currently links to `/clinician/A7B2`
    (hardcoded). Replace with dynamic `patientId` from Zustand:
    `href={"/clinician/" + patientId}`
- Modify `ClinicianPortal.tsx`:
  - Replace mock data with `useResults()` hook
  - Map `lab_report.markers` to lab table components
  - Map `router_output.disease_candidates` to radar chart
  - Show 404 state if patient not found

### 7.4 Files created / modified

| File | Action |
|------|--------|
| `backend/routers/results.py` | Create: GET /results/{patient_id} |
| `backend/main.py` | Edit: register results router |
| `src/api/schema.d.ts` | Regenerate: `pnpm run gen:api` |
| `src/api/hooks/useResults.ts` | Create: results query hook |
| `src/app/components/results/ResultsDashboard.tsx` | Edit: replace mock data with real schema |
| `src/app/components/results/SOAPNote.tsx` | Edit: replace mock SOAP with single-string format |
| `src/app/views/ClinicianPortal.tsx` | Edit: replace mock data with useResults |

### 7.5 Test suite

**File:** `tests/test_phase7_results.py`

All tests run against the REAL app and REAL session store.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_results_returns_404_for_unknown_patient` | `GET /results/{random_id}` returns 404 | HTTP 404 |
| 2 | `test_results_returns_null_fields_for_new_session` | Create session, `GET /results/{id}` returns all null fields | HTTP 200, all output fields null |
| 3 | `test_results_returns_lab_report_after_extract` | Run real extract, `GET /results/{id}` has non-null `lab_report` | `lab_report` has `markers` list |
| 4 | `test_lab_report_markers_structure` | `lab_report.markers[0]` has `display_name`, `values`, `trend` | Fields present with correct types |
| 5 | `test_router_output_has_disease_candidates` | `router_output.disease_candidates[0]` has `disease`, `disease_alignment_score`, `criteria_met` | Fields present |
| 6 | `test_translator_output_soap_is_string` | `translator_output.soap_note` is a string | `isinstance(str)` |
| 7 | `test_translator_output_layman_is_string` | `translator_output.layman_compass` is a string | `isinstance(str)` |

**Frontend test file:** `src/__tests__/phase7_results.test.ts`

All tests use real pipeline results from the real backend.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `useResults fetches real results by patientId` | After real pipeline completes, hook returns real data |
| 2 | `ResultsDashboard renders disease_alignment_score` | Gauge shows real numeric score from `disease_candidates` |
| 3 | `ResultsDashboard shows skeleton while loading` | Before results arrive, skeleton UI is visible |
| 4 | `SOAPNote renders single-string soap_note` | SOAP modal displays `translator_output.soap_note` |
| 5 | `ClinicianPortal loads results by patient_id from URL` | Navigate to `/clinician/{id}`, see real data |
| 6 | `ClinicianPortal shows 404 for unknown patient` | Navigate to `/clinician/nonexistent`, see not-found UI |
| 7 | `ResultsDashboard standalone route renders without props` | Navigate to `/dashboard` directly, component renders without crashing |
| 8 | `ResultsDashboard standalone SOAP button opens modal internally` | On `/dashboard`, click SOAP button, modal opens from internal state |

### 7.6 Done gate

- Full end-to-end flow works: Hero -> Intake -> Processing -> Results
- Results dashboard shows real `disease_alignment_score` values from NLP pipeline
- SOAP note modal shows real `soap_note` string from translator
- Clinician portal shows real patient data when accessed via `/clinician/:id`
- Clinician portal shows 404 for unknown patient IDs
- `pytest tests/test_phase7_results.py` -- all applicable tests green
- Frontend tests pass against real backend

---

## Phase 8: Error Boundaries + Resilience

**Goal:** Add error boundaries so failures at any point surface a recovery UI,
and consolidate remaining cross-component state.

### 8.1 What to build

- Expand `src/api/hooks/usePatientStore.ts` to include:
  - `wizardStep` (replaces `useState` in IntakeWizard)
  - Finalize `reset()` to clear all state for a new session
- Create `src/app/components/shared/ErrorBoundary.tsx`:
  - React error boundary that catches render errors
  - Shows a retry button and "Start over" option
  - Logs error context to `console.error` with component stack
- Create `src/api/hooks/useApiError.ts`:
  - Global TanStack Query error handler via `queryClient.setDefaultOptions`
  - Shows toast notifications (via `sonner`, already installed) on API errors
  - Distinguishes between network errors and HTTP errors
- Wrap major view boundaries in error boundaries:
  - `<IntakeWizard />`, `<Processing />`, `<ResultsDashboard />`

### 8.2 Files created / modified

| File | Action |
|------|--------|
| `src/api/hooks/usePatientStore.ts` | Edit: add wizardStep, finalize reset |
| `src/app/components/shared/ErrorBoundary.tsx` | Create: error boundary component |
| `src/api/hooks/useApiError.ts` | Create: global error handler |
| `src/app/App.tsx` | Edit: add global error handler setup |
| `src/app/views/Home.tsx` | Edit: wrap views in error boundaries |

### 8.3 Test suite

**File:** `tests/test_phase8_resilience.py`

All tests use the REAL app and REAL session store.

| # | Test name | What it verifies | Pass criteria |
|---|-----------|------------------|---------------|
| 1 | `test_session_eviction_after_ttl` | Create real session, set TTL to 1s, wait 2s, call `evict_stale_sessions()`, confirm gone | Session evicted |
| 2 | `test_concurrent_sessions_isolated` | Create two real sessions with different patient_ids, confirm data does not leak | Each session has only its own data |
| 3 | `test_session_store_empty_on_fresh_app` | Import fresh app, confirm `active_count() == 0` | Zero sessions |
| 4 | `test_malformed_request_returns_422` | `POST /extract` with missing required fields to real app | HTTP 422 with detail |
| 5 | `test_backend_startup_import_order` | Import `backend.main`, confirm app starts without error | No ImportError, no AttributeError |

**Frontend test file:** `src/__tests__/phase8_store.test.ts`

Tests hit real backend for error scenarios.

| # | Test name | What it verifies |
|---|-----------|------------------|
| 1 | `patient store reset clears all fields` | Call `reset()`, confirm every field is back to initial |
| 2 | `patient store persists across components` | Two components read same store instance |
| 3 | `error boundary catches render error` | Component that throws renders error UI |
| 4 | `error boundary shows retry and start-over buttons` | Both buttons present in error UI |
| 5 | `API 500 triggers toast notification` | Hit real backend with bad data, confirm toast appears |
| 6 | `network error shows distinct toast message` | Stop backend, trigger request, confirm toast says "network" |

### 8.4 Done gate

- Killing the backend mid-pipeline shows error card with retry option
- "Start over" button resets all state and returns to hero
- Multiple browser tabs have independent patient sessions
- `pytest tests/test_phase8_resilience.py` -- all 5 tests green
- Frontend tests pass
- Full flow tested: hero -> intake -> processing -> results -> start over -> repeat

---

## Out of Scope (deferred to future work)

The following frontend pages exist but are NOT wired to the backend in this plan:

### Vault (`src/app/views/Vault.tsx`)

The Vault page shows a document archive with local/cloud storage toggle. It
currently uses entirely mock data. Wiring it requires:
- A backend endpoint for document storage/retrieval (does not exist)
- Decision on storage backend (local filesystem vs. cloud object store)
- Upload/download API with authentication

This is deferred because no backend infrastructure exists for document
persistence beyond the in-memory session store.

### Community + Moderation (`src/app/components/community/Community.tsx`)

The Community page shows a mock forum. The `/moderate` endpoint exists and works
(stateless, no session needed), but there is no:
- Forum post CRUD API (create, read, update, delete posts)
- User authentication system
- Post listing/pagination endpoint
- Comment system

The moderation endpoint can be tested in isolation (Phase 0 confirms the
function is callable), but a full community feature requires significant new
backend work beyond middleware integration.

### Video capture (StepVision)

The `/pipeline/full` endpoint does not accept a `videos` field. Only the
standalone `/interview` endpoint does. If video support is needed in the
pipeline flow, the backend must be modified to accept videos in
`/pipeline/full`, or the frontend must make a separate `/interview` call.

---

## Testing Infrastructure

### Backend tests

All backend tests use `pytest` and follow the existing test structure in `tests/`.

```
tests/
  conftest.py                    -- created in Phase 0
  test_phase0_bootstrap.py
  test_phase1_proxy.py
  test_phase2_openapi.py
  test_phase3_query.py
  test_phase4_extract.py
  test_phase5_pipeline.py
  test_phase6_stream.py
  test_phase7_results.py
  test_phase8_resilience.py
  regressions/
    (bug-driven tests added during development -- see protocol above)
```

**Conventions (matching CLAUDE.md):**
- Each test file mirrors the structure of the feature it tests
- Never use bare `except: pass` -- all exceptions are logged
- Use `logging` module, not `print`
- Include context in error logs (endpoint, patient_id, operation)
- NO MOCKS on internal code -- tests hit real app, real sessions, real file I/O
- Tests that need a remote LLM (Azure OpenAI or vLLM) use `pytest.mark.skipif`
- Tests that need a live server (proxy tests) use `pytest.mark.skipif` with connectivity check

### Frontend tests

Frontend tests use Vitest (Vite-native) and hit the real backend.

```
src/__tests__/
  phase1_health.test.ts
  phase2_typed_client.test.ts
  phase3_useHealth.test.ts
  phase4_useExtract.test.ts
  phase5_pipeline.test.ts
  phase6_stream.test.ts
  phase7_results.test.ts
  phase8_store.test.ts
```

**Dependencies to install (Phase 1):**
- `vitest` (dev)
- `@testing-library/react` (dev)
- `@testing-library/jest-dom` (dev)
- `jsdom` (dev)

**Conventions:**
- Each test file mirrors the hook/component it tests
- NO MSW, NO mock service workers -- all API calls hit the real backend
- Tests are skipped if the backend is not running
- React hooks tested with `renderHook` from `@testing-library/react`
- Components tested with `render` + `screen` queries against real data

---

## Dependency Installation Order

Each phase installs only what it needs. No phase installs unused packages.

| Phase | pip install | pnpm add (runtime) | pnpm add --save-dev |
|-------|------------|----------------------|------------------------|
| 0 | `pip install -r backend/requirements.txt` | -- | -- |
| 1 | -- | -- | `vitest @testing-library/react @testing-library/jest-dom jsdom` |
| 2 | -- | `openapi-fetch` | `openapi-typescript` |
| 3 | -- | `@tanstack/react-query @tanstack/react-query-devtools zustand` | -- |
| 4 | -- | -- | -- |
| 5 | -- | -- | -- |
| 6 | -- | `@microsoft/fetch-event-source` | -- |
| 7 | -- | -- | -- |
| 8 | -- | -- | -- |

---

## Rollback Plan

Each phase is an atomic commit. If a phase introduces a regression:

1. `git revert <phase-commit>` to undo the phase
2. The previous phase's tests still pass (they are independent)
3. Fix the issue on a branch, re-run the failed phase's tests
4. Merge when green

No phase modifies another phase's test files. Tests are additive only.

---

## End-to-End Verification Checklist

After all 9 phases (0-8) are complete, run the full verification:

- [ ] `pytest tests/test_phase*.py -v` -- all backend tests green
- [ ] `pnpm test` -- all frontend tests green
- [ ] `npx tsc --noEmit` -- zero TypeScript errors
- [ ] Manual flow: Hero -> Upload PDF (with age/sex) -> Symptoms (with meds) -> Vision -> Processing (real SSE) -> Results (real data)
- [ ] Manual error flow: Stop backend during processing -> error card shown -> retry works
- [ ] Manual reset flow: "Start over" clears all state, returns to hero
- [ ] Network tab: no stale polling after job completes
- [ ] React Query DevTools: cache entries are correct and typed
- [ ] Bundle size check: `npx vite build && ls -la dist/assets/` -- JS bundle increase < 25 kB gzipped
- [ ] Clinician portal: navigate to `/clinician/{valid_id}` -> see real data
- [ ] Clinician portal: navigate to `/clinician/nonexistent` -> see 404 UI
- [ ] Results dashboard: `disease_alignment_score` values render (not `probability`)
- [ ] SOAP note: displays single-string `soap_note` (not sectioned list)
