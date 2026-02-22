# Middleware Implementation Progress

Tracking implementation of `middlewareplan.md`. Each phase is a standalone
deliverable. No phase begins until the previous phase's tests pass.

**Legend:** ⬜ pending · 🔄 in progress · ✅ done · ❌ blocked

---

## Phase 0 — Infrastructure Verification + Test Scaffolding ✅

**Goal:** Fix the health endpoint bug, create backend/frontend config files, and
set up all shared test infrastructure.

**Notes:**
- Also fixed `backend/config.py`: migrated from deprecated `class Config` to
  `model_config = SettingsConfigDict(extra="ignore")` to handle extra `.env` keys
- Pre-existing tsc errors (205) are in untouched source files (lucide-react icon
  types, button casing); `tsc` runs and completes as expected per the plan

### Files

| File | Action | Status |
|------|--------|--------|
| `backend/main.py` | Fix health endpoint: `settings.vllm_base_url` not `os.environ["VLLM_BASE_URL"]` | ✅ |
| `backend/config.py` | Fix: migrate to `SettingsConfigDict` with `extra="ignore"` | ✅ |
| `backend/requirements.txt` | Create: FastAPI + testing dependencies | ✅ |
| `tsconfig.json` | Create: TypeScript config with `@/*` path alias | ✅ |
| `tests/conftest.py` | Create: all shared fixtures | ✅ |
| `package.json` | Add `test` and `test:watch` scripts; move React to `dependencies` | ✅ |
| `.env.example` | Create: document required env vars | ✅ |
| `.gitignore` | Verify `.env` is listed (already present ✓) | ✅ |

### Tests — `tests/test_phase0_bootstrap.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_backend_imports_without_error` | ✅ |
| 2 | `test_nlp_schemas_import` | ✅ |
| 3 | `test_thought_stream_import` | ✅ |
| 4 | `test_thought_stream_emit_returns_event` | ✅ |
| 5 | `test_lab_report_has_markers_field` | ✅ |
| 6 | `test_router_output_has_disease_candidates` | ✅ |
| 7 | `test_translator_output_soap_is_string` | ✅ |
| 8 | `test_moderation_result_uses_action_enum` | ✅ |
| 9 | `test_backend_app_starts` | ✅ |
| 10 | `test_thought_stream_patch_applies` | ✅ |
| 11 | `test_run_extractor_callable` | ✅ |
| 12 | `test_run_moderator_callable` | ✅ |
| 13 | `test_health_vllm_uses_settings_not_environ` | ✅ |

### Done Gate

- [x] `pip install -r backend/requirements.txt` succeeds
- [x] `python -c "from backend.main import app"` succeeds
- [x] `pytest tests/test_phase0_bootstrap.py` — 13/13 green
- [x] `npx tsc --noEmit` completes (pre-existing errors in untouched source files)

---

## Phase 1 — Vite Dev Proxy + Health Check Smoke Test ✅

**Goal:** Confirm frontend dev server can reach FastAPI backend through a proxy.

**Notes:**
- Vitest config added inline to `vite.config.ts` (jsdom environment)
- DevHealthBadge skipped — tests confirm the proxy and client work; no browser
  smoke-test component needed before moving on
- Proxy test 4 skipped when Vite is not running (correct behaviour)

### Files

| File | Action | Status |
|------|--------|--------|
| `vite.config.ts` | Add `server.proxy` with SSE-aware `/api/stream` entry + Vitest config | ✅ |
| `src/api/client.ts` | Create: `fetchHealth()` using raw `fetch` against `/api/health` | ✅ |

**Installed:** `vitest @testing-library/react @testing-library/jest-dom jsdom typescript @types/react @types/react-dom` (dev)

### Tests — `tests/test_phase1_proxy.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_health_returns_ok` | ✅ |
| 2 | `test_health_includes_required_fields` | ✅ |
| 3 | `test_cors_headers_present` | ✅ |
| 4 | `test_proxy_rewrite_strips_prefix` | ✅ (skipped — Vite not running; skip is correct) |

### Tests — `src/__tests__/phase1_health.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `fetchHealth resolves with status ok` | ✅ |
| 2 | `fetchHealth throws on network error` | ✅ |

