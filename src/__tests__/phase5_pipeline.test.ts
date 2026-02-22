/**
 * Phase 5 frontend tests: usePipeline mutation + useJobStatus polling.
 *
 * All network calls are mocked via vi.mock so no live backend is required.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// ── Module mocks ──────────────────────────────────────────────────────────────

vi.mock("../api/client", () => ({
  apiClient: { GET: vi.fn() },
  postMultipart: vi.fn(),
}));

import { usePipeline, type PipelineDispatchResponse } from "../api/hooks/usePipeline";
import { useJobStatus, type JobStatusResponse } from "../api/hooks/useJobStatus";
import { usePatientStore } from "../api/hooks/usePatientStore";
import * as clientModule from "../api/client";

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

function freshQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

const DISPATCH_OK: PipelineDispatchResponse = {
  patient_id: "test-patient",
  job_id: "job-abc-123",
  status: "queued",
};

const JOB_RUNNING: JobStatusResponse = {
  job_id: "job-abc-123",
  patient_id: "test-patient",
  status: "running",
  result: null,
  error: null,
};

const JOB_DONE: JobStatusResponse = {
  job_id: "job-abc-123",
  patient_id: "test-patient",
  status: "done",
  result: { lab_report: null, interview_result: null, router_output: null, translator_output: null },
  error: null,
};

const JOB_ERROR: JobStatusResponse = {
  job_id: "job-abc-123",
  patient_id: "test-patient",
  status: "error",
  result: null,
  error: "LLM timed out",
};

// ── usePipeline ───────────────────────────────────────────────────────────────

describe("usePipeline", () => {
  beforeEach(() => {
    vi.mocked(clientModule.postMultipart).mockReset();
    act(() => usePatientStore.getState().reset());
  });

  it("mutateAsync resolves and stores job_id in Zustand", async () => {
    vi.mocked(clientModule.postMultipart).mockResolvedValue(DISPATCH_OK);

    const qc = freshQC();
    const { result } = renderHook(() => usePipeline(), { wrapper: makeWrapper(qc) });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(usePatientStore.getState().jobId).toBe("job-abc-123");
    expect(usePatientStore.getState().pipelineStatus).toBe("processing");
  });

  it("FormData uses field name 'pdfs' not 'files' for PDF uploads", async () => {
    vi.mocked(clientModule.postMultipart).mockResolvedValue(DISPATCH_OK);

    // Put a fake PDF in the store
    const fakePdf = new File(["pdf content"], "lab.pdf", { type: "application/pdf" });
    act(() => usePatientStore.getState().setPdfs([fakePdf]));

    const qc = freshQC();
    const { result } = renderHook(() => usePipeline(), { wrapper: makeWrapper(qc) });

    await act(async () => {
      await result.current.mutateAsync();
    });

    const [path, formData] = vi.mocked(clientModule.postMultipart).mock.calls[0] as [
      string,
      FormData,
    ];
    expect(path).toBe("/pipeline/full");
    expect(formData.getAll("pdfs")).toHaveLength(1);
    expect(formData.get("files")).toBeNull();
  });

  it("symptom_text is always sent (even when empty)", async () => {
    vi.mocked(clientModule.postMultipart).mockResolvedValue(DISPATCH_OK);

    act(() => usePatientStore.getState().setSymptoms(""));

    const qc = freshQC();
    const { result } = renderHook(() => usePipeline(), { wrapper: makeWrapper(qc) });

    await act(async () => {
      await result.current.mutateAsync();
    });

    const [, formData] = vi.mocked(clientModule.postMultipart).mock.calls[0] as [
      string,
      FormData,
    ];
    // symptom_text must be present (even as empty string)
    expect(formData.has("symptom_text")).toBe(true);
  });
});

// ── useJobStatus ──────────────────────────────────────────────────────────────

describe("useJobStatus", () => {
  beforeEach(() => {
    vi.mocked(clientModule.apiClient.GET).mockReset();
  });

  it("returns job data when jobId is provided", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: JOB_RUNNING,
      error: undefined,
    } as any);

    const qc = freshQC();
    const { result } = renderHook(() => useJobStatus("job-abc-123"), {
      wrapper: makeWrapper(qc),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("running");
  });

  it("polling stops when status is done", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: JOB_DONE,
      error: undefined,
    } as any);

    const qc = freshQC();
    const { result } = renderHook(() => useJobStatus("job-abc-123"), {
      wrapper: makeWrapper(qc),
    });

    await waitFor(() => expect(result.current.data?.status).toBe("done"));

    const callCount = vi.mocked(clientModule.apiClient.GET).mock.calls.length;
    // Wait to confirm no additional polling
    await new Promise((r) => setTimeout(r, 50));
    expect(vi.mocked(clientModule.apiClient.GET).mock.calls.length).toBe(callCount);
  });

  it("polling stops when status is error", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: JOB_ERROR,
      error: undefined,
    } as any);

    const qc = freshQC();
    const { result } = renderHook(() => useJobStatus("job-abc-123"), {
      wrapper: makeWrapper(qc),
    });

    await waitFor(() => expect(result.current.data?.status).toBe("error"));
    expect(result.current.data?.error).toBe("LLM timed out");
  });

  it("is disabled when jobId is null", () => {
    const qc = freshQC();
    const { result } = renderHook(() => useJobStatus(null), {
      wrapper: makeWrapper(qc),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(vi.mocked(clientModule.apiClient.GET)).not.toHaveBeenCalled();
  });
});
