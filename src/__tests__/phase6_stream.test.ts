/**
 * Phase 6 frontend tests: usePipelineStream SSE hook.
 *
 * fetchEventSource is mocked so no live server is required.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import React from "react";

// ── Mock fetchEventSource before importing the hook ───────────────────────────

vi.mock("@microsoft/fetch-event-source", () => ({
  fetchEventSource: vi.fn(),
}));

vi.mock("../api/client", () => ({
  apiClient: { GET: vi.fn() },
  postMultipart: vi.fn(),
}));

import { usePipelineStream } from "../api/hooks/usePipelineStream";
import { fetchEventSource } from "@microsoft/fetch-event-source";

// ── Helper to simulate fetchEventSource sending events ────────────────────────

type MockFES = ReturnType<typeof vi.fn>;

function simulateFES(
  events: Array<{ data: string }>,
  abortError = false,
): void {
  vi.mocked(fetchEventSource).mockImplementation((_url, opts) => {
    const { onmessage, onerror } = opts as {
      onmessage?: (ev: { data: string }) => void;
      onerror?: (err: unknown) => void;
      signal?: AbortSignal;
    };

    // Simulate receiving events asynchronously
    Promise.resolve().then(() => {
      for (const ev of events) {
        onmessage?.(ev);
      }
      if (abortError) {
        onerror?.(new DOMException("Aborted", "AbortError"));
      }
    });

    return Promise.resolve();
  });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("usePipelineStream", () => {
  const noop = () => {};

  beforeEach(() => {
    vi.mocked(fetchEventSource).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("connects to /api/stream/{patientId}", async () => {
    simulateFES([{ data: JSON.stringify({ type: "done", job_id: "j1" }) }]);

    renderHook(() =>
      usePipelineStream({
        patientId: "test-patient-123",
        onStepChange: noop,
        onSubLabel: noop,
        onDone: noop,
        onStreamError: noop,
      }),
    );

    await waitFor(() => {
      expect(vi.mocked(fetchEventSource)).toHaveBeenCalledWith(
        expect.stringContaining("test-patient-123"),
        expect.any(Object),
      );
    });
  });

  it("does NOT connect when patientId is null", () => {
    renderHook(() =>
      usePipelineStream({
        patientId: null,
        onStepChange: noop,
        onSubLabel: noop,
        onDone: noop,
        onStreamError: noop,
      }),
    );

    expect(vi.mocked(fetchEventSource)).not.toHaveBeenCalled();
  });

  it("calls onStepChange with correct index on progress event", async () => {
    const events = [
      { data: JSON.stringify({ type: "progress", phase: "route", detail: "Scoring" }) },
      { data: JSON.stringify({ type: "done" }) },
    ];
    simulateFES(events);

    const stepChanges: number[] = [];
    renderHook(() =>
      usePipelineStream({
        patientId: "p1",
        onStepChange: (s) => stepChanges.push(s),
        onSubLabel: noop,
        onDone: noop,
        onStreamError: noop,
      }),
    );

    await waitFor(() => expect(stepChanges.length).toBeGreaterThan(0));
    expect(stepChanges[0]).toBe(2); // route → index 2
  });

  it("calls onDone on terminal done event", async () => {
    simulateFES([{ data: JSON.stringify({ type: "done", job_id: "j1" }) }]);

    let doneCount = 0;
    renderHook(() =>
      usePipelineStream({
        patientId: "p2",
        onStepChange: noop,
        onSubLabel: noop,
        onDone: () => { doneCount++; },
        onStreamError: noop,
      }),
    );

    await waitFor(() => expect(doneCount).toBe(1));
  });

  it("calls onSubLabel with detail text from progress event", async () => {
    const events = [
      { data: JSON.stringify({ type: "progress", phase: "extract", detail: "Parsing biomarkers" }) },
      { data: JSON.stringify({ type: "done" }) },
    ];
    simulateFES(events);

    const labels: string[] = [];
    renderHook(() =>
      usePipelineStream({
        patientId: "p3",
        onStepChange: noop,
        onSubLabel: (l) => labels.push(l),
        onDone: noop,
        onStreamError: noop,
      }),
    );

    await waitFor(() => expect(labels.length).toBeGreaterThan(0));
    expect(labels[0]).toBe("Parsing biomarkers");
  });
});
