/**
 * Phase 4 frontend tests: useExtract mutation hook.
 *
 * All tests mock `postMultipart` via vi.mock so no live backend is required.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// ── Hoist module mock before any imports ──────────────────────────────────────

vi.mock("../api/client", () => ({
  apiClient: { GET: vi.fn() },
  postMultipart: vi.fn(),
}));

import { useExtract, type ExtractResponse } from "../api/hooks/useExtract";
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

const EXTRACT_OK: ExtractResponse = {
  patient_id: "test-patient",
  lab_report: {
    patient_id: "test-patient",
    patient_age: 40,
    patient_sex: "F",
    markers: [],
  },
};

function makeFile(name = "lab.pdf", content = "PDF content"): File {
  return new File([content], name, { type: "application/pdf" });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("useExtract", () => {
  beforeEach(() => {
    vi.mocked(clientModule.postMultipart).mockReset();
    act(() => usePatientStore.getState().reset());
  });

  it("mutateAsync resolves with ExtractResponse on success", async () => {
    vi.mocked(clientModule.postMultipart).mockResolvedValue(EXTRACT_OK);

    const qc = freshQC();
    const { result } = renderHook(() => useExtract(), { wrapper: makeWrapper(qc) });

    let data: ExtractResponse | undefined;
    await act(async () => {
      data = await result.current.mutateAsync([makeFile()]);
    });

    expect(data?.patient_id).toBe("test-patient");
    expect(data?.lab_report.markers).toBeInstanceOf(Array);
  });

  it("mutateAsync throws and sets isError when postMultipart rejects", async () => {
    vi.mocked(clientModule.postMultipart).mockRejectedValue(new Error("500: Extractor failed"));

    const qc = freshQC();
    const { result } = renderHook(() => useExtract(), { wrapper: makeWrapper(qc) });

    await act(async () => {
      try {
        await result.current.mutateAsync([makeFile()]);
      } catch {
        // expected
      }
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toContain("Extractor failed");
  });

  it("sends the file under the 'files' FormData key (not 'pdfs')", async () => {
    vi.mocked(clientModule.postMultipart).mockResolvedValue(EXTRACT_OK);

    const qc = freshQC();
    const { result } = renderHook(() => useExtract(), { wrapper: makeWrapper(qc) });
    const file = makeFile("report.pdf");

    await act(async () => {
      await result.current.mutateAsync([file]);
    });

    const [path, formData] = vi.mocked(clientModule.postMultipart).mock.calls[0] as [
      string,
      FormData,
    ];
    expect(path).toBe("/extract");
    const sentFiles = formData.getAll("files");
    expect(sentFiles).toHaveLength(1);
    expect((sentFiles[0] as File).name).toBe("report.pdf");
    // Must NOT use 'pdfs' key
    expect(formData.get("pdfs")).toBeNull();
  });

  it("isPending is true while mutation is in flight", async () => {
    let resolveUpload!: (v: ExtractResponse) => void;
    vi.mocked(clientModule.postMultipart).mockReturnValue(
      new Promise<ExtractResponse>((r) => {
        resolveUpload = r;
      }),
    );

    const qc = freshQC();
    const { result } = renderHook(() => useExtract(), { wrapper: makeWrapper(qc) });

    act(() => {
      result.current.mutate([makeFile()]);
    });

    await waitFor(() => expect(result.current.isPending).toBe(true));

    // Clean up: resolve the hanging promise
    act(() => resolveUpload(EXTRACT_OK));
    await waitFor(() => expect(result.current.isPending).toBe(false));
  });
});
