import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../client";

export type JobStatusValue = "queued" | "running" | "done" | "error";

export interface JobStatusResponse {
  job_id: string;
  patient_id: string;
  status: JobStatusValue;
  result: Record<string, unknown> | null;
  error: string | null;
}

/**
 * Polling query for GET /jobs/{job_id}.
 * Refetches every 2 seconds while the job is queued or running.
 * Stops polling automatically when status reaches `done` or `error`.
 */
export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async (): Promise<JobStatusResponse> => {
      if (!jobId) throw new Error("No job ID");
      const { data, error } = await apiClient.GET("/jobs/{job_id}", {
        params: { path: { job_id: jobId } },
      });
      if (error) throw new Error("Failed to fetch job status");
      return data as JobStatusResponse;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = (query.state.data as JobStatusResponse | undefined)?.status;
      if (status === "done" || status === "error") return false;
      return 2000;
    },
    staleTime: 0,
    retry: 1,
  });
}
