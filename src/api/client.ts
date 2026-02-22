/**
 * Aura API client.
 *
 * JSON endpoints: use the typed `apiClient` (openapi-fetch).
 * Multipart endpoints (/extract, /interview, /pipeline/full): use `postMultipart`
 * because openapi-fetch cannot auto-build FormData with a boundary.
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";

// ---------------------------------------------------------------------------
// Typed JSON client — all non-multipart endpoints
// ---------------------------------------------------------------------------

export const apiClient = createClient<paths>({ baseUrl: "/api" });

// ---------------------------------------------------------------------------
// Multipart helper — /extract, /interview, /pipeline/full
// ---------------------------------------------------------------------------

/**
 * POST multipart/form-data to a backend endpoint.
 * Do NOT set Content-Type manually — the browser sets it with the correct boundary.
 *
 * @param path  Backend path without the /api prefix (e.g. "/extract")
 * @param formData  Pre-built FormData object
 */
export async function postMultipart<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Convenience re-export for Phase 1 compatibility
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  databricks: boolean;
  vllm: boolean;
  sessions_active: number;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data, error } = await apiClient.GET("/health");
  if (error) throw new Error("Health check failed");
  return data as HealthResponse;
}