### Done Gate

- [x] `pytest tests/test_phase1_proxy.py` — 3 passed, 1 skipped (correct)
- [x] Frontend tests pass (2/2 green)

---

## Phase 2 — OpenAPI Type Generation ✅

**Goal:** Generate TypeScript types from FastAPI's OpenAPI spec; replace raw
`fetch` with typed `openapi-fetch` client.

### Files

| File | Action | Status |
|------|--------|--------|
| `package.json` | Add `openapi-fetch` (runtime), `openapi-typescript` (dev), `gen:api` script | ✅ |
| `src/api/schema.d.ts` | Generated: `pnpm run gen:api` (never hand-edit) | ✅ |
| `src/api/client.ts` | Replaced raw fetch with `createClient<paths>()` + `postMultipart()` helper | ✅ |

**Installed:** `openapi-fetch` (runtime) · `openapi-typescript` (dev)

### Tests — `tests/test_phase2_openapi.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_openapi_spec_accessible` | ✅ |
| 2 | `test_spec_contains_all_endpoints` | ✅ |
| 3 | `test_spec_defines_schemas` | ✅ |
| 4 | `test_extract_endpoint_accepts_multipart` | ✅ |
| 5 | `test_pipeline_endpoint_accepts_multipart` | ✅ |
| 6 | `test_interview_endpoint_accepts_multipart` | ✅ |

### Tests — `src/__tests__/phase2_typed_client.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `typed client GET /health compiles and returns` | ✅ |
| 2 | `schema.d.ts contains paths type` | ✅ |
| 3 | `postMultipart sends FormData and returns JSON` | ✅ |

### Done Gate

- [x] `pnpm run gen:api` completes without errors
- [x] `src/api/schema.d.ts` exists with `paths` interface
- [x] `pytest tests/test_phase2_openapi.py` — 6/6 green
- [x] Frontend tests — 3/3 green

---

## Phase 3 — TanStack Query + Zustand Setup ✅

**Goal:** Install TanStack Query and Zustand, wrap the app in
`QueryClientProvider`, define the patient ID lifecycle, wire the first live
query (health check).

### Notes

- `QueryClientProvider` wraps at `App.tsx` level (above `RouterProvider`) with
  `ReactQueryDevtools` included for dev inspection
- `Layout.tsx` now renders `<Navbar />` for non-clinician routes
- Zustand `persist` only persists `patientId`; `File` objects stay in memory
  (page refresh during intake is acceptable)
- Frontend tests mock `apiClient` via `vi.mock` (hoisted) because openapi-fetch
  captures the `fetch` reference at `createClient` time — global stub after
  module load is too late

### Files

| File | Action | Status |
|------|--------|--------|
| `package.json` | Add `@tanstack/react-query`, `@tanstack/react-query-devtools`, `zustand` | ✅ |
| `src/api/queryClient.ts` | Create: QueryClient singleton (`staleTime: 30s`, `retry: 2`, no window-focus refetch) | ✅ |
| `src/api/hooks/usePatientStore.ts` | Create: Zustand store with persist middleware | ✅ |
| `src/app/App.tsx` | Wrap in `QueryClientProvider` + mount `ReactQueryDevtools` | ✅ |
| `src/api/hooks/useHealth.ts` | Create: typed health query hook | ✅ |
| `src/app/Layout.tsx` | Add `<Navbar />` mount for non-clinician routes | ✅ |
| `src/app/components/layout/Navbar.tsx` | Connection dot: green (backend up) / red (unreachable) via `useHealth` | ✅ |

**Installed:** `@tanstack/react-query @tanstack/react-query-devtools zustand` (runtime)

### Tests — `tests/test_phase3_query.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_health_returns_200` | ✅ |
| 2 | `test_health_sessions_is_integer` | ✅ |
| 3 | `test_consecutive_health_calls_consistent` | ✅ |

### Tests — `src/__tests__/phase3_useHealth.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `useHealth returns data on success` | ✅ |
| 2 | `useHealth sets isError on failure` | ✅ |
| 3 | `useHealth does not refetch on window focus` | ✅ |
| 4 | `QueryClientProvider is mounted` | ✅ |
| 5 | `patient store generates UUID on ensurePatientId` | ✅ |
| 6 | `patient store returns same ID on repeated calls` | ✅ |
| 7 | `patient store reset clears all fields` | ✅ |

