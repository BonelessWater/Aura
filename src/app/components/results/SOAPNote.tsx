import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Download, FileText, QrCode, ExternalLink, Stethoscope, AlertTriangle } from 'lucide-react';
import { usePatientStore } from '../../../api/hooks/usePatientStore';

interface SOAPNoteProps {
  isOpen: boolean;
  onClose: () => void;
  /** Real SOAP note string from the pipeline. Falls back to demo content when null. */
  soapNote?: string | null;
}

/* ── Inline CRP sparkline ── */
const CRPSparkline = () => {
  const data = [3.1, 4.2, 5.7, 6.9, 8.4];
  const max = 10, w = 100, h = 24;
  const pts = data.map((v, i) => ({ x: (i / (data.length - 1)) * w, y: h - (v / max) * h }));
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-[100px] h-[24px] inline-block align-middle ml-2">
      <path d={d} fill="none" stroke="#C0C7DC" strokeWidth={1.5} strokeLinecap="round" />
      <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r={2.5} fill="#F0F2F8" stroke="#C0C7DC" strokeWidth={1} />
    </svg>
  );
};

export const SOAPNote = ({ isOpen, onClose, soapNote }: SOAPNoteProps) => {
  const patientId = usePatientStore((s) => s.patientId);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const dateStr = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  const clinicianId = patientId?.slice(0, 8).toUpperCase() ?? 'A7B2';

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
          animate={{ opacity: 1, backdropFilter: 'blur(12px)' }}
          exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/40"
          onClick={onClose}
        >
          {/* Main Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 30, rotateX: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0, rotateX: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20, transition: { duration: 0.2, ease: 'easeIn' } }}
            transition={{ type: "spring", damping: 25, stiffness: 300, mass: 0.5 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-4xl max-h-[90vh] bg-[#0A0D14] border border-[#2A2E3B] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
            style={{ boxShadow: '0 30px 60px -12px rgba(244, 162, 97, 0.15)' }}
          >
            {/* Subtle top line */}
            <div className="h-[1px] bg-gradient-to-r from-transparent via-[#8A93B2]/20 to-transparent" />

            {/* Header */}
            <div className="flex items-center justify-between px-7 py-5 border-b border-[#2A2E3B]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#2A2E3B] flex items-center justify-center">
                  <Stethoscope className="w-[18px] h-[18px] text-[#C0C7DC]" />
                </div>
                <div>
                  <h2 className="font-display font-bold text-[#F0F2F8] text-lg tracking-tight">SOAP Note — Clinical Summary</h2>
                  <p className="text-[11px] text-[#8A93B2] font-mono mt-0.5">{dateStr} · AI-Generated · Patient-Uploaded Data</p>
                </div>
              </div>
              <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8A93B2] hover:text-white hover:bg-white/5 transition-all">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* ── Scrollable Content ── */}
            <div className="overflow-y-auto px-7 py-6" style={{ maxHeight: 'calc(90vh - 170px)' }}>

              {soapNote ? (
                /* Real pipeline SOAP note — rendered as preformatted text */
                <div className="text-sm text-[#C0C7DC] leading-relaxed whitespace-pre-line mb-6">
                  {soapNote}
                </div>
              ) : (
                /* Demo content shown when no real pipeline results exist yet */
                <>
                  {/* ── SUBJECTIVE ── */}
                  <SOAPSection label="S" title="Subjective" delay={0.05}>
                    <p>
                      Patient reports an 18-month history of progressive joint pain affecting multiple joints, with a recurring
                      butterfly-pattern facial rash and persistent fatigue significantly impacting daily activities. Symptoms worsen
                      with sun exposure. Patient also reports intermittent oral ulcers and diffuse hair thinning developing over
                      the past 6 months. Self-tracked symptom journal includes 23 entries documenting joint pain episodes and
                      photographic evidence of malar rash (March 2025, June 2025).
                    </p>
                  </SOAPSection>

                  {/* ── OBJECTIVE ── */}
                  <SOAPSection label="O" title="Objective" delay={0.1}>
                    <p className="mb-4 text-[#8A93B2] text-xs font-mono uppercase tracking-wider">Laboratory Values (6 panels, Jan 2024 – Jul 2025)</p>

                    {/* Lab table */}
                    <table className="w-full text-sm mb-4">
                      <thead>
                        <tr className="border-b border-[#2A2E3B] text-[#8A93B2] text-xs font-mono uppercase">
                          <th className="text-left py-2 pr-4">Marker</th>
                          <th className="text-left py-2 pr-4">Value</th>
                          <th className="text-left py-2 pr-4">Reference Range</th>
                          <th className="text-left py-2">Trend</th>
                        </tr>
                      </thead>
                      <tbody className="text-[#C0C7DC]">
                        <tr className="border-b border-[#2A2E3B]/50">
                          <td className="py-2.5 pr-4 font-medium text-[#F0F2F8]">CRP</td>
                          <td className="py-2.5 pr-4">8.4 mg/L</td>
                          <td className="py-2.5 pr-4 text-[#8A93B2]">&lt; 3.0 mg/L</td>
                          <td className="py-2.5">↑ from 3.1 <CRPSparkline /></td>
                        </tr>
                        <tr className="border-b border-[#2A2E3B]/50">
                          <td className="py-2.5 pr-4 font-medium text-[#F0F2F8]">WBC</td>
                          <td className="py-2.5 pr-4">3,200/µL</td>
                          <td className="py-2.5 pr-4 text-[#8A93B2]">4,500–11,000/µL</td>
                          <td className="py-2.5">↓ Leukopenia</td>
                        </tr>
                        <tr className="border-b border-[#2A2E3B]/50">
                          <td className="py-2.5 pr-4 font-medium text-[#F0F2F8]">NLR</td>
                          <td className="py-2.5 pr-4">4.8</td>
                          <td className="py-2.5 pr-4 text-[#8A93B2]">1.0–3.0</td>
                          <td className="py-2.5">↑ Elevated</td>
                        </tr>
                      </tbody>
                    </table>

                    <p>
                      <strong className="text-[#F0F2F8]">Visual evidence:</strong> Bilateral malar erythema consistent with butterfly rash distribution;
                      localized joint edema noted in metacarpophalangeal (MCP) joints. Photo analysis via dermatology classification model
                      returned 87% confidence for malar rash pattern.
                    </p>
                  </SOAPSection>

                  {/* ── ASSESSMENT ── */}
                  <SOAPSection label="A" title="Assessment" delay={0.15}>
                    <p className="mb-4">
                      Multi-modal pattern analysis indicates a <strong className="text-[#F0F2F8]">92% alignment</strong> with a systemic autoimmune
                      profile. Secondary literature comparison flags <strong className="text-[#F0F2F8]">65% similarity</strong> to Systemic Lupus
                      Erythematosus (SLE) based on cosine similarity against canonical SLE profiles from 2,400+ confirmed cases.
                      Patient meets <strong className="text-[#F0F2F8]">7 of 11 ACR/EULAR 2019 criteria</strong> (score: 14; classification threshold ≥10).
                    </p>

                    <p className="mb-4">
                      The combination of sustained CRP elevation, leukopenia, malar rash, arthralgia, and photosensitivity presents a
                      clinical picture warranting immediate rheumatologic evaluation. Differential considerations include Rheumatoid
                      Arthritis (41% similarity), Sjögren's Syndrome (38%), and Mixed Connective Tissue Disease (29%).
                    </p>

                    {/* Citations */}
                    <div className="p-3.5 rounded-lg bg-[#1A1D26] border border-[#2A2E3B]">
                      <p className="text-[10px] font-mono uppercase tracking-wider text-[#8A93B2] mb-2">Supporting Literature</p>
                      <ol className="text-xs text-[#8A93B2] space-y-1 list-decimal list-inside">
                        <li>ACR/EULAR 2019 Classification Criteria for SLE — <em>Arthritis & Rheumatology</em>, Vol 71, No 9</li>
                        <li>Sustained CRP elevation with localized erythema in autoimmune escalation — <em>J Clin Rheumatol</em>, 2024</li>
                        <li>Leukopenia with elevated NLR as predictive marker in early SLE — <em>Lupus</em>, 2023</li>
                      </ol>
                    </div>
                  </SOAPSection>

                  {/* ── PLAN ── */}
                  <SOAPSection label="P" title="Plan" delay={0.2} last>
                    <p className="mb-4">
                      Based on the above findings, the following actions are recommended for clinical consideration:
                    </p>
                    <ol className="space-y-3 list-decimal list-inside text-[#C0C7DC]">
                      <li>
                        <strong className="text-[#F0F2F8]">Rheumatology referral (urgent)</strong> — Order ANA with titer and pattern,
                        anti-dsDNA antibodies, and complement levels (C3, C4). The sustained CRP trend and leukopenia, combined
                        with 7/11 ACR/EULAR criteria, support prioritizing this evaluation.
                      </li>
                      <li>
                        <strong className="text-[#F0F2F8]">Dermatology consult</strong> — Consider punch biopsy of malar rash if persistent,
                        to differentiate lupus-specific from nonspecific cutaneous involvement and establish histopathologic evidence.
                      </li>
                      <li>
                        <strong className="text-[#F0F2F8]">Renal function screening</strong> — Urinalysis with microscopy and serum creatinine
                        to rule out early lupus nephritis, given the systemic inflammatory burden demonstrated by lab trends.
                      </li>
                      <li>
                        <strong className="text-[#F0F2F8]">Follow-up in 4 weeks</strong> — Repeat CBC with differential and CRP to monitor
                        inflammatory trajectory. If NLR continues to rise or WBC drops further, consider expedited workup.
                      </li>
                    </ol>
                  </SOAPSection>
                </>
              )}

              {/* Disclaimer */}
              <div className="flex items-start gap-3 p-4 rounded-xl bg-[#1A1D26] border border-[#2A2E3B] mt-6">
                <AlertTriangle className="w-4 h-4 text-[#8A93B2]/50 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[#8A93B2] leading-relaxed">
                  This note is <strong className="text-[#C0C7DC]">AI-generated</strong> from patient-uploaded lab results, photos, and symptom journals.
                  It is intended as a structured conversation starter and does not constitute a clinical diagnosis. All findings,
                  scores, and recommendations require independent physician verification in the context of a complete medical history and examination.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="px-7 py-4 border-t border-[#2A2E3B] flex items-center justify-between">
              <a
                href={`/clinician/${clinicianId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-xs text-[#8A93B2] hover:text-[#C0C7DC] transition-colors"
              >
                <QrCode className="w-3.5 h-3.5" />
                Clinician Verification Portal
                <ExternalLink className="w-3 h-3" />
              </a>
              <button className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-[#2A2E3B] text-[#F0F2F8] border border-[#3A3F4D] hover:bg-[#3A3F4D] transition-all">
                <Download className="w-4 h-4" />
                Download PDF
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

/* ── SOAP section with letter label ── */
const SOAPSection = ({ label, title, delay, children, last }: {
  label: string; title: string; delay: number; children: React.ReactNode; last?: boolean;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className={last ? '' : 'mb-6 pb-6 border-b border-[#2A2E3B]/60'}
  >
    <div className="flex items-baseline gap-3 mb-3">
      <span className="text-lg font-mono font-bold text-[#F0F2F8]">{label}</span>
      <span className="text-[11px] font-mono uppercase tracking-widest text-[#8A93B2]">{title}</span>
    </div>
    <div className="text-sm text-[#C0C7DC] leading-relaxed">
      {children}
    </div>
  </motion.div>
);