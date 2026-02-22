import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Printer, QrCode, ExternalLink } from 'lucide-react';

interface SOAPNoteProps {
  isOpen: boolean;
  onClose: () => void;
}

/* -- Inline sparkline -- */
const Sparkline = ({ data, color = '#374151' }: { data: number[]; color?: string }) => {
  const max = Math.max(...data), min = Math.min(...data);
  const w = 80, h = 20;
  const pts = data.map((v, i) => ({
    x: (i / (data.length - 1)) * w,
    y: h - ((v - min) / (max - min || 1)) * h,
  }));
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ display: 'inline-block', verticalAlign: 'middle', width: 56, height: 14 }}>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r={2} fill={color} />
    </svg>
  );
};

export const SOAPNote = ({ isOpen, onClose }: SOAPNoteProps) => {
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const handlePrint = () => {
    const content = printRef.current;
    if (!content) return;
    const win = window.open('', '_blank', 'width=900,height=1200');
    if (!win) return;
    win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"/><title>AuRA Clinical Summary</title><style>
      *{box-sizing:border-box;margin:0;padding:0}
      body{font-family:'Times New Roman',Times,serif;font-size:11pt;color:#111;background:#fff;padding:0}
      .page{max-width:7.5in;margin:0 auto;padding:0.75in 0.85in}
      h2{font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;border-bottom:1px solid #111;padding-bottom:3pt;margin-bottom:8pt;margin-top:18pt}
      p{line-height:1.55;margin-bottom:6pt}
      table{width:100%;border-collapse:collapse;font-size:9.5pt;margin-bottom:8pt}
      th{text-align:left;font-weight:700;border-bottom:1.5px solid #111;padding:3pt 6pt 3pt 0;font-size:8pt;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.07em}
      td{padding:3.5pt 6pt 3.5pt 0;border-bottom:0.5px solid #e5e7eb;vertical-align:top}
      ol{padding-left:16pt}
      li{margin-bottom:6pt;line-height:1.55}
      @media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
    </style></head><body><div class="page">${content.innerHTML}</div></body></html>`);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 400);
  };

  const dateStr = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  const reportId = 'AUR-' + Math.random().toString(36).substring(2, 8).toUpperCase();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -12, transition: { duration: 0.18 } }}
            transition={{ type: 'spring', damping: 26, stiffness: 320, mass: 0.5 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-3xl max-h-[92vh] bg-[#1A1D26] border border-[#2A2E3B] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Modal chrome */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2E3B] shrink-0">
              <div>
                <p className="text-sm font-semibold text-[#F0F2F8]">Clinical Summary — SOAP Note</p>
                <p className="text-[11px] text-[#8A93B2] mt-0.5">Print or save as PDF to bring to your appointment · {dateStr}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrint}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-white text-[#111] hover:bg-gray-100 transition-all"
                >
                  <Printer className="w-4 h-4" />
                  Print / Save PDF
                </button>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[#8A93B2] hover:text-white hover:bg-white/5 transition-all"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Scrollable paper preview */}
            <div className="overflow-y-auto flex-1 bg-[#0D1017] p-6">

              {/* White paper */}
              <div
                ref={printRef}
                className="bg-white text-[#111] max-w-2xl mx-auto shadow-2xl"
                style={{ fontFamily: "'Times New Roman', Times, serif", fontSize: '10.5pt', lineHeight: 1.55, padding: '0.75in 0.85in' }}
              >
                {/* Letterhead */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '2px solid #111', paddingBottom: '10pt', marginBottom: '12pt' }}>
                  <div>
                    <div style={{ fontSize: '15pt', fontWeight: 700, letterSpacing: '0.02em', fontFamily: 'Arial, sans-serif' }}>AuRA</div>
                    <div style={{ fontSize: '8pt', color: '#555', fontFamily: 'Arial, sans-serif', marginTop: '2pt' }}>Clinical Intelligence Platform · aura-health.io</div>
                  </div>
                  <div style={{ textAlign: 'right', fontFamily: 'Arial, sans-serif' }}>
                    <div style={{ fontSize: '8.5pt', fontWeight: 700, color: '#b91c1c', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Confidential — Physician Use Only</div>
                    <div style={{ fontSize: '8pt', color: '#555', marginTop: '2pt' }}>Report ID: {reportId}</div>
                    <div style={{ fontSize: '8pt', color: '#555' }}>Generated: {dateStr}</div>
                  </div>
                </div>

                {/* Patient metadata grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8pt', marginBottom: '14pt', fontFamily: 'Arial, sans-serif' }}>
                  {[
                    { label: 'Patient', value: 'Jane D. (de-identified)' },
                    { label: 'DOB', value: 'Mar 14, 1991 · F' },
                    { label: 'Data Range', value: 'Jan 2024 – Jul 2025' },
                    { label: 'Panels Uploaded', value: '6 CBC/CMP · 2 ANA' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '2pt' }}>
                      <span style={{ fontSize: '7pt', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#777' }}>{label}</span>
                      <span style={{ fontSize: '9.5pt', fontWeight: 600 }}>{value}</span>
                    </div>
                  ))}
                </div>

                {/* S — Subjective */}
                <PrintSection label="S" title="Subjective">
                  <p>
                    Patient is a 34-year-old female presenting with an 18-month longitudinal self-reported symptom record comprising
                    polyarthralgia (bilateral MCP, PIP, and ankle joints), chronic fatigue with exertional intolerance, and photosensitive
                    malar rash documented via serial photographs (March 2025, June 2025). Additional reported symptoms include recurrent
                    oral ulcerations (non-scarring oral mucosa), diffuse non-scarring alopecia progressive over 6 months, and intermittent
                    bilateral lower-extremity edema. Symptom journal contains 23 time-stamped entries with standardized VAS scoring
                    (mean pain VAS: 6.4/10; mean fatigue VAS: 7.1/10). No prior rheumatologic evaluation. No current immunosuppressive
                    or biologic therapy. Family history: maternal aunt with RA; no known lupus family history.
                  </p>
                </PrintSection>

                {/* O — Objective */}
                <PrintSection label="O" title="Objective">
                  <p style={{ fontSize: '7.5pt', fontFamily: 'Arial, sans-serif', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#666', marginBottom: '6pt' }}>
                    Laboratory Values — Serial CBC / CMP / Immunologic Panel (18-month trend, 6 draws)
                  </p>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '9.5pt', marginBottom: '10pt' }}>
                    <thead>
                      <tr>
                        {['Marker', 'Most Recent', 'Reference Range', 'Status', '18-mo Trend'].map(h => (
                          <th key={h} style={{ textAlign: 'left', fontWeight: 700, borderBottom: '1.5px solid #111', padding: '3pt 5pt 3pt 0', fontSize: '7.5pt', fontFamily: 'Arial, sans-serif', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { marker: 'CRP (C-Reactive Protein)', val: '14.1 mg/L', ref: '< 3.0 mg/L', status: '↑ HIGH', statusColor: '#b91c1c', data: [3.1, 4.2, 5.7, 8.4, 11.2, 14.1] },
                        { marker: 'WBC (Leukocytes)', val: '2.8 × 10⁹/L', ref: '4.5–11.0 × 10⁹/L', status: '↓ Leukopenia', statusColor: '#1d4ed8', data: [5.2, 4.8, 4.1, 3.6, 3.1, 2.8] },
                        { marker: 'ANA Titer (IFA)', val: '1:640 (homogeneous)', ref: '< 1:80', status: '↑ HIGH', statusColor: '#b91c1c', data: [1, 1, 2, 3, 5, 8] },
                        { marker: 'NLR', val: '4.8', ref: '1.0–3.0', status: '↑ Elevated', statusColor: '#b91c1c', data: [1.8, 2.1, 2.8, 3.5, 4.1, 4.8] },
                        { marker: 'ESR (Westergren)', val: '68 mm/hr', ref: '0–20 mm/hr', status: '↑ HIGH', statusColor: '#b91c1c', data: [18, 24, 32, 45, 58, 68] },
                        { marker: 'Complement C3', val: '62 mg/dL', ref: '90–180 mg/dL', status: '↓ LOW', statusColor: '#1d4ed8', data: [112, 98, 88, 79, 70, 62] },
                        { marker: 'Complement C4', val: '8 mg/dL', ref: '16–47 mg/dL', status: '↓ LOW', statusColor: '#1d4ed8', data: [24, 20, 16, 13, 10, 8] },
                        { marker: 'Platelets', val: '118 × 10⁹/L', ref: '150–400 × 10⁹/L', status: '↓ Thrombocytopenia', statusColor: '#1d4ed8', data: [210, 185, 162, 144, 129, 118] },
                      ].map(({ marker, val, ref, status, statusColor, data }) => (
                        <tr key={marker} style={{ borderBottom: '0.5px solid #e5e7eb' }}>
                          <td style={{ padding: '3pt 5pt 3pt 0', fontWeight: 600 }}>{marker}</td>
                          <td style={{ padding: '3pt 5pt 3pt 0' }}>{val}</td>
                          <td style={{ padding: '3pt 5pt 3pt 0', color: '#6b7280', fontSize: '9pt' }}>{ref}</td>
                          <td style={{ padding: '3pt 5pt 3pt 0', color: statusColor, fontWeight: 700, fontSize: '8.5pt', whiteSpace: 'nowrap' }}>{status}</td>
                          <td style={{ padding: '3pt 0 3pt 0' }}><Sparkline data={data} color={statusColor} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p>
                    <strong>Dermatologic imaging analysis:</strong> Serial patient-uploaded photographs processed via convolutional
                    classification model (ResNet-50; trained on 14,200 labeled dermatology images). Output: <strong>87.3% posterior probability
                    of malar rash</strong> consistent with butterfly distribution (bilateral malar eminences, sparing nasolabial folds).
                    No scarring or atrophy. Joint photographs demonstrate bilateral MCP swelling with preserved range of motion; no gross
                    synovial hypertrophy on visual inspection.
                  </p>
                </PrintSection>

                {/* A — Assessment */}
                <PrintSection label="A" title="Assessment">
                  <p>
                    Multi-modal algorithmic analysis (AuRA pipeline: time-series lab clustering + NLP symptom encoding + image
                    classification) yields a <strong>composite autoimmune similarity score of 0.92</strong> (z-score: +3.4 SD above
                    population mean; reference cohort n = 2,847 confirmed autoimmune cases; ImmPort SDY824 + NHANES).
                  </p>

                  <p style={{ marginTop: '7pt' }}>
                    <strong>ACR/EULAR 2019 SLE Classification Criteria</strong> (Aringer et al., <em>Arthritis &amp; Rheumatology</em> 2019;71:1400)
                    — ANA entry criterion satisfied (≥1:80). Weighted domain score: <strong>14 points</strong> (classification threshold ≥10).
                  </p>

                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '9pt', margin: '5pt 0 10pt 0' }}>
                    <thead>
                      <tr>
                        {['Domain', 'Criterion', 'Wt.', 'Status'].map(h => (
                          <th key={h} style={{ textAlign: 'left', fontWeight: 700, borderBottom: '1.5px solid #111', padding: '2.5pt 5pt 2.5pt 0', fontSize: '7.5pt', fontFamily: 'Arial, sans-serif', textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { domain: 'Mucocutaneous', criterion: 'Non-scarring alopecia', weight: '+2', met: true },
                        { domain: 'Mucocutaneous', criterion: 'Oral ulcers', weight: '+2', met: true },
                        { domain: 'Mucocutaneous', criterion: 'Malar rash (ACLE)', weight: '+4', met: true },
                        { domain: 'Musculoskeletal', criterion: 'Synovitis ≥2 joints', weight: '+6', met: true },
                        { domain: 'Hematologic', criterion: 'Leukopenia (WBC < 4×10⁹/L)', weight: '+3', met: true },
                        { domain: 'Hematologic', criterion: 'Thrombocytopenia (< 100×10⁹/L)', weight: '+4', met: false },
                        { domain: 'Complement', criterion: 'Low C3 and/or C4', weight: '+4', met: true },
                        { domain: 'Immunologic', criterion: 'ANA ≥1:80 (entry criterion)', weight: 'Entry', met: true },
                        { domain: 'Immunologic', criterion: 'Anti-dsDNA (not yet tested)', weight: '+6', met: false },
                        { domain: 'Renal', criterion: 'Proteinuria (not yet assessed)', weight: '+4', met: false },
                      ].map(({ domain, criterion, weight, met }) => (
                        <tr key={criterion} style={{ borderBottom: '0.5px solid #e5e7eb', background: met ? '#f0fdf4' : 'transparent' }}>
                          <td style={{ padding: '2.5pt 5pt 2.5pt 0', color: '#6b7280', fontStyle: 'italic', fontSize: '8.5pt' }}>{domain}</td>
                          <td style={{ padding: '2.5pt 5pt 2.5pt 0' }}>{criterion}</td>
                          <td style={{ padding: '2.5pt 5pt 2.5pt 0', fontWeight: 700, fontFamily: 'Arial, sans-serif' }}>{weight}</td>
                          <td style={{ padding: '2.5pt 0 2.5pt 0', fontWeight: 700, color: met ? '#15803d' : '#9ca3af', fontSize: '8.5pt' }}>{met ? '✓ Met' : '— Pending'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p><strong>Differential diagnosis — cosine similarity vs. canonical profiles:</strong></p>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '9pt', margin: '5pt 0 8pt 0' }}>
                    <thead>
                      <tr>
                        {['Condition', 'Score', 'Key Discriminators / Gaps'].map(h => (
                          <th key={h} style={{ textAlign: 'left', fontWeight: 700, borderBottom: '1.5px solid #111', padding: '2.5pt 5pt 2.5pt 0', fontSize: '7.5pt', fontFamily: 'Arial, sans-serif', textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { condition: 'Systemic Lupus Erythematosus (SLE)', score: '0.65', note: 'Malar rash, ANA high-titer, complement consumption, leukopenia, ACR criteria score 14', bold: true },
                        { condition: 'Rheumatoid Arthritis (RA)', score: '0.41', note: 'Polyarthralgia, elevated CRP; RF/anti-CCP not tested; no erosive joint findings to date', bold: false },
                        { condition: "Sjögren's Syndrome", score: '0.38', note: 'ANA+; sicca symptoms not formally assessed; anti-Ro/SSA pending', bold: false },
                        { condition: 'MCTD', score: '0.29', note: 'Overlap features present; anti-U1 RNP antibody not yet ordered', bold: false },
                        { condition: 'Undifferentiated CTD', score: '0.22', note: 'Fallback if specific antibody workup negative; requires longitudinal follow-up', bold: false },
                      ].map(({ condition, score, note, bold }) => (
                        <tr key={condition} style={{ borderBottom: '0.5px solid #e5e7eb' }}>
                          <td style={{ padding: '3pt 5pt 3pt 0', fontWeight: bold ? 700 : 400 }}>{condition}</td>
                          <td style={{ padding: '3pt 5pt 3pt 0', fontWeight: bold ? 700 : 400, fontFamily: 'Arial, sans-serif', whiteSpace: 'nowrap' }}>{score}</td>
                          <td style={{ padding: '3pt 0 3pt 0', color: '#6b7280', fontSize: '8.5pt' }}>{note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p style={{ fontSize: '8.5pt', color: '#6b7280', fontStyle: 'italic', fontFamily: 'Arial, sans-serif' }}>
                    References: [1] Aringer M et al., ACR/EULAR 2019 SLE Criteria, <em>Arthritis Rheum.</em> 71:1400–1412.
                    [2] Tsokos GC, SLE pathogenesis, <em>Nat Rev Rheumatol.</em> 2022;18:593–610.
                    [3] Al-Herz et al., hypocomplementemia in SLE, <em>Lupus</em> 2023;32:487–496.
                    [4] Shen N et al., NLR as SLE biomarker, <em>J Autoimmun.</em> 2024;143:103155.
                  </p>
                </PrintSection>

                {/* P — Plan */}
                <PrintSection label="P" title="Plan" last>
                  <ol style={{ paddingLeft: '16pt', margin: 0 }}>
                    {[
                      {
                        title: 'Urgent Rheumatology Referral',
                        body: 'Formal evaluation per ACR/EULAR 2019 criteria. Recommended antibody panel: anti-dsDNA (quantitative ELISA), anti-Sm, anti-Ro/SSA, anti-La/SSB, anti-U1 RNP, antiphospholipid antibodies (aCL IgG/IgM, anti-β2GPI, lupus anticoagulant). Repeat ANA by IFA with pattern specification. Complement CH50 if C3/C4 borderline.',
                      },
                      {
                        title: 'Renal Screening',
                        body: 'Urinalysis with microscopy (RBC casts, granular casts), spot urine protein-to-creatinine ratio, and serum creatinine/eGFR baseline to exclude early lupus nephritis (Class III/IV). If proteinuria ≥500 mg/24h or active urinary sediment, expedite nephrology co-management.',
                      },
                      {
                        title: 'Dermatology Consultation',
                        body: '4 mm punch biopsy of active malar lesion for H&E and direct immunofluorescence (DIF) to characterize interface dermatitis and lupus band (IgG/IgM/C3 deposition at DEJ). Differentiates ACLE from rosacea or seborrheic dermatitis.',
                      },
                      {
                        title: 'Additional Hematologic Workup',
                        body: 'Direct antiglobulin test (DAT/Coombs) given mild thrombocytopenia. Peripheral blood smear with manual differential. TSH and anti-TPO to exclude Hashimoto thyroiditis overlap. Serum ferritin and LDH as inflammatory markers.',
                      },
                      {
                        title: 'Repeat Surveillance CBC / CRP (4 Weeks)',
                        body: 'Monitor CBC with differential, CRP, ESR, and C3/C4. If WBC < 2.5 × 10⁹/L or platelets < 100 × 10⁹/L, expedite hematology co-management. CRP and NLR trajectory inform timing of hydroxychloroquine initiation (rheumatologist discretion). Baseline ophthalmology fundus exam prior to hydroxychloroquine if prescribed.',
                      },
                    ].map(({ title, body }, i) => (
                      <li key={i} style={{ marginBottom: '8pt', lineHeight: 1.55 }}>
                        <strong>{title}.</strong> {body}
                      </li>
                    ))}
                  </ol>
                </PrintSection>

                {/* Signature block */}
                <div style={{ marginTop: '28pt', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ borderTop: '1px solid #111', width: '200pt', marginBottom: '3pt' }} />
                    <div style={{ fontSize: '8pt', fontFamily: 'Arial, sans-serif', color: '#555' }}>Receiving Physician Signature &amp; Date</div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '8pt', fontFamily: 'Arial, sans-serif', color: '#888' }}>
                    <div>AuRA Report · {reportId}</div>
                    <div style={{ marginTop: '2pt' }}><a href="/clinician/A7B2" style={{ color: '#555' }}>aura-health.io/verify/{reportId}</a></div>
                  </div>
                </div>

                {/* Disclaimer */}
                <div style={{ borderTop: '1px solid #ccc', marginTop: '16pt', paddingTop: '8pt', fontSize: '7pt', color: '#6b7280', fontFamily: 'Arial, sans-serif', lineHeight: 1.5 }}>
                  <strong style={{ color: '#374151' }}>DISCLAIMER:</strong> This report is AI-generated from patient-uploaded laboratory results,
                  photographs, and self-reported symptom data via the AuRA Clinical Intelligence Platform. It is intended solely as a
                  structured pre-consultation aid for licensed medical professionals and does not constitute a clinical diagnosis, prognosis,
                  or treatment plan. All findings, similarity scores, differential diagnoses, and clinical recommendations require independent
                  physician verification within the context of a complete medical history and physical examination. AuRA bears no liability
                  for any clinical decisions predicated on this document.
                </div>

              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-[#2A2E3B] flex items-center justify-between shrink-0">
              <a
                href="/clinician/A7B2"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-xs text-[#8A93B2] hover:text-[#C0C7DC] transition-colors"
              >
                <QrCode className="w-3.5 h-3.5" />
                Clinician Verification Portal
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

/* -- Print section with bold letter label -- */
const PrintSection = ({ label, title, children, last }: {
  label: string; title: string; children: React.ReactNode; last?: boolean;
}) => (
  <div style={{ marginBottom: last ? 0 : '16pt', paddingBottom: last ? 0 : '12pt', borderBottom: last ? 'none' : '1px solid #e5e7eb' }}>
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '10pt', borderBottom: '1.5px solid #111', paddingBottom: '3pt', marginBottom: '8pt' }}>
      <span style={{ fontSize: '13pt', fontWeight: 700, fontFamily: 'Arial, sans-serif', minWidth: '14pt' }}>{label}</span>
      <span style={{ fontSize: '7.5pt', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', fontFamily: 'Arial, sans-serif', color: '#374151' }}>{title}</span>
    </div>
    <div style={{ fontSize: '10.5pt', lineHeight: 1.6, color: '#111' }}>
      {children}
    </div>
  </div>
);
