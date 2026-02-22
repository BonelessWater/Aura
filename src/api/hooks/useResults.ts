import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../client";
import type { components } from "../schema";
import { usePatientStore } from "./usePatientStore";

export type ResultsResponse = components["schemas"]["ResultsResponse"];
export type DiseaseCandidate = components["schemas"]["DiseaseCandidate"];
export type RouterOutput = components["schemas"]["RouterOutput"];
export type TranslatorOutput = components["schemas"]["TranslatorOutput"];

/**
 * Fetches pipeline results for the current patient.
 *
 * Only enabled when:
 *   - patientId is set
 *   - pipelineStatus is "done"
 *
 * Returns null data while pipeline is still running or not yet started.
 */
export function useResults() {
  const patientId = usePatientStore((s) => s.patientId);
  const pipelineStatus = usePatientStore((s) => s.pipelineStatus);

  return useQuery({
    queryKey: ["results", patientId],
    queryFn: async (): Promise<ResultsResponse> => {
      const { data, error, response } = await apiClient.GET(
        "/results/{patient_id}",
        { params: { path: { patient_id: patientId! } } },
      );
      if (response.status === 404) {
        throw new Error("Patient session not found");
      }
      if (error || !data) {
        throw new Error("Failed to fetch results");
      }
      return data;
    },
    enabled: !!patientId && pipelineStatus === "done",
    staleTime: Infinity, // Results are immutable once the pipeline completes
  });
}
