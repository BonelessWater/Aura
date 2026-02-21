import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText, Users, MapPin, Check, Copy, AlertCircle, Info,
  Settings, BarChart3, MessageSquare, Compass, BookOpen,
  Sparkles, ChevronRight, Shield
} from 'lucide-react';
import { clsx } from 'clsx';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useNavigate } from 'react-router';
import { DailyNotes } from './DailyNotes';
import { DoctorHoverHelper } from './DoctorHoverHelper';

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
              <stop offset="100%" stopColor={large ? '#3ECFCF' : '#E07070'} />
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
  items: { id: string; icon: React.ElementType; label: string; onClick?: () => void }[];
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
            {/* Active dot */}
            <span className="absolute -bottom-0.5 w-1 h-1 rounded-full bg-[#7B61FF]/0 group-hover:bg-[#7B61FF] transition-all" />
          </motion.button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="bg-[#13161F]/95 backdrop-blur-lg text-white px-3 py-1.5 rounded-lg text-xs font-medium shadow-2xl border border-[#7B61FF]/15 z-[60]"
            sideOffset={12}
            side="top"
          >
            {item.label}
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
   TOOLTIP TERM — inline hover definitions for medical jargon
   ──────────────────────────────────────────────────────────── */
const TooltipTerm = ({ term, def }: { term: string; def: string }) => (
  <Tooltip.Root>
    <Tooltip.Trigger asChild>
      <span className="cursor-help border-b border-dashed border-[#F4A261]/60 text-[#F0F2F8] hover:text-[#F4A261] hover:border-[#F4A261] transition-colors pb-0.5">
        {term}
      </span>
    </Tooltip.Trigger>
    <Tooltip.Portal>
      <Tooltip.Content
        className="bg-[#13161F]/95 backdrop-blur-lg text-white px-5 py-3 rounded-xl text-sm shadow-2xl border border-[#7B61FF]/15 max-w-xs z-50 leading-relaxed"
        sideOffset={8}
      >
        {def}
        <Tooltip.Arrow className="fill-[#13161F]" />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
);

/* ════════════════════════════════════════════════════════════
   MAIN COMPONENT — THE BENTO-PULSE AURA DASHBOARD
   ════════════════════════════════════════════════════════════ */
