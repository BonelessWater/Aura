import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText, Users, MapPin, Check, Copy, AlertCircle, Info,
  Settings, BarChart3, MessageSquare, Compass, BookOpen,
  Sparkles, ChevronRight, Shield, ExternalLink, FlaskConical,
  Database, BookMarked, Download, X
} from 'lucide-react';
import { clsx } from 'clsx';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useNavigate } from 'react-router';
import { DailyNotes } from './DailyNotes';

interface ResultsDashboardProps {
  onViewSOAP: () => void;
  onViewSpecialists: () => void;
  onViewCommunity: () => void;
}

/* ────────────────────────────────────────────────────────────
   ARC GAUGE — animated SVG ring with gradient stroke
   ──────────────────────────────────────────────────────────── */
const ArcGauge = ({ score, label, color, delay = 0, large = false }: {
  score: number; label: string; color: string; delay?: number; large?: boolean;
}) => {
  const radius = large ? 62 : 32;
  const stroke = large ? 10 : 6;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const id = `gauge-${large ? 'lg' : 'sm'}-${score}`;

  return (
    <div className="relative flex flex-col items-center">
      <div className={clsx(
        "relative flex items-center justify-center",
        large ? "w-[160px] h-[160px]" : "w-[80px] h-[80px]"
      )}>
        {/* Pulsing radial glow behind gauge */}
        {large && (
          <motion.div
            className="absolute inset-[-30px] rounded-full"
            style={{
              background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`,
            }}
            animate={{ scale: [1, 1.1, 1], opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
        <svg className="transform -rotate-90 w-full h-full overflow-visible gauge-glow">
          <circle
            cx="50%" cy="50%" r={radius}
            stroke="rgba(26, 29, 38, 0.6)"
            strokeWidth={stroke} fill="transparent"
          />
          <motion.circle
            cx="50%" cy="50%" r={radius}
            stroke={`url(#${id})`}
            strokeWidth={stroke} fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.8, delay, ease: [0.22, 1, 0.36, 1] }}
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} />
              <stop offset="100%" stopColor={large ? '#2563EB' : '#E07070'} />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.span
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: delay + 0.5, type: 'spring', stiffness: 300 }}
            className={clsx("font-mono font-bold text-white", large ? "text-5xl" : "text-xl")}
          >
            {score}%
          </motion.span>
        </div>
      </div>
      <span className={clsx(
        "mt-3 text-center font-medium tracking-wide",
        large ? "text-sm text-[#7B61FF]" : "text-xs text-[#F4A261]"
      )}>
        {label}
      </span>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────
   AURA RIPPLE — concentric rings that expand outward on load
   ──────────────────────────────────────────────────────────── */
const AuraRipple = () => (
  <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden rounded-[20px]">
    {[0, 0.4, 0.8, 1.2].map((d, i) => (
      <motion.div
        key={i}
        className="absolute rounded-full border border-[#7B61FF]/20"
        style={{ width: 180, height: 180 }}
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 2.8, opacity: [0, 0.4, 0] }}
        transition={{ delay: 0.8 + d, duration: 2.5, ease: 'easeOut' }}
      />
    ))}
  </div>
);

/* ────────────────────────────────────────────────────────────
   FLOATING DOCK — macOS-style bottom navigation
   ──────────────────────────────────────────────────────────── */
