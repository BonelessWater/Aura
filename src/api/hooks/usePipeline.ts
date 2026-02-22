import { useMutation } from "@tanstack/react-query";
import { postMultipart } from "../client";
import { usePatientStore } from "./usePatientStore";

export interface PipelineDispatchResponse {
  patient_id: string;
  job_id: string;
  status: "queued";
}

/**
 * Mutation hook: dispatch the full pipeline to POST /pipeline/full.
 *
 * FormData field for PDFs is `pdfs` (NOT `files` — that's /extract).
 * `symptom_text` is ALWAYS sent (even as empty string); omitting it returns 422.
 */
export function usePipeline() {
  const ensurePatientId = usePatientStore((s) => s.ensurePatientId);
  const symptoms = usePatientStore((s) => s.symptoms);
  const selectedChips = usePatientStore((s) => s.selectedChips);
  const patientAge = usePatientStore((s) => s.patientAge);
  const patientSex = usePatientStore((s) => s.patientSex);
  const medications = usePatientStore((s) => s.medications);
  const pdfs = usePatientStore((s) => s.pdfs);
  const images = usePatientStore((s) => s.images);
  const setJobId = usePatientStore((s) => s.setJobId);
  const setPipelineStatus = usePatientStore((s) => s.setPipelineStatus);

  return useMutation({
    mutationFn: async (): Promise<PipelineDispatchResponse> => {
      const patientId = ensurePatientId();
      // Join free-text symptoms and chip selections into a single string
      const symptomText = [symptoms, ...selectedChips].filter(Boolean).join(", ");

      const fd = new FormData();
      fd.append("patient_id", patientId);
      fd.append("symptom_text", symptomText); // required — always send
      fd.append("patient_age", String(patientAge));
      fd.append("patient_sex", patientSex);
      fd.append("medications", medications);
      pdfs.forEach((f) => fd.append("pdfs", f));    // field: pdfs (not files)
      images.forEach((f) => fd.append("images", f));

      return postMultipart<PipelineDispatchResponse>("/pipeline/full", fd);
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
      setPipelineStatus("processing");
    },
    onError: () => {
      setPipelineStatus("error");
    },
  });
}
