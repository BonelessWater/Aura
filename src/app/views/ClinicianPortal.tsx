import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts';
import {
  ShieldCheck, FileText, ExternalLink, X, ChevronDown,
  ChevronRight, ThumbsUp, Minus, ThumbsDown, Send, Printer,
  QrCode,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useParams } from 'react-router';

/* ---------- Types ---------- */
interface Citation {
  id: string;
  text: string;
  doi: string;
  abstract: string;
  highlightStart: number;
  highlightEnd: number;
}

/* ---------- Mock data ---------- */
const radarConditions = [
  {
    name: 'ME/CFS (SEID)',
    color: '#7B61FF',
    data: [
      { criterion: 'PEM', score: 92 },
      { criterion: 'Fatigue > 6mo', score: 88 },
      { criterion: 'Cognitive', score: 76 },
      { criterion: 'Orthostatic', score: 85 },
      { criterion: 'Sleep Dysfunction', score: 72 },
      { criterion: 'Immune Markers', score: 58 },
    ],
  },
  {
    name: 'Fibromyalgia',
    color: '#F4A261',
    data: [
      { criterion: 'PEM', score: 45 },
      { criterion: 'Fatigue > 6mo', score: 80 },
      { criterion: 'Cognitive', score: 60 },
      { criterion: 'Orthostatic', score: 30 },
      { criterion: 'Sleep Dysfunction', score: 85 },
      { criterion: 'Immune Markers', score: 25 },
    ],
  },
  {
    name: 'POTS',
    color: '#2563EB',
    data: [
      { criterion: 'PEM', score: 55 },
      { criterion: 'Fatigue > 6mo', score: 60 },
      { criterion: 'Cognitive', score: 50 },
      { criterion: 'Orthostatic', score: 95 },
      { criterion: 'Sleep Dysfunction', score: 40 },
      { criterion: 'Immune Markers', score: 20 },
    ],
  },
];

const combinedRadarData = radarConditions[0].data.map((item, i) => ({
  criterion: item.criterion,
  'ME/CFS (SEID)': item.score,
  Fibromyalgia: radarConditions[1].data[i].score,
  POTS: radarConditions[2].data[i].score,
}));

const soapSections = [
  {
    title: 'Subjective',
    content: `Patient reports a 6-month history of debilitating fatigue following a viral illness (likely COVID-19, confirmed via PCR Jan 2025). Key symptoms include post-exertional malaise (PEM), orthostatic intolerance, and cognitive dysfunction ("brain fog"). Severity score: 8/10 on bad days. Reports inability to work >4 hours/day.`,
  },
  {
    title: 'Objective',
    items: [
      'Heart Rate Variability (HRV): Consistently low (20-30ms) via wearable data',
      'Orthostatic Vitals: HR increase of +35bpm upon standing (POTS pattern)',
      'Sleep Efficiency: 65% (fragmented) based on wearable data export',
      'EBV IgG: Elevated (>750 U/mL), suggesting reactivation',
      'CBC: Within normal limits; CRP mildly elevated (4.2 mg/L)',
    ],
  },
  {
    title: 'Assessment',
    content: `Presentation is consistent with criteria for Systemic Exertion Intolerance Disease (SEID) / ME/CFS per IOM 2015 criteria. Comorbid postural orthostatic tachycardia syndrome (POTS) suspected. Differential diagnosis should exclude thyroid dysfunction, anemia, and autoimmune conditions.`,
    citations: [
      {
        id: 'doi-1',
        text: 'Institute of Medicine (2015). Beyond ME/CFS: Redefining an Illness.',
        doi: '10.17226/19012',
        abstract: `The committee reviewed the evidence on ME/CFS and concluded that ME/CFS is a serious, chronic, complex, multisystem disease that frequently and dramatically limits the activities of affected patients. The hallmark symptom is post-exertional malaise (PEM), which is defined as a worsening of a patient's symptoms and function after exposure to physical or cognitive stressors that were previously tolerated. The committee proposed new diagnostic criteria that focus on the core symptoms of the disease: a substantial reduction in activity, post-exertional malaise, and unrefreshing sleep.`,
        highlightStart: 142,
        highlightEnd: 380,
      },
      {
        id: 'doi-2',
        text: 'Komaroff AL (2021). Advances in Understanding ME/CFS. JAMA.',
        doi: '10.1001/jama.2021.1',
        abstract: `This review summarizes advances in understanding the pathobiology of ME/CFS. Evidence supports the involvement of neuroinflammation, autoimmunity, and metabolic dysfunction. EBV reactivation has been identified as a common trigger, with elevated IgG titers correlating with symptom severity in a subset of patients. Orthostatic intolerance, particularly POTS, is now recognized as a common comorbidity.`,
        highlightStart: 185,
        highlightEnd: 360,
      },
    ],
  },
  {
    title: 'Plan',
    items: [
      'Referral to Rheumatology/Neurology for further workup',
      'Tilt Table Test to confirm POTS diagnosis',
      'Trial of low-dose Naltrexone (LDN) consideration',
      'Pacing strategy implementation to manage PEM',
      'Follow-up in 4 weeks with repeat labs (CRP, EBV)',
    ],
  },
];

