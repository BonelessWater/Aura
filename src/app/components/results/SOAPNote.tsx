import React, { useEffect } from 'react';
import { motion } from 'motion/react';
import { X, Download, FileText, QrCode, ExternalLink } from 'lucide-react';

interface SOAPNoteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SOAPNote = ({ isOpen, onClose }: SOAPNoteProps) => {
  // Close on ESC
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: isOpen ? "0%" : "100%" }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
      className="fixed inset-y-0 right-0 w-full md:w-[600px] bg-white text-[#111111] shadow-2xl z-[60] overflow-y-auto pointer-events-auto"
      style={{ pointerEvents: isOpen ? 'auto' : 'none' }}
    >
      {/* Header Banner */}
      <div className="bg-[#F4A261] text-[#111111] px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <span className="text-sm font-medium flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Print or screenshot this to hand to your doctor.
        </span>
        <button onClick={onClose} className="p-1 hover:bg-black/10 rounded-full transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-8 md:p-12 font-serif">
        <div className="mb-8 border-b border-gray-200 pb-6">
          <h1 className="text-3xl font-bold mb-2 text-black font-sans">Clinical Summary</h1>
          <p className="text-gray-500 text-sm">Generated on {new Date().toLocaleDateString()}</p>
        </div>

        <div className="space-y-8">
          <Section title="Subjective">
            <p>
              Patient reports an 18-month history of progressive joint pain, recurring malar rash, and persistent fatigue. 
              Symptoms worsen with sun exposure. Reports intermittent oral ulcers and hair thinning over the last 6 months.
            </p>
          </Section>

          <Section title="Objective">
            <ul className="list-disc pl-5 space-y-1">
              <li>CRP: 8.4 mg/L (elevated; trending upward from 3.1 mg/L 12 months prior)</li>
              <li>NLR (Neutrophil-to-Lymphocyte Ratio): 4.8 (elevated, suggestive of systemic inflammation)</li>
              <li>WBC: 3.2 × 10³/µL (leukopenia)</li>
              <li>Visual evidence: Bilateral malar erythema consistent with butterfly rash; localized joint edema in MCPs</li>
            </ul>
          </Section>

          <Section title="Assessment">
            <p>
              Data indicates a <strong>92% alignment</strong> with a Systemic Autoimmune profile, with secondary literature flags (<strong>65%</strong>) suggesting a Systemic Lupus Erythematosus (SLE) etiology.
            </p>
            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
               <strong>Citations:</strong>
               <br />
               <a href="https://pubmed.ncbi.nlm.nih.gov/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">1. Sustained CRP elevation combined with localized erythema is highly characteristic of systemic autoimmune escalation. <em>J Clin Rheumatol</em>, 2024. DOI: 10.1097/RHU.0000000000002076</a>
               <br />
               <a href="https://pubmed.ncbi.nlm.nih.gov/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">2. Leukopenia with elevated NLR as a predictive marker in early SLE. <em>Lupus</em>, 2023. DOI: 10.1177/09612033231178</a>
            </div>
          </Section>

          <Section title="Plan">
            <ol className="list-decimal pl-5 space-y-1">
              <li>Urgent referral to Rheumatology for ANA, anti-dsDNA, and complement (C3/C4) panel.</li>
              <li>Dermatology consult for biopsy of malar rash if persistent.</li>
              <li>Renal function screen (urinalysis + serum creatinine) to rule out lupus nephritis.</li>
              <li>Follow-up in 4 weeks with repeat inflammatory markers.</li>
            </ol>
          </Section>
        </div>

        <div className="mt-12 flex flex-col sm:flex-row justify-end gap-3">
          <a
            href="/clinician/A7B2"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3 bg-white text-[#111111] rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors text-sm"
          >
            <QrCode className="w-4 h-4" />
            Clinician Verification Portal
            <ExternalLink className="w-3 h-3 text-gray-400" />
          </a>
          <button className="flex items-center gap-2 px-6 py-3 bg-[#111111] text-white rounded-lg hover:bg-black/80 transition-colors">
            <Download className="w-4 h-4" />
            Download as PDF
          </button>
        </div>
      </div>
    </motion.div>
  );
};

const Section = ({ title, children }: { title: string, children: React.ReactNode }) => (
  <div className="mb-6">
    <h3 className="text-sm uppercase tracking-wider font-bold text-gray-400 mb-3 border-b border-gray-100 pb-1">{title}</h3>
    <div className="text-lg leading-relaxed text-gray-900">
      {children}
    </div>
  </div>
);