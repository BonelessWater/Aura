import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PatientState {
  patientId: string | null;
  jobId: string | null;
  pipelineStatus: "idle" | "uploading" | "processing" | "done" | "error";

  // Intake data (collected across wizard steps, sent on submit)
  pdfs: File[];              // field name matches /pipeline/full backend field
  symptoms: string;
  selectedChips: string[];
  images: File[];            // from StepVision photo capture
  patientAge: number;
  patientSex: string;
  medications: string;       // comma-separated

  // Wizard step (managed here to survive re-renders)
  wizardStep: number;

  // Actions
  ensurePatientId: () => string;
  setJobId: (id: string) => void;
  setPipelineStatus: (status: PatientState["pipelineStatus"]) => void;
  setPdfs: (files: File[]) => void;
  setSymptoms: (text: string) => void;
  toggleChip: (chip: string) => void;
  setImages: (files: File[]) => void;
  setPatientAge: (age: number) => void;
  setPatientSex: (sex: string) => void;
  setMedications: (meds: string) => void;
  setWizardStep: (step: number) => void;
  reset: () => void;
}

const INITIAL: Omit<
  PatientState,
  | "ensurePatientId"
  | "setJobId"
  | "setPipelineStatus"
  | "setPdfs"
  | "setSymptoms"
  | "toggleChip"
  | "setImages"
  | "setPatientAge"
  | "setPatientSex"
  | "setMedications"
  | "setWizardStep"
  | "reset"
> = {
  patientId: null,
  jobId: null,
  pipelineStatus: "idle",
  pdfs: [],
  symptoms: "",
  selectedChips: [],
  images: [],
  patientAge: 40,
  patientSex: "F",
  medications: "",
  wizardStep: 1,
};

export const usePatientStore = create<PatientState>()(
  persist(
    (set, get) => ({
      ...INITIAL,

      ensurePatientId: () => {
        let id = get().patientId;
        if (!id) {
          id = crypto.randomUUID();
          set({ patientId: id });
        }
        return id;
      },

      setJobId: (id) => set({ jobId: id }),
      setPipelineStatus: (status) => set({ pipelineStatus: status }),
      setPdfs: (files) => set({ pdfs: files }),
      setSymptoms: (text) => set({ symptoms: text }),
      toggleChip: (chip) =>
        set((s) => ({
          selectedChips: s.selectedChips.includes(chip)
            ? s.selectedChips.filter((c) => c !== chip)
            : [...s.selectedChips, chip],
        })),
      setImages: (files) => set({ images: files }),
      setPatientAge: (age) => set({ patientAge: age }),
      setPatientSex: (sex) => set({ patientSex: sex }),
      setMedications: (meds) => set({ medications: meds }),
      setWizardStep: (step) => set({ wizardStep: step }),

      reset: () =>
        set({
          ...INITIAL,
          // Generate a fresh UUID on reset so the next session is independent
          patientId: null,
        }),
    }),
    {
      name: "aura-patient",
      // Only persist the patient ID across page refreshes.
      // File objects (pdfs, images) are not JSON-serialisable.
      partialize: (state) => ({ patientId: state.patientId }),
    },
  ),
);