const pdfPages = [
  {
    title: 'Complete Blood Count (CBC)',
    rows: [
      { label: 'WBC', value: '6.2', unit: '10^3/uL', range: '4.5-11.0', status: 'normal' },
      { label: 'RBC', value: '4.8', unit: '10^6/uL', range: '4.7-6.1', status: 'normal' },
      { label: 'Hemoglobin', value: '14.2', unit: 'g/dL', range: '14.0-18.0', status: 'normal' },
      { label: 'Hematocrit', value: '42.5', unit: '%', range: '40-54', status: 'normal' },
      { label: 'Platelets', value: '265', unit: '10^3/uL', range: '150-400', status: 'normal' },
    ],
  },
  {
    title: 'Inflammatory Markers',
    rows: [
      { label: 'CRP', value: '4.2', unit: 'mg/L', range: '0-3.0', status: 'high' },
      { label: 'ESR', value: '18', unit: 'mm/hr', range: '0-20', status: 'normal' },
      { label: 'Ferritin', value: '95', unit: 'ng/mL', range: '20-250', status: 'normal' },
    ],
  },
  {
    title: 'Viral Panel',
    rows: [
      { label: 'EBV IgG', value: '752', unit: 'U/mL', range: '0-20', status: 'high' },
      { label: 'EBV IgM', value: '<10', unit: 'U/mL', range: '0-40', status: 'normal' },
      { label: 'CMV IgG', value: '15', unit: 'AU/mL', range: '0-6', status: 'high' },
    ],
  },
];

/* ---------- Sub-components ---------- */

