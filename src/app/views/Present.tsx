import React, { useEffect, useRef, useState } from 'react';
import { motion, useInView, useScroll, useSpring } from 'motion/react';
import { Navbar } from '../components/layout/Navbar';

// ─── Animated Counter ─────────────────────────────────────────────────────────
function useCounter(target: number, duration = 2000, start = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number | null = null;
    const step = (ts: number) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [start, target, duration]);
  return value;
}

function StatCounter({
  value, suffix = '', prefix = '', duration = 1800, label, color = '#7B61FF',
}: { value: number; suffix?: string; prefix?: string; duration?: number; label: string; color?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });
  const count = useCounter(value, duration, isInView);
  return (
    <div ref={ref} className="flex flex-col items-center gap-1">
      <span className="font-display text-5xl md:text-6xl font-semibold tracking-[0.04em]" style={{ color }}>
        {prefix}{count.toLocaleString()}{suffix}
      </span>
      <span className="text-xs text-[#8A93B2] tracking-widest uppercase text-center">{label}</span>
    </div>
  );
}

// ─── Section Label ────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block px-3 py-1 rounded-full text-xs font-mono tracking-widest uppercase border border-[#3ECFCF]/30 text-[#3ECFCF] bg-[#3ECFCF]/8 mb-6">
      {children}
    </span>
  );
}

// ─── Chart Card — standard (portrait / near-square images) ───────────────────
function ChartCard({ src, caption, className = '' }: { src: string; caption: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.93, y: 20 }}
      animate={isInView ? { opacity: 1, scale: 1, y: 0 } : {}}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl overflow-hidden border border-[#7B61FF]/15 bg-[#13161F]/65 backdrop-blur-md ${className}`}
    >
      <img src={src} alt={caption} className="w-full h-auto object-contain" />
      <p className="text-center text-[#8A93B2] text-xs px-4 py-3">{caption}</p>
    </motion.div>
  );
}

// ─── Wide Chart Card — for panoramic figures (3-panel, dual-panel, etc.) ─────
function WideChartCard({ src, caption, className = '' }: { src: string; caption: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl overflow-hidden border border-[#7B61FF]/15 bg-[#13161F]/65 backdrop-blur-md w-full ${className}`}
    >
      {/* scroll wrapper for very wide images on small screens */}
      <div className="overflow-x-auto">
        <img
          src={src}
          alt={caption}
          className="w-full min-w-[640px] h-auto object-contain"
        />
      </div>
      <p className="text-center text-[#8A93B2] text-xs px-4 py-3">{caption}</p>
    </motion.div>
  );
}

// ─── Fade-in wrapper ──────────────────────────────────────────────────────────
function FadeIn({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 28 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── Section divider ──────────────────────────────────────────────────────────
function Divider() {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="h-px bg-gradient-to-r from-transparent via-[#7B61FF]/25 to-transparent" />
    </div>
  );
}

// ─── Visual Pipeline ──────────────────────────────────────────────────────────
const PIPELINE_STEPS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <rect x="3" y="3" width="18" height="18" rx="3" />
        <path d="M7 8h10M7 12h6M7 16h8" strokeLinecap="round" />
      </svg>
    ),
    label: 'Raw Labs',
    sublabel: 'CBC · CRP · ESR\nDemographics',
    color: '#3ECFCF',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 3v3M12 18v3M4.22 6.22l2.12 2.12M17.66 15.66l2.12 2.12M3 12h3M18 12h3M4.22 17.78l2.12-2.12M17.66 8.34l2.12-2.12" strokeLinecap="round" />
        <circle cx="12" cy="12" r="4" />
      </svg>
    ),
    label: 'Z-Score Norm',
    sublabel: 'Population-adjusted\ndeviation scores',
    color: '#7B61FF',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
        <circle cx="7" cy="6" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="17" cy="18" r="1.5" fill="currentColor" stroke="none" />
      </svg>
    ),
    label: 'Visit Aggregation',
    sublabel: 'Rolling features\nacross 1–4 visits',
    color: '#F4A261',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M3 17l4-8 4 5 3-3 4 6" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="2" y="3" width="20" height="18" rx="2" />
      </svg>
    ),
    label: 'XGBoost',
    sublabel: 'Hierarchical\n4-class classifier',
    color: '#52D0A0',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3 12a9 9 0 1018 0 9 9 0 00-18 0z" />
      </svg>
    ),
    label: 'Diagnosis + Note',
    sublabel: 'Disease cluster +\nGPT-4o SOAP note',
    color: '#E07070',
  },
];

function PipelineVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <div ref={ref} className="w-full overflow-x-auto pb-2">
      <div className="flex items-stretch gap-0 min-w-[640px] relative">
        {PIPELINE_STEPS.map((step, i) => (
          <React.Fragment key={step.label}>
            {/* Step box */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.1, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="flex-1 flex flex-col items-center gap-3 px-3 py-5 rounded-2xl border bg-[#13161F]/80 backdrop-blur-md text-center relative"
              style={{ borderColor: `${step.color}25` }}
            >
              {/* Top accent bar */}
              <div className="absolute top-0 left-4 right-4 h-[2px] rounded-full" style={{ background: step.color }} />
              {/* Step number */}
              <span className="absolute top-3 right-3 text-[10px] font-mono opacity-30 text-[#8A93B2]">0{i + 1}</span>
              {/* Label */}
              <div>
                <div className="font-medium text-[#F0F2F8] text-sm">{step.label}</div>
                <div className="text-[#8A93B2] text-xs mt-1 leading-relaxed whitespace-pre-line">{step.sublabel}</div>
              </div>
            </motion.div>

            {/* Arrow connector */}
            {i < PIPELINE_STEPS.length - 1 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 1 } : {}}
                transition={{ delay: i * 0.1 + 0.15, duration: 0.4 }}
                className="flex items-center px-1 flex-shrink-0"
              >
                <svg width="28" height="20" viewBox="0 0 28 20" fill="none">
                  <path
                    d="M2 10h18M16 4l8 6-8 6"
                    stroke="url(#arrowGrad)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <defs>
                    <linearGradient id="arrowGrad" x1="0" y1="0" x2="28" y2="0" gradientUnits="userSpaceOnUse">
                      <stop stopColor={PIPELINE_STEPS[i].color} />
                      <stop offset="1" stopColor={PIPELINE_STEPS[i + 1].color} />
                    </linearGradient>
                  </defs>
                </svg>
              </motion.div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─── RAG Pipeline Visual ──────────────────────────────────────────────────────
const RAG_STEPS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 2a5 5 0 100 10A5 5 0 0012 2z" />
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round" />
      </svg>
    ),
    label: 'Patient Symptoms',
    sublabel: 'Free-text input\nfrom the patient',
    color: '#3ECFCF',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <rect x="3" y="8" width="18" height="8" rx="2" />
        <path d="M7 8V6a2 2 0 012-2h6a2 2 0 012 2v2" />
        <circle cx="8.5" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="15.5" cy="12" r="1" fill="currentColor" stroke="none" />
      </svg>
    ),
    label: 'SentenceTransformers',
    sublabel: 'S-PubMedBert\nlocal 768-dim embed',
    color: '#7B61FF',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <ellipse cx="12" cy="6" rx="8" ry="3" />
        <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" />
        <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
      </svg>
    ),
    label: 'VectorAI Search',
    sublabel: 'Actian VectorAI DB\nlocal semantic query',
    color: '#52D0A0',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
        <rect x="9" y="3" width="6" height="4" rx="1" />
        <path d="M9 12h6M9 16h4" strokeLinecap="round" />
      </svg>
    ),
    label: '90K PubMed Articles',
    sublabel: 'Ranked research\npapers retrieved',
    color: '#F4A261',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    label: 'Clinical Context',
    sublabel: 'Disease links\nresearch-grounded',
    color: '#3ECFCF',
  },
];

function RAGPipelineVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <div ref={ref} className="w-full overflow-x-auto pb-2">
      <div className="flex items-stretch gap-0 min-w-[640px] relative">
        {RAG_STEPS.map((step, i) => (
          <React.Fragment key={step.label}>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.1, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="flex-1 flex flex-col items-center gap-3 px-3 py-5 rounded-2xl border bg-[#13161F]/80 backdrop-blur-md text-center relative"
              style={{ borderColor: `${step.color}25` }}
            >
              <div className="absolute top-0 left-4 right-4 h-[2px] rounded-full" style={{ background: step.color }} />
              <span className="absolute top-3 right-3 text-[10px] font-mono opacity-30 text-[#8A93B2]">0{i + 1}</span>
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: `${step.color}18`, color: step.color, border: `1px solid ${step.color}30` }}
              >
                {step.icon}
              </div>
              <div>
                <div className="font-medium text-[#F0F2F8] text-sm">{step.label}</div>
                <div className="text-[#8A93B2] text-xs mt-1 leading-relaxed whitespace-pre-line">{step.sublabel}</div>
              </div>
            </motion.div>

            {i < RAG_STEPS.length - 1 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 1 } : {}}
                transition={{ delay: i * 0.1 + 0.15, duration: 0.4 }}
                className="flex items-center px-1 flex-shrink-0"
              >
                <svg width="28" height="20" viewBox="0 0 28 20" fill="none">
                  <path
                    d="M2 10h18M16 4l8 6-8 6"
                    stroke="url(#ragArrowGrad)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <defs>
                    <linearGradient id="ragArrowGrad" x1="0" y1="0" x2="28" y2="0" gradientUnits="userSpaceOnUse">
                      <stop stopColor={RAG_STEPS[i].color} />
                      <stop offset="1" stopColor={RAG_STEPS[i + 1].color} />
                    </linearGradient>
                  </defs>
                </svg>
              </motion.div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─── Section Nav Dots (Apple-style right rail) ───────────────────────────────
const NAV_SECTIONS = [
  { id: 's-hero',      label: 'Overview' },
  { id: 's-problem',   label: 'The Problem' },
  { id: 's-dataset',   label: 'Data' },
  { id: 's-model',     label: 'The Model' },
  { id: 's-nlp',       label: 'NLP Evaluation' },
  { id: 's-rag',       label: 'Research RAG' },
  { id: 's-early',     label: 'Early Detection' },
  { id: 's-impact',    label: 'Impact' },
  { id: 's-explore',   label: 'Exploration' },
  { id: 's-cta',       label: 'Wrap-up' },
];

function SectionNav() {
  const [active, setActive] = useState('s-hero');
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    const observers: IntersectionObserver[] = [];
    NAV_SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (!el) return;
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActive(id); },
        { threshold: 0.35 },
      );
      obs.observe(el);
      observers.push(obs);
    });
    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return (
    <div className="fixed right-6 top-1/2 -translate-y-1/2 z-[300] hidden lg:flex flex-col gap-3 items-end">
      {NAV_SECTIONS.map(({ id, label }) => (
        <button
          key={id}
          onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })}
          onMouseEnter={() => setHovered(id)}
          onMouseLeave={() => setHovered(null)}
          className="flex items-center gap-2 group"
        >
          <motion.span
            animate={{ opacity: hovered === id ? 1 : 0, x: hovered === id ? 0 : 6 }}
            className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase whitespace-nowrap"
          >
            {label}
          </motion.span>
          <motion.div
            animate={{
              width: active === id ? 20 : 6,
              backgroundColor: active === id ? '#7B61FF' : '#3A3D52',
            }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="h-[6px] rounded-full flex-shrink-0"
          />
        </button>
      ))}
    </div>
  );
}

