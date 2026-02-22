import { useEffect, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { eventToStepIndex } from "../../app/components/processing/Processing";

export interface PipelineStreamEvent {
  type?: string;
  phase?: string;
  detail?: string;
  agent?: string;   // ThoughtStream events have "agent" with "The " prefix
  summary?: string;
  job_id?: string;
}

interface UsePipelineStreamOptions {
  patientId: string | null;
  onStepChange: (step: number) => void;
  onSubLabel: (label: string) => void;
  onDone: () => void;
  onStreamError: (msg: string) => void;
}

/**
 * SSE hook: connects to GET /api/stream/{patientId} and drives the processing
 * screen in real time.
 *
 * Handles both event shapes:
 *   - Progress: { type: "progress", phase: "extract", detail: "…" }
 *   - ThoughtStream: { agent: "The Extractor", summary: "…" }
 *
 * Aborts on unmount, terminal event, or page hidden (fallback to polling).
 * SSE is primary; useJobStatus polling remains as fallback.
 */
export function usePipelineStream({
  patientId,
  onStepChange,
  onSubLabel,
  onDone,
  onStreamError,
}: UsePipelineStreamOptions) {
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!patientId) return;

    const controller = new AbortController();
    abortRef.current = controller;

    fetchEventSource(`/api/stream/${patientId}`, {
      signal: controller.signal,

      onmessage(ev) {
        if (!ev.data) return;
        let data: PipelineStreamEvent;
        try {
          data = JSON.parse(ev.data) as PipelineStreamEvent;
        } catch {
          return;
        }

        // Terminal events
        if (data.type === "done") {
          onDone();
          controller.abort();
          return;
        }
        if (data.type === "error") {
          onStreamError(data.detail ?? "Pipeline error");
          controller.abort();
          return;
        }

        // Progress event: { type: "progress", phase: "extract", detail: "…" }
        if (data.phase) {
          onStepChange(eventToStepIndex(data.phase));
          if (data.detail) onSubLabel(data.detail);
          return;
        }

        // ThoughtStream event: { agent: "The Extractor", summary: "…" }
        if (data.agent) {
          // agent names have "The " prefix: "The Extractor" → phase "extract"
          const phaseGuess = data.agent.toLowerCase().replace(/^the /, "").split(" ")[0];
          onStepChange(eventToStepIndex(phaseGuess));
          if (data.summary) onSubLabel(data.summary);
        }
      },

      onerror(err) {
        // Don't call onStreamError for AbortError (intentional abort)
        if (err instanceof DOMException && err.name === "AbortError") return;
        onStreamError(String(err));
        throw err; // Stop fetchEventSource from retrying
      },
    });

    // Pause SSE when tab is hidden — polling fallback takes over
    const handleVisibility = () => {
      if (document.visibilityState === "hidden") {
        controller.abort();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      controller.abort();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [patientId]);
}