const CitationSidePanel = ({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) => {
  if (!citation) return null;
  const { abstract, highlightStart, highlightEnd, text, doi } = citation;

  const before = abstract.slice(0, highlightStart);
  const highlighted = abstract.slice(highlightStart, highlightEnd);
  const after = abstract.slice(highlightEnd);

  return (
    <motion.div
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="fixed inset-y-0 right-0 w-full max-w-lg bg-white border-l border-gray-200 shadow-2xl z-50 overflow-y-auto"
    >
      <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Source Abstract</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      <div className="p-6 space-y-4">
        <div>
          <p className="text-sm font-medium text-gray-900 mb-1">{text}</p>
          <p className="text-xs text-blue-600 font-mono">DOI: {doi}</p>
        </div>

        <div className="h-px bg-gray-100" />

        <div className="text-sm text-gray-700 leading-relaxed">
          {before}
          <mark className="bg-[#FFF59D] px-0.5 rounded">{highlighted}</mark>
          {after}
        </div>
      </div>
    </motion.div>
  );
};

const LabTable = ({ page }: { page: (typeof pdfPages)[number] }) => (
  <div className="mb-6">
    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
      {page.title}
    </h4>
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200">
          <th className="text-left py-2 text-gray-500 font-medium">Test</th>
          <th className="text-right py-2 text-gray-500 font-medium">Result</th>
          <th className="text-right py-2 text-gray-500 font-medium">Unit</th>
          <th className="text-right py-2 text-gray-500 font-medium">Reference</th>
        </tr>
      </thead>
      <tbody>
        {page.rows.map((row) => (
          <tr key={row.label} className="border-b border-gray-50">
            <td className="py-2.5 text-gray-900 font-medium">{row.label}</td>
            <td
              className={clsx(
                'py-2.5 text-right font-mono',
                row.status === 'high'
                  ? 'text-red-600 font-semibold'
                  : 'text-gray-700'
              )}
            >
              {row.value}
              {row.status === 'high' && ' H'}
            </td>
            <td className="py-2.5 text-right text-gray-500">{row.unit}</td>
            <td className="py-2.5 text-right text-gray-400 font-mono text-xs">{row.range}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/* ---------- Main Component ---------- */
export const ClinicianPortal = () => {
  const { id } = useParams();
  const patientId = id || 'A7B2';

  const [activeCitation, setActiveCitation] = useState<string | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const allCitations: Citation[] = soapSections.flatMap((s) =>
    'citations' in s && s.citations ? s.citations : []
  );
  const activeCitationData = allCitations.find((c) => c.id === activeCitation);

  const handleFeedback = (type: string) => {
    setFeedbackGiven(type);
  };

  const handleFeedbackSubmit = () => {
    setFeedbackSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#111111]" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Top Banner */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-gradient-to-br from-[#7B61FF] to-[#2563EB] flex items-center justify-center">
                <span className="text-white text-xs font-mono font-bold">A</span>
              </div>
              <span className="text-sm font-semibold text-gray-900 tracking-wide">
                Aura <span className="text-gray-400 font-normal">Clinician View</span>
              </span>
            </div>

            <div className="hidden md:flex items-center gap-4 text-xs text-gray-500">
              <span className="font-mono">Patient #{patientId}</span>
              <span className="w-px h-4 bg-gray-200" />
              <span>{new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#2E7D32]/10 border border-[#2E7D32]/20">
              <ShieldCheck className="w-3.5 h-3.5 text-[#2E7D32]" />
              <span className="text-xs font-medium text-[#2E7D32]">Verified by Aura RAG Engine</span>
            </div>
            <button
              onClick={() => window.print()}
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
              title="Print"
            >
              <Printer className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Split Pane */}
      <div className="max-w-[1400px] mx-auto flex flex-col lg:flex-row min-h-[calc(100vh-57px)]">
        {/* Left Column: Source Data */}
        <div className="lg:w-1/2 border-r border-gray-200 bg-white overflow-y-auto">
          <div className="px-6 py-5 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              Source Data — Lab Results
            </h2>
            <p className="text-xs text-gray-400 mt-1 font-mono">
              Uploaded Jan 15, 2026 &middot; 3 panels
            </p>
          </div>

          <div className="p-6">
            {pdfPages.map((page) => (
              <LabTable key={page.title} page={page} />
            ))}

            {/* Mock PDF rendering indicator */}
            <div className="mt-8 p-4 rounded-lg bg-gray-50 border border-gray-100 text-center">
              <p className="text-xs text-gray-400">
                Original PDF rendered inline. Scroll for all pages.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Analysis */}
        <div className="lg:w-1/2 overflow-y-auto bg-[#F8F9FA]">
          <div className="px-6 py-5 border-b border-gray-100 bg-white">
            <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              Generated SOAP Note
            </h2>
          </div>

          <div className="p-6 space-y-6">
            {soapSections.map((section) => (
              <div key={section.title} className="bg-white rounded-lg border border-gray-200 p-5">
                <h3 className="text-xs uppercase tracking-wider font-semibold text-gray-400 mb-3 pb-2 border-b border-gray-100">
                  {section.title}
                </h3>

                {'content' in section && section.content && (
                  <p className="text-sm text-gray-800 leading-relaxed">{section.content}</p>
                )}

                {'items' in section && section.items && (
                  <ol className="text-sm text-gray-800 leading-relaxed space-y-1.5 list-decimal list-inside">
                    {section.items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ol>
                )}

                {'citations' in section && section.citations && (
                  <div className="mt-4 p-4 bg-blue-50/80 border border-blue-100 rounded-lg space-y-2">
                    <p className="text-xs font-semibold text-blue-800 mb-2">Citations:</p>
                    {section.citations.map((cit, i) => (
                      <button
                        key={cit.id}
                        onClick={() => setActiveCitation(cit.id)}
                        className="flex items-start gap-2 text-left w-full group"
                      >
                        <span className="text-xs text-blue-500 font-mono mt-0.5">[{i + 1}]</span>
                        <span className="text-xs text-blue-700 group-hover:text-blue-900 group-hover:underline transition-colors">
                          {cit.text}
                        </span>
                        <ExternalLink className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* Radar Chart — Confidence Breakdown */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h3 className="text-xs uppercase tracking-wider font-semibold text-gray-400 mb-2 pb-2 border-b border-gray-100">
                Confidence Breakdown — Diagnostic Criteria Mapping
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Patient symptoms mapped against diagnostic criteria for top 3 suspected conditions.
              </p>

              <div className="w-full h-[340px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={combinedRadarData} cx="50%" cy="50%" outerRadius="75%">
                    <PolarGrid stroke="#E5E7EB" />
                    <PolarAngleAxis
                      dataKey="criterion"
                      tick={{ fontSize: 11, fill: '#6B7280' }}
                    />
                    <PolarRadiusAxis
                      angle={30}
                      domain={[0, 100]}
                      tick={{ fontSize: 10, fill: '#9CA3AF' }}
                    />
                    {radarConditions.map((cond) => (
                      <Radar
                        key={cond.name}
                        name={cond.name}
                        dataKey={cond.name}
                        stroke={cond.color}
                        fill={cond.color}
                        fillOpacity={0.12}
                        strokeWidth={2}
                      />
                    ))}
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Legend */}
              <div className="flex flex-wrap gap-4 mt-3 justify-center">
                {radarConditions.map((cond) => (
                  <div key={cond.name} className="flex items-center gap-2 text-xs text-gray-600">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: cond.color }}
                    />
                    {cond.name}
                  </div>
                ))}
              </div>
            </div>

            {/* Feedback Loop */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h3 className="text-xs uppercase tracking-wider font-semibold text-gray-400 mb-4 pb-2 border-b border-gray-100">
                Clinician Feedback
              </h3>

              {!feedbackSubmitted ? (
                <>
                  <p className="text-sm text-gray-700 mb-4">
                    Did this analysis assist your diagnostic process?
                  </p>

                  <div className="flex flex-wrap gap-3">
                    {[
                      { key: 'yes', label: 'Yes, highly relevant', icon: ThumbsUp, color: '#2E7D32' },
                      { key: 'somewhat', label: 'Somewhat, but missed context', icon: Minus, color: '#F4A261' },
                      { key: 'no', label: 'No, inaccurate', icon: ThumbsDown, color: '#E07070' },
                    ].map((opt) => (
                      <button
                        key={opt.key}
                        onClick={() => handleFeedback(opt.key)}
                        className={clsx(
                          'flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm transition-all',
                          feedbackGiven === opt.key
                            ? 'border-current bg-gray-50 font-medium'
                            : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                        )}
                        style={feedbackGiven === opt.key ? { color: opt.color } : undefined}
                      >
                        <opt.icon className="w-4 h-4" />
                        {opt.label}
                      </button>
                    ))}
                  </div>

                  <AnimatePresence>
                    {feedbackGiven && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-4 overflow-hidden"
                      >
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={feedbackText}
                            onChange={(e) => setFeedbackText(e.target.value)}
                            placeholder="Optional: specific feedback (no patient PII)"
                            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none bg-white"
                          />
                          <button
                            onClick={handleFeedbackSubmit}
                            className="px-4 py-2.5 rounded-lg bg-[#111111] text-white text-sm font-medium hover:bg-gray-800 transition-colors flex items-center gap-2"
                          >
                            <Send className="w-3.5 h-3.5" />
                            Submit
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 py-4"
                >
                  <div className="w-8 h-8 rounded-full bg-[#2E7D32]/10 flex items-center justify-center">
                    <ShieldCheck className="w-4 h-4 text-[#2E7D32]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Thank you for your feedback.</p>
                    <p className="text-xs text-gray-500">This helps improve our analysis accuracy.</p>
                  </div>
                </motion.div>
              )}
            </div>

            {/* QR Code Note */}
            <div className="bg-white rounded-lg border border-gray-200 p-5 flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0 border border-gray-200">
                <QrCode className="w-8 h-8 text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Secure Access Link</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  This portal was accessed via the secure link on the patient's printed SOAP note. Access expires in 72 hours.
                </p>
                <p className="text-xs text-gray-400 font-mono mt-1">
                  aura.health/verify/{patientId.toLowerCase()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Citation Side Panel */}
      <AnimatePresence>
        {activeCitation && activeCitationData && (
          <CitationSidePanel
            citation={activeCitationData}
            onClose={() => setActiveCitation(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};