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
      <span className="font-display text-5xl md:text-6xl font-light" style={{ color }}>
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

// ─── Section Nav Dots (Apple-style right rail) ───────────────────────────────
const NAV_SECTIONS = [
  { id: 's-hero',      label: 'Overview' },
  { id: 's-problem',   label: 'The Problem' },
  { id: 's-dataset',   label: 'Data' },
  { id: 's-model',     label: 'The Model' },
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
      className="flex flex-col items-center px-6 py-4 rounded-2xl border bg-white/[0.04] backdrop-blur-xl"
      style={{ borderColor: `${color}20` }}
    >
      <span className="font-display text-3xl md:text-4xl font-light" style={{ color }}>{value}</span>
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

      {/* Pulsoid heart rate widget */}
      <iframe
        src="https://pulsoid.net/widget/view/41ec10fc-556a-40e4-99f8-49776c9a8498"
        className="fixed top-4 right-4 z-[199]"
        style={{ width: 150, height: 80, border: 'none', background: 'transparent' }}
        title="Heart Rate"
        allow="fullscreen"
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
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/[0.04] backdrop-blur-xl mb-8">
            <div className="w-1.5 h-1.5 rounded-full bg-[#3ECFCF] animate-pulse" />
            <span className="text-xs font-mono tracking-widest text-[#8A93B2] uppercase">Golden Byte 2026 · Aura</span>
          </div>

          {/* Headline */}
          <h1 className="font-display text-7xl md:text-9xl font-light tracking-tight mb-8 leading-[0.92]">
            The{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] via-[#9B7FFF] to-[#3ECFCF] bg-clip-text text-transparent">
              4-Year Wait.
            </span>
            <br />
            <span className="text-[#F0F2F8]/90">Ends Now.</span>
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
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-3xl mx-auto">
              Millions living with{' '}
              <span style={{ background: 'linear-gradient(90deg,#7B61FF,#9B80FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
                    className="flex items-center gap-4 px-5 py-4 rounded-xl border border-white/5 bg-white/[0.03] backdrop-blur-sm"
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
                    className="flex flex-col items-center justify-center py-6 px-4 rounded-2xl border bg-white/[0.035] backdrop-blur-xl"
                    style={{ borderColor: `${s.color}20` }}
                  >
                    <StatCounter value={s.value} suffix={s.suffix} prefix={s.prefix} label={s.label} color={s.color} duration={s.duration} />
                  </div>
                ))}
              </div>

              {/* Pull-quote */}
              <div className="p-5 rounded-2xl border border-[#7B61FF]/15 bg-white/[0.03] backdrop-blur-xl relative overflow-hidden">
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

      {/* ── 3. THE DATASET ───────────────────────────────────────────────── */}
      <section id="s-dataset" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          {/* Header */}
          <FadeIn className="text-center mb-20">
            <SectionLabel>The Dataset</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-3xl mx-auto">
              Built on{' '}
              <span style={{ background: 'linear-gradient(90deg,#3ECFCF,#52D0A0)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-white/[0.04]"
                    style={{ borderColor: `${s.color}30` }}
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
              <div className="rounded-2xl border border-white/8 bg-white/[0.03] backdrop-blur-xl overflow-hidden">
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
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-3xl mx-auto mb-4">
              A hierarchical XGBoost pipeline that{' '}
              <span style={{ background: 'linear-gradient(90deg,#7B61FF,#9B80FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
                  className="flex flex-col items-center py-7 px-4 rounded-2xl border bg-white/[0.035] backdrop-blur-xl relative overflow-hidden"
                  style={{ borderColor: `${m.color}22` }}
                >
                  <div
                    className="absolute top-0 left-4 right-4 h-[2px] rounded-full"
                    style={{ background: m.color }}
                  />
                  <span className="font-display text-4xl font-light mb-1.5" style={{ color: m.color }}>{m.val}</span>
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

      {/* ── 5. EARLY DETECTION ───────────────────────────────────────────── */}
      <section id="s-early" className="py-32 px-6">
        <div className="max-w-6xl mx-auto w-full">

          <FadeIn className="text-center mb-14">
            <SectionLabel>Early Detection</SectionLabel>
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-3xl mx-auto mb-6">
              Confident at{' '}
              <span style={{ background: 'linear-gradient(90deg,#52D0A0,#3ECFCF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
                  className="flex flex-col items-center py-8 px-6 rounded-2xl border bg-white/[0.035] backdrop-blur-xl text-center"
                  style={{ borderColor: `${c.dot}25` }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full" style={{ background: c.dot }} />
                    <span className="text-xs font-mono tracking-widest uppercase" style={{ color: c.dot }}>{c.name}</span>
                  </div>
                  <span className="font-display text-5xl font-light mb-1" style={{ color: c.dot }}>{c.pct}</span>
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
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-2xl mx-auto mb-4">
              <span style={{ background: 'linear-gradient(90deg,#F4A261,#FFD580)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
              <div className="flex justify-around py-8 rounded-2xl border border-[#F4A261]/15 bg-white/[0.03] backdrop-blur-xl mb-4">
                <StatCounter value={2059} prefix="$" label="Saved per healthy patient" color="#F4A261" duration={2000} />
                <div className="w-px bg-white/5" />
                <StatCounter value={707} prefix="$" label="Saved per systemic patient" color="#7B61FF" duration={1600} />
              </div>

              {/* National scale table */}
              <div className="flex-1 rounded-2xl border border-[#3ECFCF]/15 bg-white/[0.03] backdrop-blur-xl overflow-hidden">
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
              <div className="flex-1 rounded-2xl border border-[#7B61FF]/15 bg-white/[0.03] backdrop-blur-xl overflow-hidden">
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
            <h2 className="font-display text-5xl md:text-6xl font-light leading-tight max-w-3xl mx-auto mb-4">
              Understanding the data{' '}
              <span style={{ background: 'linear-gradient(90deg,#3ECFCF,#7B61FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
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
                  className="p-5 rounded-2xl border border-white/5 bg-white/[0.03] backdrop-blur-xl relative overflow-hidden"
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
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/[0.04] backdrop-blur-xl mb-10">
            <div className="w-1.5 h-1.5 rounded-full bg-[#7B61FF] animate-pulse" />
            <span className="text-xs font-mono tracking-widest text-[#8A93B2] uppercase">Aura · Golden Byte 2026</span>
          </div>

          {/* Headline */}
          <h2 className="font-display text-6xl md:text-8xl font-light mb-6 leading-[0.92] tracking-tight">
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
              className="px-9 py-4 rounded-xl font-medium text-sm tracking-wide border border-[#3ECFCF]/30 text-[#3ECFCF] hover:bg-[#3ECFCF]/8 transition-all hover:scale-105 active:scale-[0.98] backdrop-blur-xl"
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
                className="flex flex-col items-center py-5 px-3 rounded-2xl border bg-white/[0.04] backdrop-blur-xl"
                style={{ borderColor: `${s.color}20` }}
              >
                <span className="font-display text-2xl font-light" style={{ color: s.color }}>{s.val}</span>
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