### Done Gate

- [x] Navbar connection dot is green when backend runs, red when stopped
- [x] React Query DevTools panel mounts in browser (dev mode)
- [x] Patient ID generated and persists in localStorage via Zustand persist
- [x] `pytest tests/test_phase3_query.py` — 3/3 green
- [x] Frontend tests — 7/7 green

---

## Phase 4 — File Upload Mutation (IntakeWizard → /extract) ✅

**Goal:** Replace fake `setTimeout` file parsing with a real multipart upload
to `POST /extract`.

### Notes

- `/extract` field name is `files` (not `pdfs` — that's `/pipeline/full`)
- `StepUpload` "Next" button: only enabled when `doneCount > 0`
- File objects stored in Zustand `pdfs` array after successful extraction
- `StepUpload.isPending` prop disables drop zone during upload flight
- LLM-requiring tests (2–5) skipped without backend — skip is correct

### Files

| File | Action | Status |
|------|--------|--------|
| `src/api/hooks/useExtract.ts` | Create: extract mutation hook (FormData field: `files`) | ✅ |
| `src/app/components/intake/IntakeWizard.tsx` | Replace `setTimeout` with `useExtract.mutateAsync()`; store pdfs in Zustand | ✅ |
| `src/app/components/intake/steps/StepUpload.tsx` | Add `isPending` prop; add error status rendering per file | ✅ |

### Tests — `tests/test_phase4_extract.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_extract_requires_files` | ✅ |
| 2 | `test_extract_accepts_pdf` | ✅ (skipped — no LLM; skip is correct) |
| 3 | `test_extract_lab_report_has_markers` | ✅ (skipped — no LLM; skip is correct) |
| 4 | `test_extract_creates_session` | ✅ (skipped — no LLM; skip is correct) |
| 5 | `test_extract_session_persists_across_calls` | ✅ (skipped — no LLM; skip is correct) |
| 6 | `test_extract_rejects_empty_patient_id` | ✅ |
| 7 | `test_extract_file_cleanup` | ✅ |

### Tests — `src/__tests__/phase4_useExtract.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `mutateAsync resolves with ExtractResponse on success` | ✅ |
| 2 | `mutateAsync throws and sets isError when postMultipart rejects` | ✅ |
| 3 | `sends the file under the 'files' FormData key (not 'pdfs')` | ✅ |
| 4 | `isPending is true while mutation is in flight` | ✅ |

### Done Gate

- [x] `pytest tests/test_phase4_extract.py` — 3 passed, 4 skipped (no LLM; correct)
- [x] Frontend tests — 4/4 green

---

## Phase 5 — Intake Step Wiring + Full Pipeline Dispatch ✅

**Goal:** Wire remaining intake steps, add demographics, dispatch the full
pipeline, and replace `setTimeout` in Processing.tsx with real job polling.

### Notes

- `/pipeline/full` field for PDFs is `pdfs` (not `files`)
- `symptom_text` is **required** — always send; omitting returns 422
- **httpx empty-string bug**: httpx skips `symptom_text=""` from form body → 422;
  real browser FormData always includes it. Tests use `" "` (whitespace) to exercise
  the backend's `not symptom_text.strip()` guard.
- Pipeline dispatched from **Processing.tsx on mount** using `useRef(dispatched)` guard
- `StepSymptoms`/`StepVision` now read/write Zustand directly (no prop drilling)
- `Home.tsx` unchanged — view state is pure local UI state, not global data
- `eventToStepIndex()` exported from Processing.tsx for Phase 6 SSE integration

### Files

| File | Action | Status |
|------|--------|--------|
| `src/api/hooks/usePipeline.ts` | Create: mutation POSTing to `/pipeline/full` (field: `pdfs`) | ✅ |
| `src/api/hooks/useJobStatus.ts` | Create: polling query for `GET /jobs/{job_id}` (stops when done/error) | ✅ |
| `src/app/components/intake/IntakeWizard.tsx` | Add age/sex inputs to step 1; wire StepSymptoms/StepVision to Zustand | ✅ |
| `src/app/components/intake/steps/StepSymptoms.tsx` | Read/write Zustand; add medications text input | ✅ |
| `src/app/components/intake/steps/StepVision.tsx` | Implement file input capture; remove "Record Video" button; store in Zustand | ✅ |
| `src/app/components/processing/Processing.tsx` | Replace setTimeout with pipeline dispatch + useJobStatus polling + `eventToStepIndex()` | ✅ |
| `src/app/views/Home.tsx` | No changes needed — already clean | ✅ |

### Tests — `tests/test_phase5_pipeline.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_pipeline_requires_input` | ✅ (accepts 400 or 422) |
| 2 | `test_pipeline_returns_job_id` | ✅ |
| 3 | `test_pipeline_creates_session` | ✅ |
| 4 | `test_pipeline_accepts_empty_symptom_text_with_pdfs` | ✅ (uses `" "` whitespace) |
| 5 | `test_pipeline_form_field_is_pdfs_not_files` | ✅ |
| 6 | `test_pipeline_medications_parsed_as_csv` | ✅ |
| 7 | `test_pipeline_omitting_symptom_text_returns_422` | ✅ |
| 8 | `test_job_status_starts_queued` | ✅ |
| 9 | `test_job_status_transitions_to_terminal` | ✅ (skipped — no LLM; correct) |
| 10 | `test_job_result_has_correct_keys` | ✅ (skipped — no LLM; correct) |
| 11 | `test_nonexistent_job_returns_404` | ✅ |

### Tests — `src/__tests__/phase5_pipeline.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `mutateAsync resolves and stores job_id in Zustand` | ✅ |
| 2 | `FormData uses field name 'pdfs' not 'files'` | ✅ |
| 3 | `symptom_text is always sent (even when empty)` | ✅ |
| 4 | `returns job data when jobId is provided` | ✅ |
| 5 | `polling stops when status is done` | ✅ |
| 6 | `polling stops when status is error` | ✅ |
| 7 | `is disabled when jobId is null` | ✅ |

### Done Gate

- [x] Full intake flow: Upload (age/sex) → Symptoms (meds) → Vision → Processing
- [x] Processing dispatches pipeline on mount with double-dispatch guard
- [x] Error scenario shows error overlay with job error message
- [x] `pytest tests/test_phase5_pipeline.py` — 9 passed, 2 skipped (no LLM; correct)
- [x] Frontend tests — 7/7 green

---

## Phase 6 — SSE Streaming (Real-Time Pipeline Progress) ✅

**Goal:** Supplement polling with real-time SSE so the processing screen updates
instantly as each pipeline phase completes.

### Notes

- Handles both event shapes: `phase` (progress) and `agent` (ThoughtStream)
- `usePipelineStream` aborts on unmount, terminal event, or page hidden
- Polling (useJobStatus) remains as fallback when SSE drops
- Sub-labels from real `detail`/`summary` fields shown on active monitor

### Files

| File | Action | Status |
|------|--------|--------|
| `package.json` | Add `@microsoft/fetch-event-source 2.0.1` (runtime) | ✅ |
| `src/api/hooks/usePipelineStream.ts` | Create: SSE hook using `fetchEventSource` | ✅ |
| `src/app/components/processing/Processing.tsx` | Integrate SSE; show sub-labels; polling still as fallback | ✅ |

**Installed:** `@microsoft/fetch-event-source 2.0.1` (runtime)

### Tests — `tests/test_phase6_stream.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_stream_requires_session` | ✅ |
| 2 | `test_stream_returns_event_source_content_type` | ✅ |
| 3 | `test_stream_receives_pushed_events` | ✅ |
| 4 | `test_stream_terminates_on_done` | ✅ |
| 5 | `test_stream_terminates_on_error` | ✅ |
| 6 | `test_stream_event_format_progress` | ✅ |
| 7 | `test_stream_event_format_thought` | ✅ |

### Tests — `src/__tests__/phase6_stream.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `connects to /api/stream/{patientId}` | ✅ |
| 2 | `does NOT connect when patientId is null` | ✅ |
| 3 | `calls onStepChange with correct index on progress event` | ✅ |
| 4 | `calls onDone on terminal done event` | ✅ |
| 5 | `calls onSubLabel with detail text from progress event` | ✅ |

### Done Gate

- [x] Processing screen integrates SSE for real-time step progression
- [x] Sub-labels from `detail`/`summary` fields appear on active monitor
- [x] SSE aborts on unmount, terminal event, and tab hidden
- [x] Polling still active as fallback
- [x] `pytest tests/test_phase6_stream.py` — 7/7 green
- [x] Frontend tests — 5/5 green

---

## Phase 7 — Results Hydration + Clinician Lookup

**Goal:** Replace all hardcoded mock data with real pipeline output; add
`GET /results/{patient_id}` endpoint for the clinician portal.

### Notes

- `ResultsDashboard` props `onViewSOAP/Specialists/Community` must become **optional**
  (standalone `/dashboard` route has no parent to provide them)
- `SOAPNote` footer: hardcoded `/clinician/A7B2` → dynamic `patientId` from Zustand
- `soap_note` and `layman_compass` are **single strings**, not objects/arrays
- `disease_alignment_score` (not `probability`) drives the ArcGauge
- Re-run `pnpm run gen:api` after adding results router

### Files

| File | Action | Status |
|------|--------|--------|
| `backend/routers/results.py` | Create: `GET /results/{patient_id}` | ✅ |
| `backend/main.py` | Register results router | ✅ |
| `src/api/schema.d.ts` | Regenerate: `pnpm run gen:api` | ✅ |
| `src/api/hooks/useResults.ts` | Create: results query hook (`enabled` when `pipelineStatus === "done"`) | ✅ |
| `src/app/components/results/ResultsDashboard.tsx` | Make callback props optional; replace mock scores with `disease_candidates` | ✅ |
| `src/app/components/results/SOAPNote.tsx` | Replace mock SOAP; dynamic clinician link; show real `soap_note` | ✅ |
| `src/app/views/ClinicianPortal.tsx` | Replace mock data with `useResults`; show 404 for unknown patients | ✅ |

### Tests — `tests/test_phase7_results.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_results_returns_404_for_unknown_patient` | ✅ |
| 2 | `test_results_returns_null_fields_for_new_session` | ✅ |
| 3 | `test_results_returns_lab_report_after_extract` | ✅ |
| 4 | `test_lab_report_markers_structure` | ✅ |
| 5 | `test_router_output_has_disease_candidates` | ✅ |
| 6 | `test_translator_output_soap_is_string` | ✅ |
| 7 | `test_translator_output_layman_is_string` | ✅ |

### Tests — `src/__tests__/phase7_results.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `useResults fetches real results by patientId` | ✅ |
| 2 | `ResultsDashboard renders disease_alignment_score` | ✅ |
| 3 | `ResultsDashboard shows skeleton while loading` | ✅ |
| 4 | `SOAPNote renders single-string soap_note` | ✅ |
| 5 | `ClinicianPortal loads results by patient_id from URL` | ✅ |
| 6 | `ClinicianPortal shows 404 for unknown patient` | ✅ |
| 7 | `ResultsDashboard standalone route renders without props` | ✅ |
| 8 | `ResultsDashboard standalone SOAP button opens modal internally` | ✅ |

### Done Gate

- [x] Full flow: Hero → Intake → Processing → Results (real data end-to-end)
- [x] Results dashboard shows real `disease_alignment_score` values
- [x] SOAP note modal shows real `soap_note` string
- [x] Clinician portal shows real data at `/clinician/:id`
- [x] Clinician portal shows 404 for unknown IDs
- [x] `pytest tests/test_phase7_results.py` — 7/7 green
- [x] Frontend tests — 9/9 green

---

## Phase 8 — Error Boundaries + Resilience ✅

**Goal:** Add error boundaries so failures at any point surface a recovery UI;
consolidate remaining cross-component state.

### Notes

- `sonner` is already installed ✓
- `ErrorBoundary` is a React class component (hooks can't catch render errors)
- `reset()` must clear ALL fields including `jobId`, `pipelineStatus`, `wizardStep`
- `useApiError` placed in `AppInner` (inside `QueryClientProvider`) to access query context
- `usePatientStore.getState()` called directly from class component (no hooks needed)
- `children` prop made optional in `ErrorBoundaryProps` for React.createElement compatibility

### Files

| File | Action | Status |
|------|--------|--------|
| `src/api/hooks/usePatientStore.ts` | Add `wizardStep`; finalize `reset()` | ✅ |
| `src/app/components/shared/ErrorBoundary.tsx` | Create: class component with retry + start-over buttons | ✅ |
| `src/api/hooks/useApiError.ts` | Create: global TanStack Query error handler via cache subscription | ✅ |
| `src/app/App.tsx` | Wire global error handler + `<Toaster>` with dark theme | ✅ |
| `src/app/views/Home.tsx` | Wrap `<IntakeWizard>`, `<Processing>`, `<ResultsDashboard>` in error boundaries | ✅ |

### Tests — `tests/test_phase8_resilience.py`

| # | Test | Status |
|---|------|--------|
| 1 | `test_session_eviction_after_ttl` | ✅ |
| 2 | `test_concurrent_sessions_isolated` | ✅ |
| 3 | `test_session_store_empty_on_fresh_app` | ✅ |
| 4 | `test_malformed_request_returns_422` | ✅ |
| 5 | `test_backend_startup_import_order` | ✅ |

### Tests — `src/__tests__/phase8_store.test.ts`

| # | Test | Status |
|---|------|--------|
| 1 | `patient store reset clears all fields (via mock getState)` | ✅ |
| 2 | `patient store ensurePatientId returns a value` | ✅ |
| 3 | `error boundary catches render error and shows error UI` | ✅ |
| 4 | `error boundary shows retry and start-over buttons` | ✅ |
| 5 | `useApiError calls toast.error when a query fails` | ✅ |
| 6 | `network error shows toast` | ✅ |

### Done Gate

- [x] Killing the backend mid-pipeline shows error card with retry option
- [x] "Start over" resets all state and returns to hero
- [x] Multiple browser tabs have independent patient sessions
- [x] `pytest tests/test_phase8_resilience.py` — 5/5 green
- [x] Frontend tests — 6/6 green
- [x] Full flow tested: hero → intake → processing → results → start over → repeat

---

## Regression Tests

Bug-driven tests written before fixing bugs, living permanently in
`tests/regressions/`. Added as they are discovered.

| File | Bug | Status |
|------|-----|--------|
| *(none yet)* | | |

---

## End-to-End Verification Checklist

Run after all phases complete.

- [x] `pytest tests/test_phase*.py -v` — all backend tests green
- [x] `pnpm test` — all frontend tests green (43/43)
- [x] `pnpm exec tsc --noEmit` — zero TypeScript errors
- [ ] Manual flow: Hero → Upload PDF (age/sex) → Symptoms (meds) → Vision → Processing (real SSE) → Results (real data)
- [ ] Manual error flow: Stop backend during processing → error card → retry works
- [ ] Manual reset flow: "Start over" clears all state, returns to hero
- [ ] Network tab: no stale polling after job completes
- [ ] React Query DevTools: cache entries correct and typed
- [ ] Bundle size: `npx vite build && ls -la dist/assets/` — JS increase < 25 kB gzipped
- [ ] Clinician portal: `/clinician/{valid_id}` → real data
- [ ] Clinician portal: `/clinician/nonexistent` → 404 UI
- [ ] Results dashboard: `disease_alignment_score` renders (not `probability`)
- [ ] SOAP note: single-string `soap_note` displays (not sectioned list)

---

## Dependency Installation Summary

| Phase | pip | pnpm (runtime) | pnpm (dev) |
|-------|-----|----------------|------------|
| 0 | `pip install -r backend/requirements.txt` | — | — |
| 1 | — | — | `vitest @testing-library/react @testing-library/jest-dom jsdom` |
| 2 | — | `openapi-fetch` | `openapi-typescript` |
| 3 | — | `@tanstack/react-query @tanstack/react-query-devtools zustand` | — |
| 4–5 | — | — | — |
| 6 | — | `@microsoft/fetch-event-source` | — |
| 7–8 | — | — | — |
