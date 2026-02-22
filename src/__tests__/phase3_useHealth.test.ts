/**
 * Phase 3 frontend tests: TanStack Query + Zustand patient store.
 *
 * Tests the hooks in isolation using a real QueryClient and vitest module mocks.
 * No MSW, no external backend required.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import React from "react";

// ── Module mock: intercept apiClient before any hook imports ──────────────────
// vi.mock is hoisted by vitest, so it runs before the static imports below.

vi.mock("../api/client", () => ({
  apiClient: {
    GET: vi.fn(),
  },
  postMultipart: vi.fn(),
}));

// Static imports — resolved AFTER vi.mock has been applied.
import { useHealth } from "../api/hooks/useHealth";
import { usePatientStore } from "../api/hooks/usePatientStore";
import { queryClient as singletonQC } from "../api/queryClient";
import * as clientModule from "../api/client";

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

function freshQC() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,         // surface errors immediately in tests
        staleTime: 0,
        refetchOnWindowFocus: false,
      },
    },
  });
}

const HEALTH_OK = {
  status: "ok",
  databricks: false,
  vllm: false,
  sessions_active: 0,
} as const;

// ── useHealth ─────────────────────────────────────────────────────────────────

describe("useHealth", () => {
  beforeEach(() => {
    vi.mocked(clientModule.apiClient.GET).mockReset();
  });

  it("returns data on success", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: HEALTH_OK,
      error: undefined,
    } as any);

    const qc = freshQC();
    const { result } = renderHook(() => useHealth(), { wrapper: makeWrapper(qc) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("ok");
  });

  it("sets isError on failure (error present)", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: undefined,
      error: { message: "Backend down" },
    } as any);

    const qc = freshQC();
    const { result } = renderHook(() => useHealth(), { wrapper: makeWrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("does not refetch on window focus (singleton QueryClient)", () => {
    const defaults = singletonQC.getDefaultOptions();
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });
});

// ── QueryClientProvider mounted ───────────────────────────────────────────────

describe("QueryClientProvider", () => {
  it("is present: useQueryClient resolves without throwing", () => {
    const qc = freshQC();
    const { result } = renderHook(() => useQueryClient(), {
      wrapper: makeWrapper(qc),
    });
    expect(result.current).toBe(qc);
  });
});

// ── usePatientStore ───────────────────────────────────────────────────────────

describe("usePatientStore", () => {
  beforeEach(() => {
    act(() => usePatientStore.getState().reset());
  });

  it("generates a UUID on ensurePatientId", () => {
    const id = usePatientStore.getState().ensurePatientId();
    expect(typeof id).toBe("string");
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    );
  });

  it("returns the same ID on repeated calls (idempotent)", () => {
    const id1 = usePatientStore.getState().ensurePatientId();
    const id2 = usePatientStore.getState().ensurePatientId();
    expect(id1).toBe(id2);
  });

  it("reset clears all fields and nullifies patientId", () => {
    const store = usePatientStore.getState();

    store.ensurePatientId();
    store.setSymptoms("fatigue");
    store.setWizardStep(3);

    act(() => store.reset());

    const after = usePatientStore.getState();
    expect(after.patientId).toBeNull();
    expect(after.symptoms).toBe("");
    expect(after.wizardStep).toBe(1);
  });
});
