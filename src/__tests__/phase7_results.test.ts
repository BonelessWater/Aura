/**
 * Phase 7 frontend tests: useResults hook, ResultsDashboard, SOAPNote,
 * and ClinicianPortal with real-data hydration.
 *
 * apiClient is mocked at module level so no live server is required.
 */

import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router";

// React 19 changed the return type of function components; cast to avoid TS2769
const MRouter = MemoryRouter as React.ComponentType<any>;
const MRoutes = Routes as React.ComponentType<any>;
const MRoute = Route as React.ComponentType<any>;

// ── Polyfill browser APIs missing in jsdom ───────────────────────────────────

(globalThis as any).IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// ── Mock at module level (hoisted) ──────────────────────────────────────────

vi.mock("../api/client", () => ({
  apiClient: { GET: vi.fn() },
  postMultipart: vi.fn(),
}));

vi.mock("../api/hooks/usePatientStore", () => ({
  usePatientStore: vi.fn((selector: (s: any) => any) =>
    selector({
      patientId: "test-patient-uuid",
      pipelineStatus: "done",
      jobId: null,
      pdfs: [],
      symptoms: "",
      selectedChips: [],
      images: [],
      patientAge: 40,
      patientSex: "F",
      medications: "",
      wizardStep: 1,
      ensurePatientId: () => "test-patient-uuid",
      setJobId: vi.fn(),
      setPipelineStatus: vi.fn(),
      setPdfs: vi.fn(),
      setSymptoms: vi.fn(),
      toggleChip: vi.fn(),
      setImages: vi.fn(),
      setPatientAge: vi.fn(),
      setPatientSex: vi.fn(),
      setMedications: vi.fn(),
      setWizardStep: vi.fn(),
      reset: vi.fn(),
    })
  ),
}));

// Stub out heavy/browser-dependent components that aren't under test
vi.mock("../app/components/results/DoctorHoverHelper", () => ({
  DoctorHoverHelper: () => null,
}));

vi.mock("../app/components/results/DailyNotes", () => ({
  DailyNotes: () => React.createElement("div", { "data-testid": "daily-notes" }),
}));

import { useResults } from "../api/hooks/useResults";
import * as clientModule from "../api/client";

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeQC() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

const MOCK_RESULTS = {
  patient_id: "test-patient-uuid",
  lab_report: {
    patient_id: "test-patient-uuid",
    markers: [{ loinc_code: "2093-3", display_name: "CRP", values: [] }],
    bio_fingerprint: {},
  },
  interview_result: null,
  research_result: null,
  router_output: {
    patient_id: "test-patient-uuid",
    cluster: "Systemic",
    cluster_alignment_score: 0.87,
    routing_recommendation: "Rheumatology",
    disease_candidates: [
      {
        disease: "Systemic Lupus Erythematosus",
        disease_alignment_score: 0.72,
        supporting_dois: [],
        criteria_met: [],
        criteria_count: 0,
        criteria_cap_applied: false,
        drug_induced_flag: false,
      },
    ],
  },
  translator_output: {
    patient_id: "test-patient-uuid",
    soap_note:
      "S: Patient reports fatigue.\nO: CRP elevated.\nA: Autoimmune pattern.\nP: Refer.",
    layman_compass: "Your immune system appears overactive.",
    faithfulness_score: 0.91,
    flagged_sentences: [],
    fk_grade_level: 9.5,
  },
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useResults", () => {
  beforeEach(() => {
    vi.mocked(clientModule.apiClient.GET).mockReset();
  });

  it("fetches results by patientId when pipelineStatus is done", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: MOCK_RESULTS,
      error: undefined,
      response: { status: 200 } as Response,
    });

    const qc = makeQC();
    const { result } = renderHook(() => useResults(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(clientModule.apiClient.GET)).toHaveBeenCalledWith(
      "/results/{patient_id}",
      expect.objectContaining({
        params: { path: { patient_id: "test-patient-uuid" } },
      }),
    );
    expect(result.current.data?.router_output?.cluster_alignment_score).toBe(
      0.87,
    );
  });

  it("throws on 404 response", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: null,
      error: undefined,
      response: { status: 404 } as Response,
    });

    const qc = makeQC();
    const { result } = renderHook(() => useResults(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toMatch(/not found/i);
  });
});

