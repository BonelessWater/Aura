import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '../ui/Button';
import {
  Menu, X, Home, FileText, Users, MapPin,
  ChevronRight, Check, Copy, AlertCircle, Info,
  Settings, BarChart3, MessageSquare, Compass, BookOpen,
  Sparkles
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

const ArcGauge = ({ score, label, color, delay = 0, small = false }: { score: number; label: string; color: string; delay?: number; small?: boolean }) => {
  const radius = small ? 30 : 50;
  const stroke = small ? 6 : 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className={clsx("relative flex flex-col items-center", small ? "w-32" : "w-48")}>
      <div className={clsx("relative flex items-center justify-center", small ? "w-[80px] h-[80px]" : "w-[120px] h-[120px]")}>
        {/* Pulsing glow behind the gauge */}
        {!small && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`,
            }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0.8, 0.5] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
        <svg className="transform -rotate-90 w-full h-full overflow-visible gauge-glow">
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            stroke="rgba(26, 29, 38, 0.8)"
            strokeWidth={stroke}
            fill="transparent"
          />
          <motion.circle
            cx="50%"
            cy="50%"
            r={radius}
            stroke={`url(#gauge-gradient-${small ? 'small' : 'large'})`}
            strokeWidth={stroke}
            fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, delay, ease: [0.22, 1, 0.36, 1] }}
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id={`gauge-gradient-${small ? 'small' : 'large'}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} />
              <stop offset="100%" stopColor={small ? '#E07070' : '#3ECFCF'} />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <motion.span
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: delay + 0.5, type: 'spring', stiffness: 300 }}
            className={clsx("font-mono font-bold text-white", small ? "text-xl" : "text-4xl")}
          >
            {score}%
          </motion.span>
        </div>
      </div>
      <span className={clsx(
        "mt-4 text-center font-medium tracking-wide",
        small ? "text-xs text-[#F4A261]" : "text-sm text-[#7B61FF]"
      )}>
        {label}
      </span>
    </div>
  );
};

export const ResultsDashboard = ({ onViewSOAP, onViewSpecialists, onViewCommunity }: ResultsDashboardProps) => {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState('scores');
  const navigate = useNavigate();
  const mainRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const handleCopy = () => {
    navigator.clipboard?.writeText("I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos.");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Track which section is in view for sidebar highlight
  useEffect(() => {
    const container = mainRef.current;
    if (!container) return;
    const sections = ['scores', 'translation', 'next-steps', 'daily-notes'];
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { root: container, rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const scrollItems = [
    { id: 'scores', icon: BarChart3, label: "Your Scores", scrollTo: 'scores' },
    { id: 'translation', icon: Compass, label: "Translation", scrollTo: 'translation' },
    { id: 'next-steps', icon: MessageSquare, label: "Next Steps", scrollTo: 'next-steps' },
    { id: 'daily-notes', icon: BookOpen, label: "Daily Notes", scrollTo: 'daily-notes' },
  ];

  const actionItems = [
    { id: 'soap', icon: FileText, label: "SOAP Note", onClick: onViewSOAP },
    { id: 'specialists', icon: MapPin, label: "Specialists", onClick: onViewSpecialists },
    { id: 'community', icon: Users, label: "Community", onClick: onViewCommunity },
    { id: 'vault', icon: Settings, label: "The Vault", href: "/vault" },
  ];

  return (
    <Tooltip.Provider>
      <div ref={wrapperRef} className="flex h-screen bg-transparent overflow-hidden relative">
        <DoctorHoverHelper boxRef={wrapperRef} />

        {/* ─── Sidebar ─── */}
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="w-20 lg:w-[280px] border-r border-[rgba(123,97,255,0.1)] flex flex-col bg-[rgba(10,13,20,0.7)] backdrop-blur-xl z-20"
        >
          {/* Top gradient accent */}
          <div className="h-[2px] bg-gradient-to-r from-[#7B61FF] via-[#3ECFCF] to-transparent" />

          <div className="p-6 pb-4">
            <h1 className="text-xl font-display font-bold text-white hidden lg:block tracking-wider">
              <span className="bg-gradient-to-r from-[#7B61FF] to-[#3ECFCF] bg-clip-text text-transparent">Aura</span>
            </h1>
            <p className="text-[10px] text-[#8A93B2] hidden lg:block mt-1 font-mono tracking-widest uppercase">Results Dashboard</p>
          </div>

          <nav className="flex-1 px-3 space-y-1">
            {/* Section label */}
            <span className="text-[9px] uppercase tracking-[0.15em] text-[#8A93B2]/50 px-3 pb-1 block font-medium">Navigate</span>

            {scrollItems.map((item, i) => {
              const isActive = activeSection === item.scrollTo;
              return (
                <motion.button
                  key={item.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  onClick={() => scrollToSection(item.scrollTo!)}
                  className={clsx(
                    "w-full flex items-center gap-3 p-3 rounded-xl transition-all group relative",
                    isActive
                      ? "bg-[#7B61FF]/10 text-white"
                      : "text-[#8A93B2] hover:bg-white/[0.03] hover:text-white"
                  )}
                >
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-7 sidebar-active-indicator"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  <item.icon className={clsx(
                    "w-[18px] h-[18px] transition-all",
                    isActive && "text-[#7B61FF] drop-shadow-[0_0_6px_rgba(123,97,255,0.5)]"
                  )} />
                  <span className="hidden lg:block text-sm font-medium">{item.label}</span>
                  {isActive && (
                    <ChevronRight className="w-3 h-3 ml-auto hidden lg:block text-[#7B61FF]/50" />
                  )}
                </motion.button>
              );
            })}

            {/* Divider */}
            <div className="gradient-divider my-3 mx-3" />

            {/* Section label */}
            <span className="text-[9px] uppercase tracking-[0.15em] text-[#8A93B2]/50 px-3 pb-1 block font-medium">Actions</span>

            {actionItems.map((item, i) => (
              <motion.button
                key={item.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                onClick={item.onClick || (item.href ? () => navigate(item.href!) : undefined)}
                className="w-full flex items-center gap-3 p-3 rounded-xl text-[#8A93B2] hover:bg-white/[0.03] hover:text-white transition-all group"
              >
                <item.icon className="w-[18px] h-[18px] group-hover:text-[#3ECFCF] transition-colors" />
                <span className="hidden lg:block text-sm font-medium">{item.label}</span>
              </motion.button>
            ))}
          </nav>

          {/* Bottom branding */}
          <div className="p-4 border-t border-[rgba(123,97,255,0.08)]">
            <div className="flex items-center gap-2 px-2">
              <Sparkles className="w-3.5 h-3.5 text-[#7B61FF]/40" />
              <span className="text-[10px] text-[#8A93B2]/40 font-mono hidden lg:block">v1.0 · Hacklytics 2026</span>
            </div>
          </div>
        </motion.div>

        {/* ─── Main Content ─── */}
        <div ref={mainRef} className="flex-1 overflow-y-auto p-6 lg:p-10 relative scroll-smooth">

          <div className="max-w-5xl mx-auto space-y-8">

            {/* ─── Score Cards ─── */}
            <div id="scores" className="scroll-target grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Score Card 1: Primary */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="dashboard-card glow-violet p-8 flex flex-col items-center justify-center relative"
              >
                {/* Decorative corner accent */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#7B61FF]/[0.06] to-transparent rounded-bl-full" />
                <div className="absolute top-4 right-4">
                  <Tooltip.Root>
                    <Tooltip.Trigger asChild>
                      <Info className="w-4 h-4 text-[#8A93B2]/50 hover:text-[#8A93B2] transition-colors cursor-help" />
                    </Tooltip.Trigger>
                    <Tooltip.Portal>
                      <Tooltip.Content className="bg-[#1A1D26] text-white px-4 py-2 rounded-lg text-sm shadow-xl border border-[#2A2E3B] max-w-xs z-50" sideOffset={5}>
                        Category Confidence — how strongly your overall data aligns with known autoimmune patterns.
                        <Tooltip.Arrow className="fill-[#2A2E3B]" />
                      </Tooltip.Content>
                    </Tooltip.Portal>
                  </Tooltip.Root>
                </div>
                <ArcGauge score={92} label="Systemic Autoimmune Alignment" color="#7B61FF" delay={0.2} />
              </motion.div>

              {/* Score Card 2: Secondary */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="dashboard-card p-8 flex flex-col items-center justify-center relative"
              >
                <div className="absolute top-0 left-0 w-24 h-24 bg-gradient-to-br from-[#F4A261]/[0.04] to-transparent rounded-br-full" />
                <div className="absolute bottom-4 left-0 right-0 text-center">
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 }}
                    className="text-xs text-[#E07070] bg-[#E07070]/[0.08] px-3 py-1.5 rounded-full border border-[#E07070]/10 font-medium"
                  >
                    This is a pattern match, not a diagnosis.
                  </motion.span>
                </div>
                <ArcGauge score={65} label="SLE Pattern Similarity" color="#F4A261" delay={0.4} small />
              </motion.div>
            </div>

            {/* ─── Trust / Safety Callout ─── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="dashboard-card glow-rose p-5 flex items-start gap-4"
              style={{ borderColor: 'rgba(224, 112, 112, 0.12)' }}
            >
              <div className="w-10 h-10 rounded-xl bg-[#E07070]/10 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-5 h-5 text-[#E07070]" />
              </div>
              <div className="text-sm text-[#8A93B2] leading-relaxed">
                <p className="font-display font-medium text-[#F0F2F8] mb-1 text-base">This is not a medical diagnosis.</p>
                <p>Aura identifies statistical patterns in your data by matching them against published medical literature.
                  Only a licensed physician can interpret these findings in the context of your full medical history.
                  These scores should be used to inform — not replace — a clinical conversation.</p>
              </div>
            </motion.div>

            {/* Gradient divider */}
            <div className="gradient-divider" />

            {/* ─── Translation Panel ─── */}
            <motion.div
              id="translation"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="scroll-target dashboard-card glow-violet p-8 lg:p-10"
            >
              <h3 className="text-xl font-display font-semibold text-[#F0F2F8] mb-8 flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#3ECFCF]/10 flex items-center justify-center">
                  <FileText className="w-[18px] h-[18px] text-[#3ECFCF]" />
                </div>
                <span className="bg-gradient-to-r from-[#F0F2F8] to-[#8A93B2] bg-clip-text text-transparent">
                  Clinical Translation
                </span>
              </h3>

              <div className="space-y-6 text-[#C0C7DC] leading-loose text-[17px] font-light">
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
            </motion.div>

            {/* ─── What This Means / What This Does Not Mean ─── */}
            <div id="next-steps" className="scroll-target grid grid-cols-1 md:grid-cols-2 gap-6">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className="dashboard-card glow-teal p-7"
                style={{ borderColor: 'rgba(62, 207, 207, 0.15)' }}
              >
                <h4 className="text-sm font-display font-semibold text-[#3ECFCF] mb-4 uppercase tracking-wider flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#3ECFCF]" />
                  What this means
                </h4>
                <ul className="space-y-3 text-sm text-[#C0C7DC] leading-relaxed">
                  <motion.li initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
                    • Your lab trends and symptoms match patterns seen in peer-reviewed autoimmune research.
                  </motion.li>
                  <motion.li initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 }}>
                    • A specialist (Rheumatologist) is the right next step to confirm or rule out these patterns.
                  </motion.li>
                  <motion.li initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.8 }}>
                    • The SOAP note gives your doctor a structured starting point backed by cited literature.
                  </motion.li>
                </ul>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className="dashboard-card glow-rose p-7"
                style={{ borderColor: 'rgba(224, 112, 112, 0.12)' }}
              >
                <h4 className="text-sm font-display font-semibold text-[#E07070] mb-4 uppercase tracking-wider flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#E07070]" />
                  What this does not mean
                </h4>
                <ul className="space-y-3 text-sm text-[#C0C7DC] leading-relaxed">
                  <motion.li initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
                    • This is <strong className="text-[#F0F2F8]">not</strong> a diagnosis of Lupus or any specific disease.
                  </motion.li>
                  <motion.li initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 }}>
                    • Pattern similarity scores reflect statistical alignment, not clinical certainty.
                  </motion.li>
                  <motion.li initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.8 }}>
                    • Only a doctor with access to your full history can make a diagnosis.
                  </motion.li>
                </ul>
              </motion.div>
            </div>

            {/* Gradient divider */}
            <div className="gradient-divider" />

            {/* ─── GP Script Callout ─── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="dashboard-card p-7 relative overflow-hidden"
              style={{ borderColor: 'rgba(62, 207, 207, 0.2)' }}
            >
              {/* Subtle gradient sweep */}
              <div className="absolute inset-0 bg-gradient-to-r from-[#3ECFCF]/[0.03] via-transparent to-[#7B61FF]/[0.03] pointer-events-none" />

              <div className="relative z-10">
                <div className="flex justify-between items-start mb-5">
                  <h4 className="font-display font-semibold text-[#3ECFCF] text-lg flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    What to say at your next appointment
                  </h4>
                </div>

                <p className="text-[15px] text-[#C0C7DC] mb-5 italic leading-relaxed pl-4 border-l-2 border-[#3ECFCF]/20">
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
                    <motion.div
                      initial={{ scale: 0.5 }}
                      animate={{ scale: 1 }}
                      className="flex items-center gap-2"
                    >
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

            {/* ─── Daily Notes ─── */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="dashboard-card p-8"
            >
              <DailyNotes />
            </motion.div>

          </div>
        </div>
      </div>
    </Tooltip.Provider>
  );
};

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