export const ResultsDashboard = ({ onViewSOAP, onViewSpecialists, onViewCommunity }: ResultsDashboardProps) => {
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [expandedTile, setExpandedTile] = useState<string | null>(null);

  const handleCopy = () => {
    navigator.clipboard?.writeText(
      "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Dock items — replaces the old sidebar
  const dockItems = [
    { id: 'soap', icon: FileText, label: 'SOAP Note', onClick: onViewSOAP },
    { id: 'specialists', icon: MapPin, label: 'Find Specialists', onClick: onViewSpecialists },
    { id: 'community', icon: Users, label: 'Community', onClick: onViewCommunity },
    { id: 'vault', icon: Settings, label: 'The Vault', onClick: () => navigate('/vault') },
  ];

  return (
    <Tooltip.Provider>
      <div ref={wrapperRef} className="relative min-h-screen bg-transparent">
        <DoctorHoverHelper boxRef={wrapperRef} />

        {/* ─── Persistent Safety Header ─── */}
        <SafetyHeader />

        {/* ─── Main Bento Grid ─── */}
        <div className="max-w-[1200px] mx-auto px-6 py-8 pb-28">

          {/* Top label */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-3 mb-8"
          >
            <Sparkles className="w-4 h-4 text-[#7B61FF]/60" />
            <span className="text-xs font-mono text-[#8A93B2]/60 uppercase tracking-[0.2em]">Your Aura · Analysis Complete</span>
          </motion.div>

          {/* ═══ ROW 1: Primary Score (large) + Clinical Translation ═══ */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 mb-5">

            {/* ── PRIMARY SCORE: The "Aura Core" ── */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="lg:col-span-2 dashboard-card glow-violet p-8 flex flex-col items-center justify-center relative min-h-[320px]"
              style={{ animation: 'pulse-border-violet 6s ease-in-out infinite' }}
            >
              {/* Aura ripple rings */}
              <AuraRipple />

              {/* Corner accent */}
              <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-bl from-[#7B61FF]/[0.06] to-transparent rounded-bl-full pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-[#3ECFCF]/[0.04] to-transparent rounded-tr-full pointer-events-none" />

              {/* Info tooltip */}
              <div className="absolute top-4 right-4 z-10">
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <Info className="w-4 h-4 text-[#8A93B2]/40 hover:text-[#8A93B2] transition-colors cursor-help" />
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content className="bg-[#13161F]/95 backdrop-blur-lg text-white px-4 py-2 rounded-lg text-sm shadow-xl border border-[#7B61FF]/15 max-w-xs z-50" sideOffset={5}>
                      Category Confidence — how strongly your data aligns with known autoimmune patterns.
                      <Tooltip.Arrow className="fill-[#13161F]" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
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
                <div className="w-8 h-8 rounded-lg bg-[#3ECFCF]/10 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-[#3ECFCF]" />
                </div>
                <span className="bg-gradient-to-r from-[#F0F2F8] to-[#8A93B2] bg-clip-text text-transparent">
                  Clinical Translation
                </span>
              </h3>

              <div className="space-y-5 text-[#C0C7DC] leading-relaxed text-[15px] font-light flex-1">
                <p>
                  Patient presents with chronic <TooltipTerm term="joint inflammation" def="Swelling, pain, and stiffness in one or more joints caused by immune system activity." /> and <TooltipTerm term="malar rash" def="A butterfly-shaped rash across the cheeks and nose, a hallmark sign of Lupus." />.
                  Longitudinal blood work shows a sustained upward trend in <TooltipTerm term="CRP" def="C-Reactive Protein — an inflammatory marker. Persistent elevation suggests chronic systemic inflammation." /> over 18 months.
                  Currently experiencing <TooltipTerm term="leukopenia" def="A lower-than-normal white blood cell count, commonly seen in autoimmune conditions like Lupus." /> and persistent fatigue affecting daily tasks.
                </p>
                <div className="gradient-divider" />
                <p>
                  Lab ratios combined with visual evidence align with a <span className="text-[#F0F2F8] font-medium border-b-2 border-[#7B61FF]/40 pb-0.5">Systemic Autoimmune</span> profile.
                  Secondary literature flags suggest <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where the immune system attacks healthy tissue, causing widespread inflammation." /> as a potential etiology requiring specialist confirmation.
                </p>
              </div>

              {/* Bottom tag */}
              <div className="flex items-center gap-2 mt-5 pt-4 border-t border-[rgba(123,97,255,0.08)]">
                <Compass className="w-3.5 h-3.5 text-[#3ECFCF]/40" />
                <span className="text-[10px] text-[#8A93B2]/40 font-mono uppercase tracking-widest">Layman's Compass · Plain-English Summary</span>
              </div>
            </motion.div>
          </div>

          {/* ═══ ROW 2: SLE Score + What This Means / Doesn't Mean ═══ */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">

            {/* ── SLE SATELLITE ── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="dashboard-card p-6 flex flex-col items-center justify-center relative"
              style={{ animation: 'pulse-border-amber 8s ease-in-out infinite' }}
            >
              <div className="absolute top-0 left-0 w-20 h-20 bg-gradient-to-br from-[#F4A261]/[0.05] to-transparent rounded-br-full pointer-events-none" />
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
              <h4 className="text-xs font-display font-semibold text-[#3ECFCF] mb-4 uppercase tracking-wider flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#3ECFCF]" />
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
              <div className="absolute inset-0 bg-gradient-to-r from-[#3ECFCF]/[0.03] via-transparent to-[#7B61FF]/[0.03] pointer-events-none rounded-[20px]" />

              <div className="relative z-10">
                <h4 className="font-display font-semibold text-[#3ECFCF] text-base mb-4 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  What to say at your next appointment
                </h4>

                <p className="text-sm text-[#C0C7DC] mb-5 italic leading-relaxed pl-4 border-l-2 border-[#3ECFCF]/20">
                  "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
                </p>

                <button
                  onClick={handleCopy}
                  className={clsx(
                    "w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all",
                    copied
                      ? "bg-[#52D0A0]/15 text-[#52D0A0] border border-[#52D0A0]/20"
                      : "bg-[#3ECFCF]/10 text-[#3ECFCF] border border-[#3ECFCF]/15 hover:bg-[#3ECFCF]/15 hover:border-[#3ECFCF]/25"
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
      </div>
    </Tooltip.Provider>
  );
};