describe("ResultsDashboard", () => {
  beforeEach(() => {
    vi.mocked(clientModule.apiClient.GET).mockReset();
  });

  it("renders disease_alignment_score from results", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: MOCK_RESULTS,
      error: undefined,
      response: { status: 200 } as Response,
    });

    const { ResultsDashboard } = await import(
      "../app/components/results/ResultsDashboard"
    );
    const qc = makeQC();

    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          MRouter,
          {},
          React.createElement(ResultsDashboard, {}),
        ),
      ),
    );

    // Score should appear: 87% (cluster_alignment_score 0.87 → 87%)
    await waitFor(() => {
      expect(screen.getByText("87%")).toBeInTheDocument();
    });
  });

  it("shows skeleton while loading", async () => {
    vi.mocked(clientModule.apiClient.GET).mockImplementation(
      () => new Promise(() => {}), // Never resolves
    );

    const { ResultsDashboard } = await import(
      "../app/components/results/ResultsDashboard"
    );
    const qc = makeQC();

    const { container } = render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          MRouter,
          {},
          React.createElement(ResultsDashboard, {}),
        ),
      ),
    );

    // Skeleton pulse divs should be present during loading
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders standalone without callback props", async () => {
    vi.mocked(clientModule.apiClient.GET).mockImplementation(
      () => new Promise(() => {}),
    );

    const { ResultsDashboard } = await import(
      "../app/components/results/ResultsDashboard"
    );
    const qc = makeQC();

    // No props — should render without throwing
    let thrownError: unknown = null;
    try {
      render(
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(
            MRouter,
            {},
            React.createElement(ResultsDashboard, {}),
          ),
        ),
      );
    } catch (err) {
      thrownError = err;
    }
    expect(thrownError).toBeNull();
  });
});

describe("SOAPNote", () => {
  it("renders single-string soap_note when provided", async () => {
    const { SOAPNote } = await import(
      "../app/components/results/SOAPNote"
    );

    render(
      React.createElement(
        MRouter,
        {},
        React.createElement(SOAPNote, {
          isOpen: true,
          onClose: vi.fn(),
          soapNote: "S: Patient reports fatigue.\nO: CRP elevated.",
        }),
      ),
    );

    expect(
      screen.getByText(/Patient reports fatigue/i),
    ).toBeInTheDocument();
  });

  it("falls back to demo content when soapNote is null", async () => {
    const { SOAPNote } = await import(
      "../app/components/results/SOAPNote"
    );

    render(
      React.createElement(
        MRouter,
        {},
        React.createElement(SOAPNote, {
          isOpen: true,
          onClose: vi.fn(),
          soapNote: null,
        }),
      ),
    );

    // Demo content has the word "Subjective"
    expect(screen.getByText("Subjective")).toBeInTheDocument();
  });
});

describe("ClinicianPortal", () => {
  beforeEach(() => {
    vi.mocked(clientModule.apiClient.GET).mockReset();
  });

  it("loads results by patient_id from URL", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: MOCK_RESULTS,
      error: undefined,
      response: { status: 200 } as Response,
    });

    const { ClinicianPortal } = await import("../app/views/ClinicianPortal");
    const qc = makeQC();

    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          MRouter,
          { initialEntries: ["/clinician/test-patient-uuid"] },
          React.createElement(
            MRoutes,
            {},
            React.createElement(MRoute, {
              path: "/clinician/:id",
              element: React.createElement(ClinicianPortal),
            }),
          ),
        ),
      ),
    );

    await waitFor(() => {
      expect(vi.mocked(clientModule.apiClient.GET)).toHaveBeenCalledWith(
        "/results/{patient_id}",
        expect.objectContaining({
          params: { path: { patient_id: "test-patient-uuid" } },
        }),
      );
    });
  });

  it("shows 404 message for unknown patient", async () => {
    vi.mocked(clientModule.apiClient.GET).mockResolvedValue({
      data: null,
      error: undefined,
      response: { status: 404 } as Response,
    });

    const { ClinicianPortal } = await import("../app/views/ClinicianPortal");
    const qc = makeQC();

    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          MRouter,
          { initialEntries: ["/clinician/unknown-xyz"] },
          React.createElement(
            MRoutes,
            {},
            React.createElement(MRoute, {
              path: "/clinician/:id",
              element: React.createElement(ClinicianPortal),
            }),
          ),
        ),
      ),
    );

    await waitFor(() => {
      expect(screen.getByText(/Patient Not Found/i)).toBeInTheDocument();
    });
  });
});
