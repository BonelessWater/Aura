import { useMutation } from "@tanstack/react-query";
import { postMultipart } from "../client";
import { usePatientStore } from "./usePatientStore";

export interface ExtractResponse {
  patient_id: string;
  lab_report: {
    patient_id: string;
    patient_age: number;
    patient_sex: string;
    markers: Array<Record<string, unknown>>;
    disease_candidates?: Array<unknown>;
  };
}

/**
 * Mutation hook: upload one or more files to POST /extract.
 * FormData field name must be `files` (distinct from `/pipeline/full` which uses `pdfs`).
 */
export function useExtract() {
  const ensurePatientId = usePatientStore((s) => s.ensurePatientId);
  const patientAge = usePatientStore((s) => s.patientAge);
  const patientSex = usePatientStore((s) => s.patientSex);

  return useMutation({
    mutationFn: async (files: File[]): Promise<ExtractResponse> => {
      const patientId = ensurePatientId();
      const fd = new FormData();
      fd.append("patient_id", patientId);
      fd.append("patient_age", String(patientAge));
      fd.append("patient_sex", patientSex);
      files.forEach((f) => fd.append("files", f));
      return postMultipart<ExtractResponse>("/extract", fd);
    },
  });
}