// ─── Apple-style glass stat pill ─────────────────────────────────────────────
function StatPill({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div
      className="flex flex-col items-center px-6 py-4 rounded-2xl border bg-[#13161F]/80 backdrop-blur-md"
      style={{ borderColor: `${color}35` }}
    >
      <span className="font-display text-3xl md:text-4xl font-semibold tracking-[0.04em]" style={{ color }}>{value}</span>
      <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase mt-1 text-center">{label}</span>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export const Present = () => {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });

  return (
    <div className="relative min-h-screen text-[#F0F2F8] font-sans overflow-x-hidden">
      <Navbar />

      {/* Glass pane — frosted layer over blood cell background for readability */}
      <div className="fixed inset-0 pointer-events-none z-[1] backdrop-blur-md bg-[#020005]/35" />

      {/* Scroll progress bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-[200] h-[2px] origin-left"
        style={{ scaleX, background: 'linear-gradient(90deg, #7B61FF, #3ECFCF)' }}
      />


      {/* Section navigation dots */}
      <SectionNav />

      <div className="relative z-[2]">

      {/* ── 1. HERO ──────────────────────────────────────────────────────── */}
      <section id="s-hero" className="min-h-screen flex flex-col items-center justify-center px-6 pt-28 pb-20 text-center relative overflow-hidden">
        {/* Ambient glow */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 70% 55% at 50% 38%, rgba(123,97,255,0.10) 0%, transparent 70%)',
        }} />

        <FadeIn className="relative z-10 max-w-4xl w-full">
          {/* Event tag */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#7B61FF]/25 bg-[#7B61FF]/[0.08] backdrop-blur-md mb-8">
            <div className="w-1.5 h-1.5 rounded-full bg-[#3ECFCF] animate-pulse" />
            <span className="text-xs font-mono tracking-widest text-[#8A93B2] uppercase">Golden Byte 2026 · Aura</span>
          </div>

          {/* Headline */}
          <h1 className="font-display text-7xl md:text-9xl font-semibold tracking-[-0.01em] mb-8 leading-[0.9]">
            The{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] via-[#9B7FFF] to-[#3ECFCF] bg-clip-text text-transparent">
              4-Year Wait.
            </span>
            <br />
            <span className="text-[#F0F2F8]">Ends Now.</span>
          </h1>

          {/* Sub-copy */}
          <p className="text-lg md:text-xl text-[#8A93B2] max-w-xl mx-auto leading-relaxed mb-12">
            Autoimmune diseases affect{' '}
            <span className="text-[#F0F2F8] font-medium">50 million Americans</span>, yet the
            average patient waits{' '}
            <span className="text-[#F0F2F8] font-medium">4–7 years</span> and sees{' '}
            <span className="text-[#F0F2F8] font-medium">4–6 doctors</span> before a correct diagnosis.
          </p>

          {/* Hero stat row */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-wrap justify-center gap-3 mb-14"
          >
            <StatPill value="50M" label="Americans affected" color="#7B61FF" />
            <StatPill value="4–7 yr" label="Avg diagnostic delay" color="#3ECFCF" />
            <StatPill value="0.897" label="Model AUC" color="#52D0A0" />
            <StatPill value="$2K+" label="Saved per patient" color="#F4A261" />
          </motion.div>

          {/* Hero image */}
          <motion.div
            initial={{ opacity: 0, scale: 0.93, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 1, ease: [0.22, 1, 0.36, 1] }}
            className="relative inline-block"
          >
            <div className="absolute inset-0 rounded-3xl" style={{
              background: 'radial-gradient(ellipse at 50% 80%, rgba(123,97,255,0.28) 0%, transparent 65%)',
            }} />
            <img
              src="/assets/doctor-hero-neon.png"
              alt="Aura clinical AI"
              className="relative w-60 md:w-72 mx-auto object-contain drop-shadow-2xl"
            />
          </motion.div>
        </FadeIn>

        {/* Scroll cue */}
        <motion.div
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[#8A93B2]/60"
          animate={{ y: [0, 7, 0] }}
          transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut' }}
        >
          <span className="text-[10px] font-mono tracking-widest uppercase">Scroll</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>
      </section>

      <Divider />

      {/* ── 2. THE PROBLEM ───────────────────────────────────────────────── */}
      <section id="s-problem" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">
          {/* Section header — centered */}
          <FadeIn className="text-center mb-20">
            <SectionLabel>The Problem</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto">
              Millions living with{' '}
              <span className="bg-gradient-to-r from-[#7B61FF] to-[#9B80FF] bg-clip-text text-transparent">
                undiagnosed
              </span>{' '}
              autoimmune disease.
            </h2>
          </FadeIn>

          {/* Two-column body */}
          <div className="grid md:grid-cols-2 gap-12 items-stretch">

            {/* Left — copy + list */}
            <FadeIn>
              <p className="text-[#8A93B2] text-lg leading-relaxed mb-10">
                The immune system attacks the body's own tissues. Symptoms overlap dozens of
                conditions and are often dismissed — making early clinical diagnosis extraordinarily
                difficult without the right tools.
              </p>

              {/* Clean indicator list — no emojis */}
              <div className="space-y-4">
                {[
                  { text: '4–7 year average diagnostic delay', color: '#E07070' },
                  { text: '4–6 specialists seen before diagnosis', color: '#F4A261' },
                  { text: 'Years of inappropriate or no treatment', color: '#7B61FF' },
                  { text: 'Irreversible organ damage accumulates in delays', color: '#3ECFCF' },
                ].map((item) => (
                  <div
                    key={item.text}
                    className="flex items-center gap-4 px-5 py-4 rounded-xl border border-white/[0.07] bg-[#13161F]/70 backdrop-blur-md"
                  >
                    <div className="w-1.5 h-8 rounded-full flex-shrink-0" style={{ background: item.color }} />
                    <span className="text-[#F0F2F8]/85 text-sm leading-snug">{item.text}</span>
                  </div>
                ))}
              </div>
            </FadeIn>

            {/* Right — stat grid + quote */}
            <FadeIn delay={0.12}>
              <div className="grid grid-cols-2 gap-4 mb-6">
                {[
                  { value: 50, suffix: 'M', label: 'Americans affected', color: '#7B61FF', duration: 1600 },
                  { value: 7, prefix: 'Up to ', suffix: ' yrs', label: 'Diagnostic delay', color: '#3ECFCF', duration: 1200 },
                  { value: 6, prefix: 'Up to ', label: 'Doctors visited', color: '#F4A261', duration: 1200 },
                  { value: 100, suffix: 'B+', prefix: '$', label: 'Annual cost burden', color: '#52D0A0', duration: 1800 },
                ].map((s) => (
                  <div
                    key={s.label}
                    className="flex flex-col items-center justify-center py-6 px-4 rounded-2xl border backdrop-blur-md"
                    style={{ borderColor: `${s.color}35`, background: `${s.color}0D` }}
                  >
                    <StatCounter value={s.value} suffix={s.suffix} prefix={s.prefix} label={s.label} color={s.color} duration={s.duration} />
                  </div>
                ))}
              </div>

              {/* Pull-quote */}
              <div className="p-5 rounded-2xl border border-[#7B61FF]/20 bg-[#7B61FF]/[0.06] backdrop-blur-md relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl bg-gradient-to-b from-[#7B61FF] to-[#3ECFCF]" />
                <p className="text-[#8A93B2] text-sm leading-relaxed italic pl-2">
                  "Autoimmune diseases are notoriously hard to diagnose. Patients spend years being
                  told their symptoms are in their head."
                </p>
                <p className="text-[#7B61FF] text-xs mt-2 pl-2 font-medium">— AARDA, 2023</p>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Divider />

      {/* ── 4. THE DATASET ───────────────────────────────────────────────── */}
      <section id="s-dataset" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          {/* Header */}
          <FadeIn className="text-center mb-20">
            <SectionLabel>The Dataset</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto">
              Built on{' '}
              <span className="bg-gradient-to-r from-[#3ECFCF] to-[#52D0A0] bg-clip-text text-transparent">
                real patient data
              </span>{' '}
              from 3 sources.
            </h2>
          </FadeIn>

          {/* Copy + class breakdown side by side */}
          <div className="grid md:grid-cols-2 gap-12 items-start mb-14">
            <FadeIn>
              <p className="text-[#8A93B2] text-lg leading-relaxed">
                We harmonized <span className="text-[#F0F2F8] font-medium">48,503</span> de-identified patient records across NHANES (73.6%),
                Harvard Dataverse (24.8%), and supplementary clinical data — spanning CBC panels,
                inflammatory markers, demographics, and multi-visit trajectories.
              </p>
              {/* Source pills */}
              <div className="flex flex-wrap gap-2 mt-6">
                {[
                  { name: 'NHANES', pct: '73.6%', color: '#7B61FF' },
                  { name: 'Harvard Dataverse', pct: '24.8%', color: '#3ECFCF' },
                  { name: 'Supplementary', pct: '1.6%', color: '#F4A261' },
                ].map((s) => (
                  <div
                    key={s.name}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-md"
                    style={{ borderColor: `${s.color}35`, background: `${s.color}0D` }}
                  >
                    <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                    <span className="text-xs text-[#F0F2F8]/80">{s.name}</span>
                    <span className="text-xs font-mono" style={{ color: s.color }}>{s.pct}</span>
                  </div>
                ))}
              </div>
            </FadeIn>

            <FadeIn delay={0.1}>
              {/* Class breakdown — Apple-style table rows */}
              <div className="rounded-2xl border border-white/[0.08] bg-[#13161F]/80 backdrop-blur-md overflow-hidden">
                <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
                  <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase">Class</span>
                  <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase">Patients</span>
                </div>
                {[
                  { label: 'Healthy', n: '32,706', color: '#52D0A0', pct: 67.4 },
                  { label: 'Systemic Autoimmune', n: '13,030', color: '#7B61FF', pct: 26.9 },
                  { label: 'Endocrine Autoimmune', n: '1,966', color: '#F4A261', pct: 4.1 },
                  { label: 'GI Autoimmune', n: '801', color: '#3ECFCF', pct: 1.6 },
                ].map((c, i, arr) => (
                  <div
                    key={c.label}
                    className={`px-5 py-4 flex items-center gap-4 ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}
                  >
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c.color }} />
                    <div className="flex-1">
                      <div className="text-sm text-[#F0F2F8]/85 mb-1.5">{c.label}</div>
                      <div className="h-1 rounded-full bg-white/5 overflow-hidden w-full">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ background: c.color }}
                          initial={{ width: 0 }}
                          whileInView={{ width: `${c.pct}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.9, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
                        />
                      </div>
                    </div>
                    <span className="font-mono text-sm flex-shrink-0" style={{ color: c.color }}>{c.n}</span>
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>

          <FadeIn delay={0.15}>
            <WideChartCard
              src="/figures/01_demographics.png"
              caption="48,503 patients across 4 disease clusters: age and sex breakdown"
            />
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 4. THE MODEL ─────────────────────────────────────────────────── */}
      <section id="s-model" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-8">
            <SectionLabel>The Solution</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto mb-4">
              A hierarchical XGBoost pipeline that{' '}
              <span className="bg-gradient-to-r from-[#7B61FF] to-[#3ECFCF] bg-clip-text text-transparent">
                sees what doctors miss.
              </span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-xl mx-auto">
              Trained on 48K patients, ingesting routine labs every patient already has.
            </p>
          </FadeIn>

          {/* Pipeline */}
          <FadeIn delay={0.05} className="mb-16">
            <PipelineVisual />
          </FadeIn>

          {/* AUC score cards — prominent Apple-style row */}
          <FadeIn delay={0.1} className="mb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Systemic AUC', val: '0.963', color: '#7B61FF' },
                { label: 'Healthy AUC', val: '0.933', color: '#52D0A0' },
                { label: 'Endocrine AUC', val: '0.880', color: '#F4A261' },
                { label: 'Macro AUC', val: '0.897', color: '#3ECFCF' },
              ].map((m, i) => (
                <motion.div
                  key={m.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  className="flex flex-col items-center py-7 px-4 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                  style={{ borderColor: `${m.color}35`, background: `${m.color}0D` }}
                >
                  <div
                    className="absolute top-0 left-4 right-4 h-[2px] rounded-full"
                    style={{ background: m.color }}
                  />
                  <span className="font-display text-4xl font-semibold tracking-[0.04em] mb-1.5" style={{ color: m.color }}>{m.val}</span>
                  <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase text-center">{m.label}</span>
                </motion.div>
              ))}
            </div>
          </FadeIn>

          {/* Feature importance + ROC side by side */}
          <div className="grid md:grid-cols-2 gap-8 mb-10">
            <FadeIn delay={0.1}>
              <ChartCard
                src="/figures/08_feature_importance.png"
                caption="Feature importance (gain): CRP and ESR dominate, confirming inflammation markers as key signals"
              />
            </FadeIn>
            <FadeIn delay={0.18}>
              <ChartCard
                src="/figures/07_roc_curves.png"
                caption="ROC curves by disease cluster: Systemic AUC 0.963, Healthy AUC 0.933"
              />
            </FadeIn>
          </div>

          {/* Model comparison */}
          <FadeIn delay={0.1}>
            <WideChartCard
              src="/figures/04_model_comparison.png"
              caption="Model comparison: XGBoost leads with macro AUC 0.897 across LR, LightGBM, Random Forest, and CatBoost"
            />
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 4b. NLP EVALUATION ───────────────────────────────────────────── */}
      <section id="s-nlp" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-8">
            <SectionLabel>NLP Evaluation</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto mb-4">
              Clinical notes graded by{' '}
              <span className="bg-gradient-to-r from-[#52D0A0] to-[#3ECFCF] bg-clip-text text-transparent">
                a biomedical LLM.
              </span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-2xl mx-auto">
              The final pipeline step — SOAP note generation — is evaluated with BERTScore
              against ground-truth clinical summaries using OpenBioLLM-8B and roberta-large.
            </p>
          </FadeIn>

          {/* BERTScore metric cards */}
          <FadeIn delay={0.08} className="mb-12">
            <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
              {[
                { label: 'BERTScore F1', val: '0.8087', color: '#52D0A0' },
                { label: 'Precision', val: '0.8155', color: '#7B61FF' },
                { label: 'Recall', val: '0.8038', color: '#F4A261' },
              ].map((m, i) => (
                <motion.div
                  key={m.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  className="flex flex-col items-center py-7 px-4 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                  style={{ borderColor: `${m.color}35`, background: `${m.color}0D` }}
                >
                  <div className="absolute top-0 left-4 right-4 h-[2px] rounded-full" style={{ background: m.color }} />
                  <span className="font-display text-4xl font-semibold tracking-[0.04em] mb-1.5" style={{ color: m.color }}>{m.val}</span>
                  <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase text-center">{m.label}</span>
                </motion.div>
              ))}
            </div>
          </FadeIn>

          {/* Two charts side by side: overall + by category */}
          <div className="grid md:grid-cols-5 gap-8 mb-10">
            <FadeIn delay={0.1} className="md:col-span-2">
              <ChartCard
                src="/figures/nlp_bertscore_overall.png"
                caption="OpenBioLLM-8B overall BERTScore (roberta-large): F1 0.8087, Precision 0.8155, Recall 0.8038 — all above 0.80 baseline"
              />
            </FadeIn>
            <FadeIn delay={0.15} className="md:col-span-3">
              <WideChartCard
                src="/figures/nlp_bertscore_by_category.png"
                caption="BERTScore F1 by disease category: Systemic avg 0.801 · Gastrointestinal avg 0.812 · Endocrine avg 0.814 — consistent across all three clusters"
              />
            </FadeIn>
          </div>

          {/* Insight callout */}
          <FadeIn delay={0.18}>
            <div className="grid sm:grid-cols-3 gap-5">
              {[
                {
                  title: 'Above 0.80 across all metrics',
                  desc: 'F1, Precision, and Recall all exceed the 0.80 clinical relevance threshold — the notes read like expert summaries.',
                  color: '#52D0A0',
                  index: '01',
                },
                {
                  title: 'Consistent across disease clusters',
                  desc: 'Systemic (0.801), GI (0.812), and Endocrine (0.814) clusters score within 1.5% of each other — no cluster is left behind.',
                  color: '#3ECFCF',
                  index: '02',
                },
                {
                  title: 'Biomedical LLM, not generic GPT',
                  desc: 'OpenBioLLM-8B is fine-tuned on biomedical literature — domain knowledge reflected directly in note quality and terminology precision.',
                  color: '#7B61FF',
                  index: '03',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="p-5 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                  style={{ borderColor: `${item.color}25`, background: `${item.color}08` }}
                >
                  <div className="absolute top-0 left-5 right-5 h-[2px] rounded-full" style={{ background: item.color }} />
                  <span className="font-mono text-[10px] text-[#8A93B2]/40 tracking-widest absolute top-4 right-4">{item.index}</span>
                  <div className="font-medium text-sm mb-2 mt-3" style={{ color: item.color }}>{item.title}</div>
                  <div className="text-[#8A93B2] text-xs leading-relaxed">{item.desc}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 4c. RAG SYSTEM ───────────────────────────────────────────────── */}
      <section id="s-rag" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-8">
            <SectionLabel>Research Intelligence</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto mb-4">
              90,000 PubMed papers.{' '}
              <span className="bg-gradient-to-r from-[#52D0A0] to-[#3ECFCF] bg-clip-text text-transparent">
                Zero data leaves.
              </span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-2xl mx-auto">
              A fully local RAG system built on Actian VectorAI DB — patient symptoms are matched
              against a curated corpus of autoimmune research without ever touching an external server.
            </p>
          </FadeIn>

          {/* Privacy trust bar */}
          <FadeIn delay={0.06} className="mb-12">
            <div className="flex flex-wrap justify-center gap-3">
              {[
                { icon: (
                    <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="1.6">
                      <path d="M8 14s6-3 6-7.5V3L8 1 2 3v3.5C2 11 8 14 8 14z" />
                    </svg>
                  ), text: 'VectorAI DB — local only', color: '#52D0A0' },
                { icon: (
                    <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="1.6">
                      <rect x="3" y="6" width="10" height="8" rx="1.5" />
                      <path d="M5.5 6V4.5a2.5 2.5 0 015 0V6" strokeLinecap="round" />
                    </svg>
                  ), text: 'SentenceTransformers — local embeddings', color: '#3ECFCF' },
                { icon: (
                    <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="1.6">
                      <circle cx="8" cy="8" r="6" />
                      <path d="M8 5v3l2 2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ), text: 'No external API calls', color: '#7B61FF' },
                { icon: (
                    <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5" stroke="currentColor" strokeWidth="1.6">
                      <path d="M2 8h12M2 4h12M2 12h8" strokeLinecap="round" />
                    </svg>
                  ), text: 'HIPAA-aligned architecture', color: '#F4A261' },
              ].map((badge) => (
                <div
                  key={badge.text}
                  className="flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-md"
                  style={{ borderColor: `${badge.color}35`, background: `${badge.color}0D`, color: badge.color }}
                >
                  {badge.icon}
                  <span className="text-xs font-mono tracking-wide" style={{ color: badge.color }}>{badge.text}</span>
                </div>
              ))}
            </div>
          </FadeIn>

          {/* RAG Pipeline */}
          <FadeIn delay={0.08} className="mb-14">
            <RAGPipelineVisual />
          </FadeIn>

          {/* Privacy + scale callout — two-column */}
          <div className="grid md:grid-cols-2 gap-8 mb-12">

            {/* Left — privacy architecture */}
            <FadeIn delay={0.1}>
              <div className="h-full rounded-2xl border border-[#52D0A0]/20 bg-[#52D0A0]/[0.04] backdrop-blur-md overflow-hidden">
                {/* Header bar */}
                <div className="px-6 py-4 border-b border-white/5 flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-[#52D0A0]/15 border border-[#52D0A0]/25">
                    <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4" stroke="#52D0A0" strokeWidth="1.5">
                      <path d="M8 14s6-3 6-7.5V3L8 1 2 3v3.5C2 11 8 14 8 14z" />
                      <path d="M5.5 8l2 2L11 6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <span className="text-[10px] font-mono tracking-widest text-[#52D0A0] uppercase">Privacy Architecture</span>
                </div>

                <div className="px-6 py-5 space-y-4">
                  {[
                    {
                      component: 'Actian VectorAI DB',
                      detail: 'Runs entirely on-premise. Patient queries never leave the hospital environment.',
                      status: 'Local',
                      color: '#52D0A0',
                    },
                    {
                      component: 'SentenceTransformers (S-PubMedBert-MS-MARCO)',
                      detail: 'Biomedical embedding model runs locally. 768-dim vectors generated with no cloud dependency.',
                      status: 'Local',
                      color: '#3ECFCF',
                    },
                    {
                      component: 'PubMed Corpus',
                      detail: '90,000+ articles indexed once at setup. All lookups happen against a local snapshot.',
                      status: 'Static',
                      color: '#7B61FF',
                    },
                  ].map((item, i, arr) => (
                    <div
                      key={item.component}
                      className={`flex items-start gap-4 pb-4 ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}
                    >
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0 mt-2"
                        style={{ background: item.color, boxShadow: `0 0 6px ${item.color}80` }}
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-[#F0F2F8]/90">{item.component}</span>
                          <span
                            className="text-[9px] font-mono tracking-widest px-2 py-0.5 rounded-full border"
                            style={{ color: item.color, borderColor: `${item.color}40`, background: `${item.color}12` }}
                          >
                            {item.status}
                          </span>
                        </div>
                        <p className="text-[#8A93B2] text-xs leading-relaxed">{item.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </FadeIn>

            {/* Right — scale + how it works */}
            <FadeIn delay={0.14}>
              <div className="flex flex-col gap-5 h-full">
                {/* Stat cards */}
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { val: '90K+', label: 'PubMed Articles Indexed', color: '#F4A261' },
                    { val: '100%', label: 'Locally Processed', color: '#52D0A0' },
                  ].map((s, i) => (
                    <motion.div
                      key={s.label}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.14 + i * 0.06, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                      className="flex flex-col items-center py-6 px-4 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                      style={{ borderColor: `${s.color}35`, background: `${s.color}0D` }}
                    >
                      <div className="absolute top-0 left-4 right-4 h-[2px] rounded-full" style={{ background: s.color }} />
                      <span className="font-display text-3xl font-semibold tracking-[0.04em] mb-1" style={{ color: s.color }}>{s.val}</span>
                      <span className="text-[10px] font-mono tracking-widest text-[#8A93B2] uppercase text-center">{s.label}</span>
                    </motion.div>
                  ))}
                </div>

                {/* How it works callout */}
                <div className="flex-1 p-5 rounded-2xl border border-[#7B61FF]/20 bg-[#7B61FF]/[0.05] backdrop-blur-md relative overflow-hidden">
                  <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl bg-gradient-to-b from-[#3ECFCF] to-[#52D0A0]" />
                  <p className="text-[10px] font-mono tracking-widest text-[#3ECFCF] uppercase mb-3 pl-2">How It Works</p>
                  <div className="space-y-3 pl-2">
                    {[
                      'Patient enters symptoms in free text',
                      'SentenceTransformers (S-PubMedBert-MS-MARCO) encodes text into 768-dim vectors locally',
                      'Actian VectorAI DB performs cosine similarity search',
                      'Top-ranked PubMed papers surface disease-symptom links',
                      'Retrieved context grounds the model\'s differential output',
                    ].map((step, i) => (
                      <div key={step} className="flex items-start gap-3">
                        <span className="font-mono text-[10px] text-[#3ECFCF]/50 flex-shrink-0 mt-0.5 w-4">{i + 1}.</span>
                        <span className="text-[#8A93B2] text-xs leading-snug">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </FadeIn>
          </div>

          {/* Bottom insight cards */}
          <FadeIn delay={0.2}>
            <div className="grid sm:grid-cols-3 gap-5">
              {[
                {
                  title: 'Research-grounded, not hallucinated',
                  desc: 'Every disease connection is backed by a real PubMed citation retrieved at query time — no generative fabrication.',
                  color: '#52D0A0',
                  index: '01',
                },
                {
                  title: 'Air-gapped by design',
                  desc: 'VectorAI DB and vLLM both run locally. No symptom data, embeddings, or results ever transit to a third-party service.',
                  color: '#3ECFCF',
                  index: '02',
                },
                {
                  title: 'Autoimmune-specialized corpus',
                  desc: '90,000+ articles curated from PubMed specifically around autoimmune pathology, lab markers, and clinical presentations.',
                  color: '#7B61FF',
                  index: '03',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="p-5 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                  style={{ borderColor: `${item.color}25`, background: `${item.color}08` }}
                >
                  <div className="absolute top-0 left-5 right-5 h-[2px] rounded-full" style={{ background: item.color }} />
                  <span className="font-mono text-[10px] text-[#8A93B2]/40 tracking-widest absolute top-4 right-4">{item.index}</span>
                  <div className="font-medium text-sm mb-2 mt-3" style={{ color: item.color }}>{item.title}</div>
                  <div className="text-[#8A93B2] text-xs leading-relaxed">{item.desc}</div>
                </div>
              ))}
            </div>
          </FadeIn>

        </div>
      </section>

      <Divider />

      {/* ── 5. EARLY DETECTION ───────────────────────────────────────────── */}
      <section id="s-early" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-14">
            <SectionLabel>Early Detection</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto mb-6">
              Confident at{' '}
              <span className="bg-gradient-to-r from-[#52D0A0] to-[#3ECFCF] bg-clip-text text-transparent">
                Visit 1.
              </span>
              <br />Before symptoms escalate.
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-xl mx-auto leading-relaxed">
              Using only demographics and a basic CBC from the very first visit, the model
              already flags systemic autoimmune disease at{' '}
              <span className="text-[#F0F2F8] font-medium">72% confidence</span>.
              For healthy patients, it avoids unnecessary workups — saving visits and cost.
            </p>
          </FadeIn>

          {/* Two outcome pills */}
          <FadeIn delay={0.1} className="mb-14">
            <div className="grid sm:grid-cols-2 gap-5 max-w-2xl mx-auto">
              {[
                { dot: '#52D0A0', name: 'Healthy patients', pct: '98%', sub: 'correctly cleared — save 3 specialist visits' },
                { dot: '#7B61FF', name: 'Systemic autoimmune', pct: '99%', sub: 'correctly flagged — save 1+ specialist visits' },
              ].map((c) => (
                <div
                  key={c.name}
                  className="flex flex-col items-center py-8 px-6 rounded-2xl border backdrop-blur-md text-center"
                  style={{ borderColor: `${c.dot}35`, background: `${c.dot}0D` }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full" style={{ background: c.dot }} />
                    <span className="text-xs font-mono tracking-widest uppercase" style={{ color: c.dot }}>{c.name}</span>
                  </div>
                  <span className="font-display text-5xl font-semibold tracking-[0.04em] mb-1" style={{ color: c.dot }}>{c.pct}</span>
                  <span className="text-[#8A93B2] text-xs leading-relaxed max-w-[180px]">{c.sub}</span>
                </div>
              ))}
            </div>
          </FadeIn>

          <FadeIn delay={0.15}>
            <WideChartCard
              src="/figures/07_cost_savings.png"
              caption="Visits saved per patient and estimated cost savings by disease cluster"
            />
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 6. IMPACT ────────────────────────────────────────────────────── */}
      <section id="s-impact" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-20">
            <SectionLabel>The Impact</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-2xl mx-auto mb-4">
              <span className="bg-gradient-to-r from-[#F4A261] to-[#FFD580] bg-clip-text text-transparent">
                $2,059
              </span>{' '}
              saved per patient.
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-xl mx-auto">
              By flagging autoimmune patterns early, Aura eliminates unnecessary specialist
              referrals, repeat testing, and months of diagnostic limbo.
            </p>
          </FadeIn>

          <div className="grid md:grid-cols-5 gap-6 items-stretch">

            {/* Left col — financial breakdown table (3 cols wide) */}
            <FadeIn delay={0.08} className="md:col-span-3 flex flex-col">
              {/* Headline stat */}
              <div className="flex justify-around py-8 rounded-2xl border border-[#F4A261]/20 bg-[#F4A261]/[0.05] backdrop-blur-md mb-4">
                <StatCounter value={2059} prefix="$" label="Saved per healthy patient" color="#F4A261" duration={2000} />
                <div className="w-px bg-white/5" />
                <StatCounter value={707} prefix="$" label="Saved per systemic patient" color="#7B61FF" duration={1600} />
              </div>

              {/* National scale table */}
              <div className="flex-1 rounded-2xl border border-[#3ECFCF]/20 bg-[#3ECFCF]/[0.05] backdrop-blur-md overflow-hidden">
                <div className="px-6 py-3 border-b border-white/5">
                  <span className="text-[10px] font-mono tracking-widest text-[#3ECFCF] uppercase">At National Scale</span>
                </div>
                {[
                  ['50M patients in the US', '50,000,000', '#F0F2F8'],
                  ['Avg specialist visits avoided', '1–3', '#F0F2F8'],
                  ['Cost per visit avoided', '$700', '#F0F2F8'],
                  ['Potential US savings', '$35–100B', '#F4A261'],
                ].map(([k, v, c], i, arr) => (
                  <div
                    key={String(k)}
                    className={`flex justify-between items-center px-6 py-4 ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}
                  >
                    <span className="text-[#8A93B2] text-sm">{k}</span>
                    <span className="font-mono text-sm font-medium" style={{ color: c }}>{v}</span>
                  </div>
                ))}
              </div>
            </FadeIn>

            {/* Right col — beyond cost list (2 cols wide) */}
            <FadeIn delay={0.16} className="md:col-span-2 flex flex-col">
              <div className="flex-1 rounded-2xl border border-[#7B61FF]/20 bg-[#7B61FF]/[0.05] backdrop-blur-md overflow-hidden">
                <div className="px-6 py-3 border-b border-white/5">
                  <span className="text-[10px] font-mono tracking-widest text-[#7B61FF] uppercase">Beyond Cost</span>
                </div>
                <div className="px-6 py-5 space-y-4">
                  {[
                    'Earlier treatment prevents irreversible organ damage',
                    'Reduces diagnostic odyssey and patient mental burden',
                    'Works from routine labs, no new tests required',
                    'Equitable across age groups and both sexes',
                    'SOAP note generation ready for clinical workflow',
                  ].map((t) => (
                    <div key={t} className="flex items-start gap-3">
                      <div className="w-4 h-4 rounded-full border border-[#52D0A0]/40 bg-[#52D0A0]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                          <path d="M1.5 4l2 2L6.5 2" stroke="#52D0A0" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <span className="text-[#8A93B2] text-sm leading-snug">{t}</span>
                    </div>
                  ))}
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Divider />

      {/* ── 7. DATA EXPLORATION ──────────────────────────────────────────── */}
      <section id="s-explore" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-20">
            <SectionLabel>Data Exploration</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-semibold tracking-[0.02em] leading-tight max-w-3xl mx-auto mb-4">
              Understanding the data{' '}
              <span className="bg-gradient-to-r from-[#3ECFCF] to-[#7B61FF] bg-clip-text text-transparent">
                before the model.
              </span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-xl mx-auto">
              Rigorous EDA informed every modeling decision — from feature selection to
              class balancing and Z-score normalization.
            </p>
          </FadeIn>

          {/* Source & cluster distribution */}
          <FadeIn delay={0.05} className="mb-8">
            <WideChartCard
              src="/figures/01_source_distribution.png"
              caption="Data sources: NHANES (73.6%) and Harvard Dataverse (24.8%), cluster distribution varies meaningfully by source"
            />
          </FadeIn>
          <FadeIn delay={0.08} className="mb-8">
            <WideChartCard
              src="/figures/01_cluster_distribution.png"
              caption="Disease cluster distribution across the full dataset"
            />
          </FadeIn>

          {/* Z-score + correlation matrix side by side */}
          <div className="grid md:grid-cols-5 gap-8 mb-10">
            <FadeIn delay={0.1} className="md:col-span-3">
              <WideChartCard
                src="/figures/05_zscore_analysis.png"
                caption="Z-score distributions: normalization reveals population-level deviations per cluster"
              />
            </FadeIn>
            <FadeIn delay={0.14} className="md:col-span-2">
              <ChartCard
                src="/figures/02_feature_correlation.png"
                caption="Feature correlation matrix: Hemoglobin/Hematocrit tightly correlated (0.95)"
              />
            </FadeIn>
          </div>

          {/* Key findings — 3 insight cards */}
          <FadeIn delay={0.15}>
            <div className="grid sm:grid-cols-3 gap-5">
              {[
                {
                  title: 'CRP & ESR are independent',
                  desc: 'Low correlation between each other despite both being inflammation markers. The model benefits from both.',
                  color: '#7B61FF',
                  index: '01',
                },
                {
                  title: 'Hemoglobin ↔ Hematocrit: r = 0.95',
                  desc: 'Near-perfect collinearity. Z-score features break this dependency by adjusting for population context.',
                  color: '#3ECFCF',
                  index: '02',
                },
                {
                  title: 'Neutrophil ↔ Lymphocyte: r = −0.84',
                  desc: 'Strong inverse relationship reflects the classic inflammatory shift, a key biomarker pattern for autoimmune detection.',
                  color: '#F4A261',
                  index: '03',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="p-5 rounded-2xl border backdrop-blur-md relative overflow-hidden"
                  style={{ borderColor: `${item.color}25`, background: `${item.color}08` }}
                >
                  <div className="absolute top-0 left-5 right-5 h-[2px] rounded-full" style={{ background: item.color }} />
                  <span className="font-mono text-[10px] text-[#8A93B2]/40 tracking-widest absolute top-4 right-4">{item.index}</span>
                  <div className="font-medium text-sm mb-2 mt-3" style={{ color: item.color }}>{item.title}</div>
                  <div className="text-[#8A93B2] text-xs leading-relaxed">{item.desc}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 8. CLOSING CTA ───────────────────────────────────────────────── */}
      <section id="s-cta" className="min-h-[80vh] flex flex-col items-center justify-center px-6 py-28 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 70% 55% at 50% 52%, rgba(62,207,207,0.09) 0%, rgba(123,97,255,0.05) 40%, transparent 70%)',
        }} />

        <FadeIn className="relative z-10 max-w-3xl w-full">
          {/* Tag */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#7B61FF]/25 bg-[#7B61FF]/[0.08] backdrop-blur-md mb-10">
            <div className="w-1.5 h-1.5 rounded-full bg-[#7B61FF] animate-pulse" />
            <span className="text-xs font-mono tracking-widest text-[#8A93B2] uppercase">Aura · Golden Byte 2026</span>
          </div>

          {/* Headline */}
          <h2 className="font-display text-6xl md:text-8xl font-semibold mb-6 leading-[0.88] tracking-[-0.01em]">
            Routine labs.{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] via-[#9B7FFF] to-[#3ECFCF] bg-clip-text text-transparent">
              Extraordinary insight.
            </span>
          </h2>

          <p className="text-[#8A93B2] text-lg mb-14 max-w-lg mx-auto leading-relaxed">
            Aura sits at the intersection of clinical AI and patient equity — transforming data
            every physician already has into a life-changing early warning system.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-20">
            <a
              href="/"
              className="px-9 py-4 rounded-xl font-medium text-white text-sm tracking-wide transition-all hover:scale-105 active:scale-[0.98] shadow-lg"
              style={{ background: 'linear-gradient(135deg, #7B61FF, #2563EB)' }}
            >
              Try Aura Live
            </a>
            <a
              href="/clinician"
              className="px-9 py-4 rounded-xl font-medium text-sm tracking-wide border border-[#3ECFCF]/30 text-[#3ECFCF] hover:bg-[#3ECFCF]/8 transition-all hover:scale-105 active:scale-[0.98] backdrop-blur-md"
            >
              Clinician Portal
            </a>
          </div>

          {/* Final stats strip */}
          <div className="grid grid-cols-3 gap-5 max-w-md mx-auto">
            {[
              { val: '0.90', label: 'AUC Score', color: '#7B61FF' },
              { val: '48K', label: 'Patients Trained', color: '#3ECFCF' },
              { val: '$2K+', label: 'Saved / Patient', color: '#F4A261' },
            ].map((s) => (
              <div
                key={s.label}
                className="flex flex-col items-center py-5 px-3 rounded-2xl border backdrop-blur-md"
                style={{ borderColor: `${s.color}35`, background: `${s.color}0D` }}
              >
                <span className="font-display text-2xl font-semibold tracking-[0.04em]" style={{ color: s.color }}>{s.val}</span>
                <span className="text-[9px] font-mono tracking-widest text-[#8A93B2] uppercase mt-1.5 text-center">{s.label}</span>
              </div>
            ))}
          </div>
        </FadeIn>
      </section>

      </div>{/* end z-[2] content wrapper */}
    </div>
  );
};
