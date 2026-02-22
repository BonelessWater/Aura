import { useEffect } from "react";
import { toast } from "sonner";
import { queryClient } from "../queryClient";

/**
 * Global API error handler for TanStack Query.
 *
 * Call once at the top of the component tree (in App). Subscribes to the
 * query cache and shows a sonner toast for any query or mutation failure
 * that is not a 404 (404s are handled inline by the component).
 *
 * Uses queryClient.getQueryCache().subscribe() so it works with the
 * singleton queryClient without modifying the QueryClient constructor.
 */
export function useApiError() {
  useEffect(() => {
    const unsubscribeQuery = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === "updated" && event.query.state.status === "error") {
        const error = event.query.state.error as Error | null;
        if (!error) return;

        // 404 is handled inline — don't toast
        const is404 =
          (error as Error & { status?: number }).status === 404 ||
          error.message.includes("not found") ||
          error.message.includes("404");

        if (!is404) {
          toast.error(error.message || "An API error occurred", {
            id: "api-error", // deduplicate repeated errors
          });
        }
      }
    });

    const unsubscribeMutation = queryClient
      .getMutationCache()
      .subscribe((event) => {
        if (
          event.type === "updated" &&
          event.mutation?.state.status === "error"
        ) {
          const error = event.mutation.state.error as Error | null;
          if (error) {
            toast.error(error.message || "Request failed", {
              id: "mutation-error",
            });
          }
        }
      });

    return () => {
      unsubscribeQuery();
      unsubscribeMutation();
    };
  }, []);
}
