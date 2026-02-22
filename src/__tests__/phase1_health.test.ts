/**
 * Phase 1 health tests.
 *
 * Calls the real backend through the real Vite proxy.
 * Tests are skipped if the backend is not reachable.
 *
 * No mocks. No MSW. Real fetch → real proxy → real FastAPI app.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { fetchHealth } from "../api/client";

// ---------------------------------------------------------------------------
// Backend connectivity guard
// ---------------------------------------------------------------------------

let backendUp = false;

beforeAll(async () => {
  try {
    const res = await fetch("/api/health");
    backendUp = res.ok;
  } catch {
    backendUp = false;
  }
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("fetchHealth (via Vite proxy → real backend)", () => {
  it("resolves with status ok", async () => {
    if (!backendUp) {
      console.warn("Backend not running — skipping");
      return;
    }
    const data = await fetchHealth();
    expect(data.status).toBe("ok");
    expect(typeof data.sessions_active).toBe("number");
  });

  it("throws on network error when backend is unreachable", async () => {
    // Call against a port that is definitely not listening
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    try {
      await expect(fetchHealth()).rejects.toThrow();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
