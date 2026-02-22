import React, { useState } from 'react';
import { IntakeLayout } from './IntakeLayout';
import { StepUpload } from './steps/StepUpload';
import { StepSymptoms } from './steps/StepSymptoms';
import { StepVision } from './steps/StepVision';
import { useExtract } from '../../../api/hooks/useExtract';
import { usePatientStore } from '../../../api/hooks/usePatientStore';

interface IntakeWizardProps {
  onComplete: () => void;
}

// Each step gets its own doctor PNG
const STEP_IMAGES: Record<number, string> = {
  1: '/assets/doctor-hero-pointing.png',
  2: '/assets/doctor-heart-pensive.png',
  3: '/assets/doctor-hero-camera.png',
};

// Narration per step
const NARRATION: Record<number, { greeting: string; tip: React.ReactNode }> = {
  1: {
    greeting: "Let's find your pattern!",
    tip: <>Upload <b className="text-white">bloodwork PDFs</b>, <b className="text-white">lab panels</b>, or <b className="text-white">doctor's notes</b>. The more <b className="text-white">years of data</b>, the clearer the pattern — even <b className="text-white">2–3 reports</b> help!</>,
  },
  2: {
    greeting: "Now tell me how you feel.",
    tip: <>Describe <b className="text-white">when it started</b>, what makes it <b className="text-white">worse</b>, and any <b className="text-white">patterns</b> you've noticed. Tap the chips below to add <b className="text-white">common symptoms</b> quickly.</>,
  },
  3: {
    greeting: "Almost there!",
    tip: <>A photo of a <b className="text-white">rash</b>, <b className="text-white">swelling</b>, or <b className="text-white">skin change</b> lets our vision model translate what it sees into <b className="text-white">clinical language</b> for deeper analysis.</>,
  },
};

export const IntakeWizard = ({ onComplete }: IntakeWizardProps) => {
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState<{ name: string; status: 'parsing' | 'done' | 'error'; errorMsg?: string }[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const extractMutation = useExtract();
  const setPdfs = usePatientStore((s) => s.setPdfs);
  const patientAge = usePatientStore((s) => s.patientAge);
  const setPatientAge = usePatientStore((s) => s.setPatientAge);
  const patientSex = usePatientStore((s) => s.patientSex);
  const setPatientSex = usePatientStore((s) => s.setPatientSex);

  const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
  const MAX_FILE_SIZE = 50 * 1024 * 1024;

  const handleNext = () => {
    if (step < 3) setStep(step + 1);
    else onComplete();
  };

  const validateAndAddFile = async (file: File) => {
    setFileError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setFileError(`"${file.name}" is not a supported file type. Please upload a PDF, JPG, or PNG.`);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setFileError(`"${file.name}" exceeds the 50 MB limit. Try a smaller file.`);
      return;
    }
    if (file.size < 1024) {
      setFileError(`"${file.name}" appears to be empty or corrupted. Try uploading a clearer copy.`);
      return;
    }
    const entry = { name: file.name, status: 'parsing' as const };
    setFiles(prev => [...prev, entry]);
    try {
      await extractMutation.mutateAsync([file]);
      setFiles(prev =>
        prev.map(f => f.name === file.name && f.status === 'parsing' ? { ...f, status: 'done' } : f)
      );
      // Store File object in Zustand for the full pipeline dispatch
      const currentPdfs = usePatientStore.getState().pdfs;
      setPdfs([...currentPdfs, file]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setFiles(prev =>
        prev.map(f => f.name === file.name && f.status === 'parsing' ? { ...f, status: 'error', errorMsg: msg } : f)
      );
      setFileError(msg);
    }
  };

  const handleFileUpload = () => fileInputRef.current?.click();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected) return;
    Array.from(selected).forEach(validateAndAddFile);
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files;
    if (!dropped) return;
    Array.from(dropped).forEach(validateAndAddFile);
  };

  const { greeting, tip } = NARRATION[step];

  return (
    <IntakeLayout
      step={step}
      doctorImage={STEP_IMAGES[step]}
      greeting={greeting}
      tip={tip}
    >
      {step === 1 && (
        <>
          {/* Demographics — age and sex, stored in Zustand for pipeline dispatch */}
          <div className="flex gap-4 w-full max-w-lg mb-4">
            <div className="flex-1">
              <label className="block text-xs text-[#8A93B2] mb-1">Age</label>
              <input
                type="number"
                min={1}
                max={120}
                value={patientAge}
                onChange={(e) => setPatientAge(Number(e.target.value))}
                className="w-full bg-[#0A0D14] border border-[#2A2E3B] rounded-lg px-3 py-2 text-sm text-[#F0F2F8] focus:border-[#7B61FF] focus:outline-none"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-[#8A93B2] mb-1">Biological sex</label>
              <select
                value={patientSex}
                onChange={(e) => setPatientSex(e.target.value)}
                className="w-full bg-[#0A0D14] border border-[#2A2E3B] rounded-lg px-3 py-2 text-sm text-[#F0F2F8] focus:border-[#7B61FF] focus:outline-none"
              >
                <option value="F">Female</option>
                <option value="M">Male</option>
                <option value="O">Other / prefer not to say</option>
              </select>
            </div>
          </div>

          <StepUpload
            files={files}
            fileError={fileError}
            fileInputRef={fileInputRef}
            onFileChange={handleFileChange}
            onFileUpload={handleFileUpload}
            onDrop={handleDrop}
            onClearError={() => setFileError(null)}
            onNext={handleNext}
            onSkipToSymptoms={() => { setFileError(null); setStep(2); }}
            isPending={extractMutation.isPending}
          />
        </>
      )}

      {step === 2 && (
        <StepSymptoms onNext={handleNext} />
      )}

      {step === 3 && (
        <StepVision onComplete={onComplete} />
      )}
    </IntakeLayout>
  );
};
