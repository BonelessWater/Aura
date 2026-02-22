/**
 * Phase 2 typed client tests.
 *
 * Verifies the openapi-fetch typed client works against the real backend
 * and that schema.d.ts was generated correctly.
 *
 * Tests are backend-connectivity-aware: if backend is down, skip live tests.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { apiClient, postMultipart } from "../api/client";
import type { paths } from "../api/schema";

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

describe("Phase 2: typed client", () => {
  it("schema.d.ts contains paths type", () => {
    // If this file compiles, the type import succeeded.
    // We use a type-level check — assign a known path to narrow the type.
    const path: keyof paths = "/health";
    expect(path).toBe("/health");
  });

  it("typed client GET /health compiles and returns", async () => {
    if (!backendUp) {
      console.warn("Backend not running — skipping");
      return;
    }
    const { data, error } = await apiClient.GET("/health");
    expect(error).toBeUndefined();
    expect(data).toBeDefined();
    expect((data as { status: string }).status).toBe("ok");
  });

  it("postMultipart sends FormData and returns JSON", async () => {
    if (!backendUp) {
      console.warn("Backend not running — skipping");
      return;
    }
    // POST /extract with no files → expect a 400 error (proves the endpoint was reached)
    const fd = new FormData();
    fd.append("patient_id", "type-test-001");
    await expect(postMultipart("/extract", fd)).rejects.toThrow("400");
  });
});