const FloatingDock = ({ items }: {
  items: { id: string; icon: React.ElementType; label: string; description: string; onClick?: () => void }[];
}) => (
  <motion.nav
    initial={{ y: 60, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ delay: 0.5, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1 px-3 py-2.5 rounded-2xl"
    style={{
      background: 'rgba(13, 16, 24, 0.75)',
      backdropFilter: 'blur(24px)',
      WebkitBackdropFilter: 'blur(24px)',
      border: '1px solid rgba(123, 97, 255, 0.12)',
      animation: 'dock-breathe 4s ease-in-out infinite',
    }}
  >
    {items.map((item) => (
      <Tooltip.Root key={item.id} delayDuration={200}>
        <Tooltip.Trigger asChild>
          <motion.button
            onClick={item.onClick}
            whileHover={{ scale: 1.25, y: -6 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            className="w-11 h-11 flex items-center justify-center rounded-xl text-[#8A93B2] hover:text-white hover:bg-[#7B61FF]/10 transition-colors relative group"
          >
            <item.icon className="w-[18px] h-[18px]" />
            <span className="absolute -bottom-0.5 w-1 h-1 rounded-full bg-[#7B61FF]/0 group-hover:bg-[#7B61FF] transition-all" />
          </motion.button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="bg-[#13161F]/95 backdrop-blur-lg text-white px-4 py-3 rounded-xl text-xs shadow-2xl border border-[#7B61FF]/15 z-[60] max-w-[220px]"
            sideOffset={14}
            side="top"
          >
            <p className="font-semibold text-sm mb-1">{item.label}</p>
            <p className="text-[#8A93B2] leading-relaxed">{item.description}</p>
            <Tooltip.Arrow className="fill-[#13161F]" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    ))}
  </motion.nav>
);

/* ────────────────────────────────────────────────────────────
   PERSISTENT SAFETY HEADER — blurred, always visible
   ──────────────────────────────────────────────────────────── */
const SafetyHeader = () => (
  <motion.div
    initial={{ y: -40, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ delay: 0.2, duration: 0.5 }}
    className="sticky top-0 z-40 flex items-center justify-center gap-2 py-2.5 px-4 text-xs"
    style={{
      background: 'rgba(10, 13, 20, 0.6)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(224, 112, 112, 0.1)',
    }}
  >
    <Shield className="w-3.5 h-3.5 text-[#E07070]/70" />
    <span className="text-[#8A93B2]">
      <span className="text-[#E07070]/80 font-medium">Not a medical diagnosis</span>
      <span className="mx-1.5 text-[#2A2E3B]">·</span>
      Aura identifies statistical patterns — only a licensed physician can interpret these findings.
    </span>
  </motion.div>
);

/* ────────────────────────────────────────────────────────────
   RICH TOOLTIP TERM — hover for definition + source + methodology
   ──────────────────────────────────────────────────────────── */
const TooltipTerm = ({ term, def, source, methodology }: {
  term: string; def: string; source?: string; methodology?: string;
}) => (
  <Tooltip.Root delayDuration={150}>
    <Tooltip.Trigger asChild>
      <span className="cursor-help border-b border-dashed border-[#F4A261]/60 text-[#F0F2F8] hover:text-[#F4A261] hover:border-[#F4A261] transition-colors pb-0.5">
        {term}
      </span>
    </Tooltip.Trigger>
    <Tooltip.Portal>
      <Tooltip.Content
        className="bg-[#0D1017]/95 backdrop-blur-xl text-white px-5 py-4 rounded-xl text-sm shadow-2xl border border-[#7B61FF]/15 max-w-sm z-50"
        sideOffset={10}
      >
        <p className="font-medium text-[#F0F2F8] mb-2 leading-relaxed">{def}</p>
        {source && (
          <div className="flex items-start gap-2 mt-2 pt-2 border-t border-[#7B61FF]/10">
            <BookMarked className="w-3 h-3 text-[#7B61FF]/60 mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-[#8A93B2] leading-relaxed">
              <span className="text-[#7B61FF]/80 font-medium">Source:</span> {source}
            </p>
          </div>
        )}
        {methodology && (
          <div className="flex items-start gap-2 mt-1.5">
            <FlaskConical className="w-3 h-3 text-[#2563EB]/60 mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-[#8A93B2] leading-relaxed">
              <span className="text-[#2563EB]/80 font-medium">How detected:</span> {methodology}
            </p>
          </div>
        )}
        <Tooltip.Arrow className="fill-[#0D1017]" />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
);

/* ────────────────────────────────────────────────────────────
   INLINE SVG CHARTS for the Clinical Summary Modal
   ──────────────────────────────────────────────────────────── */

// CRP Trend Line Chart
const CRPTrendChart = () => {
  const data = [
    { month: 'Jan 24', value: 3.2 },
    { month: 'May 24', value: 5.1 },
    { month: 'Sep 24', value: 7.8 },
    { month: 'Jan 25', value: 9.4 },
    { month: 'Apr 25', value: 12.1 },
    { month: 'Jul 25', value: 14.8 },
  ];
  const maxVal = 18;
  const w = 420, h = 140, pad = 40;
  const chartW = w - pad * 2, chartH = h - 30;
  const points = data.map((d, i) => ({
    x: pad + (i / (data.length - 1)) * chartW,
    y: 10 + chartH - (d.value / maxVal) * chartH,
  }));
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const areaD = pathD + ` L${points[points.length - 1].x},${10 + chartH} L${points[0].x},${10 + chartH} Z`;
  // Normal threshold line at y = 3.0
  const threshY = 10 + chartH - (3.0 / maxVal) * chartH;

  return (
    <div>
      <p className="text-[11px] text-[#8A93B2] font-mono uppercase tracking-widest mb-3">CRP Trend · mg/L over 18 months</p>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxWidth: 420 }}>
        {/* Grid lines */}
        {[0, 3, 6, 9, 12, 15, 18].map(v => {
          const y = 10 + chartH - (v / maxVal) * chartH;
          return <line key={v} x1={pad} x2={w - pad} y1={y} y2={y} stroke="rgba(123,97,255,0.07)" strokeWidth={1} />;
        })}
        {/* Normal threshold */}
        <line x1={pad} x2={w - pad} y1={threshY} y2={threshY} stroke="rgba(82,208,160,0.3)" strokeWidth={1} strokeDasharray="4,4" />
        <text x={w - pad + 4} y={threshY + 3} fill="#52D0A0" fontSize={8} fontFamily="JetBrains Mono">Normal</text>
        {/* Area fill */}
        <path d={areaD} fill="url(#crpGradient)" />
        {/* Line */}
        <path d={pathD} fill="none" stroke="#E07070" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        {/* Dots */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={3.5} fill="#0D1017" stroke="#E07070" strokeWidth={2} />
            <text x={p.x} y={h - 2} textAnchor="middle" fill="#8A93B2" fontSize={8} fontFamily="JetBrains Mono">{data[i].month}</text>
            <text x={p.x} y={p.y - 8} textAnchor="middle" fill="#F0F2F8" fontSize={9} fontFamily="JetBrains Mono" fontWeight="bold">{data[i].value}</text>
          </g>
        ))}
        <defs>
          <linearGradient id="crpGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#E07070" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#E07070" stopOpacity={0} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};

// Autoimmune Comparison Horizontal Bar Chart
const ComparisonBarChart = () => {
  const conditions = [
    { label: 'SLE (Lupus)', value: 65, color: '#F4A261' },
    { label: 'Rheumatoid Arthritis', value: 41, color: '#7B61FF' },
    { label: "Sjögren's Syndrome", value: 38, color: '#2563EB' },
    { label: 'MCTD', value: 29, color: '#8A93B2' },
  ];

  return (
    <div>
      <p className="text-[11px] text-[#8A93B2] font-mono uppercase tracking-widest mb-3">Pattern Similarity Comparison</p>
      <div className="space-y-3">
        {conditions.map((c, i) => (
          <div key={c.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-[#C0C7DC]">{c.label}</span>
              <span className="text-xs font-mono font-bold" style={{ color: c.color }}>{c.value}%</span>
            </div>
            <div className="h-2 rounded-full bg-[#1A1D26] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${c.value}%` }}
                transition={{ delay: 0.3 + i * 0.1, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="h-full rounded-full"
                style={{ background: `linear-gradient(90deg, ${c.color}80, ${c.color})` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ACR/EULAR Criteria Checklist
const CriteriaChecklist = () => {
  const criteria = [
    { name: 'Malar Rash', met: true, points: 6 },
    { name: 'Leukopenia', met: true, points: 3 },
    { name: 'Elevated CRP', met: true, points: 2 },
    { name: 'Arthralgia / Joint Pain', met: true, points: 4 },
    { name: 'ANA Positive', met: true, points: 2 },
    { name: 'Anti-dsDNA Elevated', met: true, points: 6 },
    { name: 'Low Complement (C3/C4)', met: true, points: 3 },
    { name: 'Oral Ulcers', met: false, points: 0 },
    { name: 'Serositis', met: false, points: 0 },
    { name: 'Renal Disorder', met: false, points: 0 },
    { name: 'Neurologic Disorder', met: false, points: 0 },
  ];
  const totalScore = criteria.reduce((sum, c) => sum + c.points, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-[11px] text-[#8A93B2] font-mono uppercase tracking-widest">ACR/EULAR Criteria · 2019</p>
        <span className="text-xs font-mono font-bold text-[#7B61FF]">{totalScore} / ≥10 pts</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        {criteria.map((c) => (
          <div key={c.name} className="flex items-center gap-2 text-xs">
            <div className={clsx(
              "w-3.5 h-3.5 rounded flex items-center justify-center flex-shrink-0",
              c.met ? "bg-[#52D0A0]/15" : "bg-[#2A2E3B]/50"
            )}>
              {c.met && <Check className="w-2.5 h-2.5 text-[#52D0A0]" />}
            </div>
            <span className={c.met ? "text-[#C0C7DC]" : "text-[#8A93B2]/50"}>{c.name}</span>
            {c.met && <span className="text-[9px] font-mono text-[#7B61FF]/60 ml-auto">+{c.points}</span>}
          </div>
        ))}
      </div>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════
   DETAIL MODAL — reusable shell for per-card content
   ════════════════════════════════════════════════════════════ */
type ModalType = 'score' | 'sle' | 'summary' | null;

const CLINICAL_SUMMARY_TEXT = `AURA CLINICAL SUMMARY
Generated: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
─────────────────────────────────

PATIENT-REPORTED SYMPTOMS
• Chronic joint inflammation — 23 journal entries over 18 months
• Recurring malar (butterfly) rash — photo evidence Mar 2025, Jun 2025
• Persistent fatigue affecting daily activities
• Photosensitivity reported in 8 journal entries

LABORATORY FINDINGS (6 panels, Jan 2024 – Jul 2025)
• CRP: 3.2 → 14.8 mg/L (sustained upward trend; normal < 3.0)
• WBC: 3,200/µL (leukopenia; normal 4,500–11,000/µL)
• ANA: Positive, 1:320 titer, homogeneous pattern
• Anti-dsDNA: Elevated at 45 IU/mL (normal < 25)
• Complement C3/C4: Low-normal, trending downward

VISUAL EVIDENCE ANALYSIS
• Malar rash detected with 87% confidence (DermNet-trained CNN)
• Pattern consistent with lupus butterfly distribution
• No discoid lesions identified

PATTERN ANALYSIS
• Systemic Autoimmune Alignment: 92% (Category Confidence)
• SLE Pattern Similarity: 65% (Cosine similarity vs. canonical SLE profile)
• ACR/EULAR criteria matched: 7 of 11 (score: 14; threshold: ≥10)

CITED SOURCES
[1] ACR/EULAR 2019 Classification Criteria for SLE — Arthritis & Rheumatology, Vol 71
[2] Petri et al., 2012: SLICC classification criteria — Arthritis & Rheum 64(8)
[3] PubMed Central: CRP as predictor of autoimmune progression (PMC7234561)

─────────────────────────────────
DISCLAIMER: This is NOT a medical diagnosis. Aura identifies statistical
patterns in user-uploaded data. Only a licensed physician can interpret
these findings in the context of a full medical history.
`;

/* ── Modal content configs for each card ── */
const modalConfigs: Record<'score' | 'sle' | 'summary', {
  title: string;
  subtitle: string;
  icon: typeof FileText;
  color: string;
}> = {
  score: {
    title: 'How 92% Is Calculated',
    subtitle: 'Methodology & Lab Trends',
    icon: BarChart3,
    color: '#7B61FF',
  },
  sle: {
    title: 'SLE Pattern Breakdown',
    subtitle: 'Comparison & Classification Criteria',
    icon: Database,
    color: '#F4A261',
  },
  summary: {
    title: 'Full Clinical Summary',
    subtitle: `Generated ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`,
    icon: FileText,
    color: '#7B61FF',
  },
};

const DetailModal = ({ modalType, onClose }: { modalType: ModalType; onClose: () => void }) => {
  useEffect(() => {
    if (!modalType) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [modalType, onClose]);

  const handleDownload = () => {
    const blob = new Blob([CLINICAL_SUMMARY_TEXT], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aura-clinical-summary-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!modalType) return null;
  const config = modalConfigs[modalType];
  const IconComp = config.icon;

  return (
    <AnimatePresence>
      {modalType && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          onClick={onClose}
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl"
            style={{
              background: 'rgba(13, 16, 24, 0.95)',
              backdropFilter: 'blur(32px)',
              WebkitBackdropFilter: 'blur(32px)',
              border: `1px solid ${config.color}25`,
              boxShadow: `0 24px 80px rgba(0, 0, 0, 0.5), 0 0 0 1px ${config.color}15`,
            }}
          >
            {/* Top gradient line */}
            <div className="h-[2px]" style={{ background: `linear-gradient(90deg, ${config.color}, ${config.color}60)` }} />

            {/* Header */}
            <div className="flex items-center justify-between px-7 py-5 border-b" style={{ borderColor: `${config.color}18` }}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: `${config.color}15` }}>
                  <IconComp className="w-[18px] h-[18px]" style={{ color: config.color }} />
                </div>
                <div>
                  <h2 className="font-display font-bold text-[#F0F2F8] text-lg">{config.title}</h2>
                  <p className="text-[11px] text-[#8A93B2] font-mono uppercase tracking-widest mt-0.5">{config.subtitle}</p>
                </div>
              </div>
              <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8A93B2] hover:text-white hover:bg-white/5 transition-all">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Content — differs per modal type */}
            <div className="overflow-y-auto px-7 py-6 space-y-6" style={{ maxHeight: 'calc(85vh - 140px)' }}>

              {/* ═══ SCORE MODAL: Methodology + CRP Chart + Lab Findings ═══ */}
              {modalType === 'score' && (
                <>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#7B61FF]" />
                      <h4 className="text-xs font-display font-semibold text-[#7B61FF] uppercase tracking-wider">Methodology</h4>
                    </div>
                    <p className="text-sm text-[#C0C7DC] leading-relaxed">
                      This score represents the weighted alignment between your uploaded lab panels, photo analysis, and symptom journal against 14 known autoimmune pattern signatures in our literature database.
                    </p>
                    <p className="text-xs text-[#8A93B2] leading-relaxed mt-3">
                      Multi-modal RAG pipeline: lab values are vectorized against PubMed-indexed reference ranges, photo features are extracted via a dermatology classification model, and symptom correlations are scored using TF-IDF against ACR/EULAR classification criteria.
                    </p>
                  </motion.div>

                  <div className="gradient-divider" />

                  <motion.div
                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                    className="p-5 rounded-xl" style={{ background: 'rgba(224, 112, 112, 0.04)', border: '1px solid rgba(224, 112, 112, 0.08)' }}
                  >
                    <CRPTrendChart />
                  </motion.div>

                  <div className="gradient-divider" />

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                      <h4 className="text-xs font-display font-semibold text-[#2563EB] uppercase tracking-wider">Laboratory Findings</h4>
                      <span className="text-[10px] text-[#8A93B2]/50 font-mono">(6 panels, Jan 2024 – Jul 2025)</span>
                    </div>
                    <ul className="space-y-2 pl-4">
                      {['CRP: 3.2 → 14.8 mg/L (sustained upward trend; normal < 3.0)',
                        'WBC: 3,200/µL (leukopenia; normal 4,500–11,000/µL)',
                        'ANA: Positive, 1:320 titer, homogeneous pattern',
                        'Anti-dsDNA: Elevated at 45 IU/mL (normal < 25)',
                        'Complement C3/C4: Low-normal, trending downward',
                      ].map((item, i) => (
                        <li key={i} className="text-sm text-[#C0C7DC] leading-relaxed flex items-start gap-2">
                          <span className="text-[#8A93B2]/30 mt-0.5">•</span><span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#F4A261]" />
                      <h4 className="text-xs font-display font-semibold text-[#F4A261] uppercase tracking-wider">Visual Evidence</h4>
                    </div>
                    <ul className="space-y-2 pl-4">
                      {['Malar rash detected with 87% confidence (DermNet-trained CNN)',
                        'Pattern consistent with lupus butterfly distribution',
                        'No discoid lesions identified',
                      ].map((item, i) => (
                        <li key={i} className="text-sm text-[#C0C7DC] leading-relaxed flex items-start gap-2">
                          <span className="text-[#8A93B2]/30 mt-0.5">•</span><span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                </>
              )}

              {/* ═══ SLE MODAL: Comparison Chart + ACR/EULAR Criteria ═══ */}
              {modalType === 'sle' && (
                <>
                  <motion.div
                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
                    className="p-5 rounded-xl" style={{ background: 'rgba(123, 97, 255, 0.04)', border: '1px solid rgba(123, 97, 255, 0.08)' }}
                  >
                    <ComparisonBarChart />
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#F4A261]" />
                      <h4 className="text-xs font-display font-semibold text-[#F4A261] uppercase tracking-wider">How 65% SLE is calculated</h4>
                    </div>
                    <p className="text-sm text-[#C0C7DC] leading-relaxed">
                      Cosine similarity between your vectorized symptom+lab profile and the canonical SLE profile derived from 2,400+ confirmed SLE cases in medical literature. 65% means partial overlap — not confirmation.
                    </p>
                    <p className="text-xs text-[#8A93B2] leading-relaxed mt-2">
                      Source: Petri et al., 2012 — Derivation and validation of SLICC classification criteria — Arthritis & Rheum 64(8).
                    </p>
                  </motion.div>

                  <div className="gradient-divider" />

                  <motion.div
                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
                    className="p-5 rounded-xl" style={{ background: 'rgba(82, 208, 160, 0.03)', border: '1px solid rgba(82, 208, 160, 0.08)' }}
                  >
                    <CriteriaChecklist />
                  </motion.div>
                </>
              )}

              {/* ═══ FULL SUMMARY MODAL: Symptoms + Sources + Download ═══ */}
              {modalType === 'summary' && (
                <>
                  {[{
                    title: 'Patient-Reported Symptoms', color: '#7B61FF',
                    items: [
                      'Chronic joint inflammation — 23 journal entries over 18 months',
                      'Recurring malar (butterfly) rash — photo evidence Mar 2025, Jun 2025',
                      'Persistent fatigue affecting daily activities',
                      'Photosensitivity reported in 8 journal entries',
                    ],
                  }, {
                    title: 'Pattern Analysis', color: '#7B61FF',
                    items: [
                      'Systemic Autoimmune Alignment: 92% (Category Confidence)',
                      'SLE Pattern Similarity: 65% (Cosine similarity)',
                      'ACR/EULAR criteria matched: 7 of 11 (score: 14; threshold ≥10)',
                      'Comparison: RA 41% · Sjögren\'s 38% · MCTD 29%',
                    ],
                  }, {
                    title: 'Cited Sources', color: '#8A93B2',
                    items: [
                      '[1] ACR/EULAR 2019 SLE Classification Criteria — Arthritis & Rheumatology, Vol 71',
                      '[2] Petri et al., 2012: SLICC criteria — Arthritis & Rheum 64(8)',
                      '[3] PubMed Central: CRP as predictor of autoimmune progression (PMC7234561)',
                    ],
                  }].map((section, si) => (
                    <motion.div
                      key={section.title}
                      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 + si * 0.06 }}
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: section.color }} />
                        <h4 className="text-xs font-display font-semibold uppercase tracking-wider" style={{ color: section.color }}>{section.title}</h4>
                      </div>
                      <ul className="space-y-2 pl-4">
                        {section.items.map((item, i) => (
                          <li key={i} className="text-sm text-[#C0C7DC] leading-relaxed flex items-start gap-2">
                            <span className="text-[#8A93B2]/30 mt-0.5">•</span><span>{item}</span>
                          </li>
                        ))}
                      </ul>
                      {si < 2 && <div className="gradient-divider mt-5" />}
                    </motion.div>
                  ))}
                </>
              )}

              {/* Disclaimer — shown in all modals */}
              <div className="flex items-start gap-3 p-4 rounded-xl" style={{ background: 'rgba(224, 112, 112, 0.06)', border: '1px solid rgba(224, 112, 112, 0.1)' }}>
                <Shield className="w-4 h-4 text-[#E07070]/60 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[#8A93B2] leading-relaxed">
                  This is <span className="text-[#E07070]/80 font-medium">not a medical diagnosis</span>. Aura identifies statistical patterns in user-uploaded data. Only a licensed physician can interpret these findings.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="px-7 py-4 border-t border-[rgba(123,97,255,0.1)] flex items-center justify-between">
              <span className="text-[10px] text-[#8A93B2]/40 font-mono uppercase tracking-widest">
                <Sparkles className="w-3 h-3 inline mr-1" />Aura · Privacy-First Analysis
              </span>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-[#7B61FF]/10 text-[#7B61FF] border border-[#7B61FF]/15 hover:bg-[#7B61FF]/20 hover:border-[#7B61FF]/25 transition-all"
              >
                <Download className="w-4 h-4" />
                Download Summary
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

/* ════════════════════════════════════════════════════════════
   MAIN COMPONENT — THE BENTO-PULSE AURA DASHBOARD
   ════════════════════════════════════════════════════════════ */
export const ResultsDashboard = ({ onViewSOAP, onViewSpecialists, onViewCommunity }: ResultsDashboardProps) => {
  const [copied, setCopied] = useState(false);
  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const navigate = useNavigate();

  const handleCopy = () => {
    navigator.clipboard?.writeText(
      "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Dock items — replaces the old sidebar
  const dockItems = [
    { id: 'soap', icon: FileText, label: 'SOAP Note', description: 'AI-generated clinical note formatted in Subjective, Objective, Assessment, Plan structure for your physician.', onClick: onViewSOAP },
    { id: 'specialists', icon: MapPin, label: 'Find Specialists', description: 'Locate board-certified Rheumatologists near you, ranked by autoimmune specialization and patient reviews.', onClick: onViewSpecialists },
    { id: 'community', icon: Users, label: 'Community', description: 'Connect with others who share similar symptom patterns. All conversations are anonymous and privacy-first.', onClick: onViewCommunity },
    { id: 'vault', icon: Settings, label: 'The Vault', description: 'Your encrypted local data store — labs, photos, and symptom logs. Nothing leaves your device.', onClick: () => navigate('/vault') },
  ];

  return (
    <Tooltip.Provider delayDuration={150}>
      <div className="relative min-h-screen bg-transparent">

        {/* ─── Persistent Safety Header ─── */}
        <SafetyHeader />

        {/* ─── Main Bento Grid ─── */}
        <div className="max-w-[1200px] mx-auto px-6 py-8 pb-28">

          {/* ─── AURA Ribbon Logo ─── */}
          <div className="flex flex-col items-center justify-center mb-10 relative">
            {/* Soft glow behind logo */}
            <motion.div
              className="absolute w-[260px] h-[80px] rounded-full pointer-events-none"
              style={{
                background: 'radial-gradient(ellipse, rgba(123,97,255,0.12) 0%, transparent 70%)',
                filter: 'blur(25px)',
              }}
              animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.7, 0.4] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            />

            {/* Ribbon logo image */}
            <motion.img
              src="/assets/aura-ribbon-logo.png"
              alt="AURA — spelled with awareness ribbons"
              initial={{ opacity: 0, scale: 0.9, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="h-14 md:h-18 w-auto object-contain drop-shadow-[0_0_20px_rgba(123,97,255,0.2)] select-none"
              draggable={false}
            />

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="mt-2 text-[10px] font-mono text-[#8A93B2]/50 uppercase tracking-[0.35em]"
            >
              Analysis Complete
            </motion.p>

            {/* Thin gradient line under */}
            <motion.div
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 1 }}
              transition={{ delay: 0.7, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              className="mt-2 h-[1px] w-36 bg-gradient-to-r from-transparent via-[#7B61FF]/30 to-transparent"
            />
          </div>

          {/* ═══ ROW 1: Primary Score (large) + Clinical Translation ═══ */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 mb-5">

            {/* ── PRIMARY SCORE: The "Aura Core" — clicks to open full summary ── */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              onClick={() => setActiveModal('score')}
              className="lg:col-span-2 dashboard-card glow-violet p-8 flex flex-col items-center justify-center relative min-h-[320px] cursor-pointer group"
              style={{ animation: 'pulse-border-violet 6s ease-in-out infinite' }}
            >
              {/* Aura ripple rings */}
              <AuraRipple />

              {/* Corner accent */}
              <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-bl from-[#7B61FF]/[0.06] to-transparent rounded-bl-full pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-[#2563EB]/[0.04] to-transparent rounded-tr-full pointer-events-none" />

              {/* Click hint */}
              <div className="absolute top-4 right-4 z-10 flex items-center gap-1.5 text-[#8A93B2]/40 group-hover:text-[#8A93B2]/70 transition-colors">
                <Info className="w-3.5 h-3.5" />
                <span className="text-[9px] font-mono uppercase tracking-widest hidden lg:inline">Click for details</span>
              </div>

              <div className="relative z-10">
                <ArcGauge score={92} label="Systemic Autoimmune Alignment" color="#7B61FF" delay={0.3} large />
              </div>

              {/* Subtle label */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
                className="mt-4 text-[10px] text-[#8A93B2]/40 font-mono uppercase tracking-widest"
              >
                Category Confidence
              </motion.p>
            </motion.div>

            {/* ── CLINICAL TRANSLATION ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="lg:col-span-3 dashboard-card p-8 flex flex-col"
            >
              <h3 className="text-lg font-display font-semibold text-[#F0F2F8] mb-6 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-[#2563EB]" />
                </div>
                <span className="bg-gradient-to-r from-[#F0F2F8] to-[#8A93B2] bg-clip-text text-transparent">
                  Clinical Translation
                </span>
              </h3>

              <div className="space-y-5 text-[#C0C7DC] leading-relaxed text-[15px] font-light flex-1">
                <p>
                  Patient presents with chronic <TooltipTerm term="joint inflammation" def="Swelling, pain, and stiffness in one or more joints caused by immune system activity." source="Identified from your symptom journal entries tagged with 'joint pain' (23 occurrences over 18 months)." methodology="NLP keyword extraction + temporal frequency analysis from your daily logs." /> and <TooltipTerm term="malar rash" def="A butterfly-shaped rash across the cheeks and nose, a hallmark sign of Lupus." source="Detected from photo uploads dated Mar 2025 and Jun 2025." methodology="Dermatology classification model (DermNet-trained CNN) with 87% confidence on malar pattern." />.
                  Longitudinal blood work shows a sustained upward trend in <TooltipTerm term="CRP" def="C-Reactive Protein — an inflammatory marker. Persistent elevation suggests chronic systemic inflammation." source="Your lab panels: CRP rose from 3.2 mg/L (Jan 2024) to 14.8 mg/L (Jul 2025) across 6 samples." methodology="Linear regression on serial lab values, compared against PubMed reference thresholds (normal < 3.0 mg/L)." /> over 18 months.
                  Currently experiencing <TooltipTerm term="leukopenia" def="A lower-than-normal white blood cell count, commonly seen in autoimmune conditions like Lupus." source="Latest WBC: 3,200/µL (Jul 2025). Normal range: 4,500–11,000/µL." methodology="Flagged automatically when your lab value fell below the lower reference limit across 2+ consecutive panels." /> and persistent fatigue affecting daily tasks.
                </p>
                <div className="gradient-divider" />
                <p>
                  Lab ratios combined with visual evidence align with a <span className="text-[#F0F2F8] font-medium border-b-2 border-[#7B61FF]/40 pb-0.5">Systemic Autoimmune</span> profile.
                  Secondary literature flags suggest <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where the immune system attacks healthy tissue, causing widespread inflammation." source="ACR/EULAR 2019 SLE Classification Criteria — Arthritis & Rheumatology, Vol 71." methodology="Your data matched 7 of 11 weighted criteria (≥10 points required; you scored 14). Criteria include: malar rash, leukopenia, elevated CRP, and arthralgia." /> as a potential etiology requiring specialist confirmation.
                </p>
              </div>

              {/* Bottom action */}
              <div className="flex items-center justify-between mt-5 pt-4 border-t border-[rgba(123,97,255,0.08)]">
                <div className="flex items-center gap-2">
                  <Compass className="w-3.5 h-3.5 text-[#2563EB]/40" />
                  <span className="text-[10px] text-[#8A93B2]/40 font-mono uppercase tracking-widest">Layman's Compass</span>
                </div>
                <button
                  onClick={() => setActiveModal('summary')}
                  className="flex items-center gap-1.5 text-xs font-medium text-[#7B61FF] hover:text-[#9B85FF] transition-colors group"
                >
                  View Full Summary
                  <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </motion.div>
          </div>

          {/* ═══ ROW 2: SLE Score + What This Means / Doesn't Mean ═══ */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">

            {/* ── SLE SATELLITE — clicks to open full summary ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              onClick={() => setActiveModal('sle')}
              className="dashboard-card p-6 flex flex-col items-center justify-center relative cursor-pointer group"
              style={{ animation: 'pulse-border-amber 8s ease-in-out infinite' }}
            >
              <div className="absolute top-0 left-0 w-20 h-20 bg-gradient-to-br from-[#F4A261]/[0.05] to-transparent rounded-br-full pointer-events-none" />

              {/* Click hint */}
              <div className="absolute top-3 right-3 text-[#8A93B2]/30 group-hover:text-[#8A93B2]/60 transition-colors">
                <Info className="w-3 h-3" />
              </div>

              <ArcGauge score={65} label="SLE Pattern Similarity" color="#F4A261" delay={0.5} />

              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
                className="mt-4 text-[10px] text-[#E07070] bg-[#E07070]/[0.07] px-3 py-1 rounded-full border border-[#E07070]/10 font-medium"
              >
                Pattern match, not a diagnosis.
              </motion.span>
            </motion.div>

            {/* ── WHAT THIS MEANS ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="dashboard-card glow-teal p-6"
              style={{ borderColor: 'rgba(62, 207, 207, 0.15)' }}
            >
              <h4 className="text-xs font-display font-semibold text-[#2563EB] mb-4 uppercase tracking-wider flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                What this means
              </h4>
              <ul className="space-y-2.5 text-sm text-[#C0C7DC] leading-relaxed">
                <motion.li initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
                  • Lab trends match patterns in peer-reviewed autoimmune research.
                </motion.li>
                <motion.li initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 }}>
                  • A Rheumatologist is the right next step.
                </motion.li>
                <motion.li initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.8 }}>
                  • The SOAP note gives your doctor a structured starting point.
                </motion.li>
              </ul>
            </motion.div>

            {/* ── WHAT THIS DOES NOT MEAN ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="dashboard-card glow-rose p-6"
              style={{ borderColor: 'rgba(224, 112, 112, 0.12)' }}
            >
              <h4 className="text-xs font-display font-semibold text-[#E07070] mb-4 uppercase tracking-wider flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#E07070]" />
                What this does not mean
              </h4>
              <ul className="space-y-2.5 text-sm text-[#C0C7DC] leading-relaxed">
                <motion.li initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
                  • This is <strong className="text-[#F0F2F8]">not</strong> a diagnosis of Lupus or any specific disease.
                </motion.li>
                <motion.li initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 }}>
                  • Scores reflect statistical alignment, not clinical certainty.
                </motion.li>
                <motion.li initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.8 }}>
                  • Only a doctor with access to your full history can diagnose.
                </motion.li>
              </ul>
            </motion.div>
          </div>

          {/* ═══ ROW 3: GP Script + Daily Notes ═══ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* ── GP SCRIPT ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="dashboard-card p-7 relative"
              style={{ borderColor: 'rgba(62, 207, 207, 0.15)' }}
            >
              {/* Gradient sweep */}
              <div className="absolute inset-0 bg-gradient-to-r from-[#2563EB]/[0.03] via-transparent to-[#7B61FF]/[0.03] pointer-events-none rounded-[20px]" />

              <div className="relative z-10">
                <h4 className="font-display font-semibold text-[#2563EB] text-base mb-4 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  What to say at your next appointment
                </h4>

                <p className="text-sm text-[#C0C7DC] mb-5 italic leading-relaxed pl-4 border-l-2 border-[#2563EB]/20">
                  "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
                </p>

                <button
                  onClick={handleCopy}
                  className={clsx(
                    "w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all",
                    copied
                      ? "bg-[#52D0A0]/15 text-[#52D0A0] border border-[#52D0A0]/20"
                      : "bg-[#2563EB]/10 text-[#2563EB] border border-[#2563EB]/15 hover:bg-[#2563EB]/15 hover:border-[#2563EB]/25"
                  )}
                >
                  {copied ? (
                    <motion.div initial={{ scale: 0.5 }} animate={{ scale: 1 }} className="flex items-center gap-2">
                      <Check className="w-4 h-4" /> Copied!
                    </motion.div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Copy className="w-4 h-4" /> Copy Script
                    </div>
                  )}
                </button>
              </div>
            </motion.div>

            {/* ── DAILY NOTES ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="dashboard-card p-7"
            >
              <DailyNotes />
            </motion.div>
          </div>
        </div>

        {/* ─── Floating Action Dock ─── */}
        <FloatingDock items={dockItems} />

        {/* ─── Clinical Summary Modal ─── */}
        <DetailModal modalType={activeModal} onClose={() => setActiveModal(null)} />
      </div>
    </Tooltip.Provider>
  );
};