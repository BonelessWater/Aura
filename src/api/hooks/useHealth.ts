import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../client";
import type { HealthResponse } from "../client";

/**
 * Typed health query hook.
 * Polls the backend health endpoint every 30 s (staleTime from queryClient).
 * isError is true when the backend is unreachable.
 */
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/health");
      if (error) throw new Error("Health check failed");
      return data as HealthResponse;
    },
  });
}
