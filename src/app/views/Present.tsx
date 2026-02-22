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
              {/* Icon */}
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: `${step.color}18`, color: step.color }}
              >
                {step.icon}
              </div>
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

// ─── Main Page ────────────────────────────────────────────────────────────────
export const Present = () => {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });

  return (
    <div className="relative min-h-screen text-[#F0F2F8] font-sans overflow-x-hidden">
      <Navbar />

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

      {/* ── 1. HERO ──────────────────────────────────────────────────────── */}
      <section className="min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-16 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(123,97,255,0.08) 0%, transparent 70%)'
        }} />
        <FadeIn className="relative z-10 max-w-4xl">
          <SectionLabel>Golden Byte 2026 · Aura</SectionLabel>
          <h1 className="font-display text-6xl md:text-8xl font-light tracking-tight mb-6 leading-none">
            The{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] to-[#3ECFCF] bg-clip-text text-transparent">
              4-Year Wait.
            </span>
            <br />Ends Now.
          </h1>
          <p className="text-lg md:text-xl text-[#8A93B2] max-w-2xl mx-auto leading-relaxed mb-10">
            Autoimmune diseases affect <span className="text-[#F0F2F8]">50 million Americans</span> — yet the
            average patient waits <span className="text-[#F0F2F8]">4–7 years</span> and sees{' '}
            <span className="text-[#F0F2F8]">4–6 doctors</span> before a correct diagnosis.
            Aura changes that with AI and routine labs.
          </p>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
            className="relative inline-block"
          >
            <div className="absolute inset-0 rounded-3xl" style={{
              background: 'radial-gradient(ellipse at 50% 80%, rgba(123,97,255,0.25) 0%, transparent 60%)'
            }} />
            <img src="/assets/doctor-hero-neon.png" alt="Aura clinical AI"
              className="relative w-64 md:w-80 mx-auto object-contain drop-shadow-2xl" />
          </motion.div>
        </FadeIn>
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-[#8A93B2] text-xs tracking-widest uppercase"
          animate={{ y: [0, 6, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          <span>Scroll</span>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>
      </section>

      <Divider />

      {/* ── 2. THE PROBLEM ───────────────────────────────────────────────── */}
      <section className="min-h-screen flex items-center px-6 py-24">
        <div className="max-w-6xl mx-auto w-full grid md:grid-cols-2 gap-16 items-center">
          <FadeIn>
            <SectionLabel>The Problem</SectionLabel>
            <h2 className="font-display text-4xl md:text-5xl font-light mb-6 leading-tight">
              Millions living with{' '}
              <span className="text-[#7B61FF]">undiagnosed</span>{' '}
              autoimmune disease.
            </h2>
            <p className="text-[#8A93B2] text-lg leading-relaxed mb-8">
              The immune system attacks the body's own tissues. Symptoms overlap dozens of conditions
              and are often dismissed — making early clinical diagnosis extraordinarily difficult
              without the right tools.
            </p>
            <div className="space-y-3">
              {[
                { icon: '⏱', text: '4–7 year average diagnostic delay' },
                { icon: '🏥', text: '4–6 specialists seen before diagnosis' },
                { icon: '💊', text: 'Years of inappropriate or no treatment' },
                { icon: '🧠', text: 'Irreversible organ damage accumulates in delays' },
              ].map((item) => (
                <div key={item.text} className="flex items-center gap-3 text-[#F0F2F8]/80">
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>
          </FadeIn>

          <FadeIn delay={0.15}>
            <div className="grid grid-cols-2 gap-6 mb-8">
              <StatCounter value={50} suffix="M" label="Americans affected" color="#7B61FF" duration={1600} />
              <StatCounter value={7} prefix="Up to " suffix=" yrs" label="Diagnostic delay" color="#3ECFCF" duration={1200} />
              <StatCounter value={6} prefix="Up to " label="Doctors visited" color="#F4A261" duration={1200} />
              <StatCounter value={100} suffix="B+" prefix="$" label="Annual cost burden" color="#52D0A0" duration={1800} />
            </div>
            <div className="p-4 rounded-xl border border-[#7B61FF]/15 bg-[#13161F]/65 backdrop-blur-md">
              <p className="text-[#8A93B2] text-sm leading-relaxed text-center italic">
                "Autoimmune diseases are notoriously hard to diagnose. Patients spend years being told their symptoms are in their head."
              </p>
              <p className="text-[#7B61FF] text-xs text-center mt-2">— AARDA, 2023</p>
            </div>
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 3. THE DATASET ───────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto w-full">
          <div className="grid md:grid-cols-2 gap-16 items-start mb-12">
            <FadeIn>
              <SectionLabel>The Dataset</SectionLabel>
              <h2 className="font-display text-4xl md:text-5xl font-light mb-6 leading-tight">
                Built on <span className="text-[#3ECFCF]">real patient data</span> from 3 sources.
              </h2>
              <p className="text-[#8A93B2] text-lg leading-relaxed mb-8">
                We harmonized 48,503 de-identified patient records across NHANES (73.6%), Harvard
                Dataverse (24.8%), and supplementary clinical data — spanning CBC panels, inflammatory
                markers, demographics, and multi-visit trajectories.
              </p>
            </FadeIn>
            <FadeIn delay={0.1}>
              <div className="grid grid-cols-2 gap-3 mt-2">
                {[
                  { label: 'Healthy', n: '32,706', color: '#52D0A0' },
                  { label: 'Systemic Autoimmune', n: '13,030', color: '#7B61FF' },
                  { label: 'GI Autoimmune', n: '801', color: '#3ECFCF' },
                  { label: 'Endocrine Autoimmune', n: '1,966', color: '#F4A261' },
                ].map((c) => (
                  <div
                    key={c.label}
                    className="p-3 rounded-lg border border-white/5 bg-[#13161F]/65"
                    style={{ borderLeftColor: c.color, borderLeftWidth: 3 }}
                  >
                    <div className="font-mono text-lg" style={{ color: c.color }}>{c.n}</div>
                    <div className="text-[#8A93B2] text-xs">{c.label}</div>
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>
          <FadeIn delay={0.15}>
            <WideChartCard
              src="/figures/01_demographics.png"
              caption="48,503 patients across 4 disease clusters — age and sex breakdown"
            />
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 4. THE MODEL ─────────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto w-full">
          <FadeIn className="text-center mb-12">
            <SectionLabel>The Solution</SectionLabel>
            <h2 className="font-display text-4xl md:text-5xl font-light mb-4 leading-tight">
              A hierarchical XGBoost pipeline that{' '}
              <span className="text-[#7B61FF]">sees what doctors miss.</span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-2xl mx-auto">
              Trained on 48K patients, ingesting routine labs every patient already has.
            </p>
          </FadeIn>

          {/* Visual pipeline */}
          <FadeIn delay={0.05} className="mb-14">
            <PipelineVisual />
          </FadeIn>

          {/* Feature importance + AUC metrics */}
          <div className="grid md:grid-cols-2 gap-10 mb-10">
            <FadeIn delay={0.1}>
              <ChartCard
                src="/figures/08_feature_importance.png"
                caption="Feature importance (gain) — CRP and ESR dominate, confirming inflammation markers as key signals"
              />
            </FadeIn>
            <FadeIn delay={0.2}>
              <ChartCard
                src="/figures/07_roc_curves.png"
                caption="ROC curves by disease cluster — Systemic AUC 0.963, Healthy AUC 0.933"
              />
              <div className="grid grid-cols-4 gap-2 mt-4">
                {[
                  { label: 'Systemic', val: '0.963', color: '#7B61FF' },
                  { label: 'Healthy', val: '0.933', color: '#52D0A0' },
                  { label: 'Endocrine', val: '0.880', color: '#F4A261' },
                  { label: 'Overall', val: '0.897', color: '#3ECFCF' },
                ].map((m) => (
                  <div key={m.label} className="p-3 rounded-xl border border-white/5 bg-[#13161F]/65 text-center">
                    <div className="font-mono text-xl font-light" style={{ color: m.color }}>{m.val}</div>
                    <div className="text-[#8A93B2] text-[10px] mt-0.5">{m.label}</div>
                  </div>
                ))}
              </div>
            </FadeIn>
          </div>

          {/* Model comparison — wide, full-width */}
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
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto w-full">
          <FadeIn className="text-center mb-12 max-w-3xl mx-auto">
            <SectionLabel>Early Detection</SectionLabel>
            <h2 className="font-display text-4xl md:text-5xl font-light mb-6 leading-tight">
              Confident at <span className="text-[#52D0A0]">Visit 1.</span>
              <br />Before symptoms escalate.
            </h2>
            <p className="text-[#8A93B2] text-lg leading-relaxed mb-8">
              Using only demographics and a basic CBC from the very first visit, the model already
              flags systemic autoimmune disease at <span className="text-[#F0F2F8]">72% confidence</span>.
              For healthy patients, it avoids unnecessary workups — saving visits and cost.
            </p>
            <div className="flex gap-4 justify-center">
              <div className="p-4 rounded-xl border border-[#52D0A0]/20 bg-[#52D0A0]/5 flex-1 max-w-xs">
                <div className="flex items-center gap-2 mb-1 justify-center">
                  <div className="w-2 h-2 rounded-full bg-[#52D0A0]" />
                  <span className="text-[#52D0A0] font-medium text-sm">Healthy patients</span>
                </div>
                <div className="flex items-end gap-2 justify-center">
                  <span className="font-display text-3xl text-[#52D0A0]">98%</span>
                  <span className="text-[#8A93B2] text-sm mb-1">save 3 visits</span>
                </div>
              </div>
              <div className="p-4 rounded-xl border border-[#7B61FF]/20 bg-[#7B61FF]/5 flex-1 max-w-xs">
                <div className="flex items-center gap-2 mb-1 justify-center">
                  <div className="w-2 h-2 rounded-full bg-[#7B61FF]" />
                  <span className="text-[#7B61FF] font-medium text-sm">Systemic autoimmune</span>
                </div>
                <div className="flex items-end gap-2 justify-center">
                  <span className="font-display text-3xl text-[#7B61FF]">99%</span>
                  <span className="text-[#8A93B2] text-sm mb-1">save 1 or more visits</span>
                </div>
              </div>
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
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto w-full">
          <FadeIn className="text-center mb-16">
            <SectionLabel>The Impact</SectionLabel>
            <h2 className="font-display text-4xl md:text-5xl font-light mb-4 leading-tight">
              <span className="text-[#F4A261]">$2,059</span> saved per patient.
              <br />
              <span className="text-[#3ECFCF]">Visits avoided.</span> Lives reclaimed.
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-2xl mx-auto">
              By flagging autoimmune patterns early, Aura eliminates unnecessary specialist
              referrals, repeat testing, and months of diagnostic limbo.
            </p>
          </FadeIn>

          <div className="grid md:grid-cols-2 gap-12 items-start">
            <FadeIn delay={0.1}>
              <div className="grid grid-cols-2 gap-6 mb-6">
                <StatCounter value={2059} prefix="$" label="Saved per healthy patient" color="#F4A261" duration={2000} />
                <StatCounter value={707} prefix="$" label="Saved per systemic patient" color="#7B61FF" duration={1600} />
              </div>
              <div className="p-5 rounded-2xl border border-[#3ECFCF]/15 bg-[#13161F]/65 backdrop-blur-md mb-4">
                <h3 className="text-[#3ECFCF] font-medium mb-3 text-sm tracking-wide uppercase">At National Scale</h3>
                <div className="space-y-3 text-[#8A93B2]">
                  {[
                    ['50M patients in the US', '50,000,000', '#F0F2F8'],
                    ['Avg specialist visits avoided', '1–3', '#F0F2F8'],
                    ['Cost per visit avoided', '$700', '#F0F2F8'],
                    ['Potential US savings', '$35–100B', '#F4A261'],
                  ].map(([k, v, c]) => (
                    <React.Fragment key={String(k)}>
                      <div className="flex justify-between items-center">
                        <span>{k}</span>
                        <span className="font-mono font-bold" style={{ color: c }}>{v}</span>
                      </div>
                      <div className="h-px bg-white/5" />
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={0.2}>
              <div className="p-5 rounded-2xl border border-[#7B61FF]/15 bg-[#13161F]/65 backdrop-blur-md">
                <h3 className="text-[#7B61FF] font-medium mb-3 text-sm tracking-wide uppercase">Beyond Cost</h3>
                <div className="space-y-3 text-[#8A93B2] text-sm">
                  {[
                    'Earlier treatment prevents irreversible organ damage',
                    'Reduces diagnostic odyssey and patient mental burden',
                    'Works from routine labs — no new tests required',
                    'Equitable across age groups and both sexes',
                    'SOAP note generation ready for clinical workflow',
                  ].map((t) => (
                    <div key={t} className="flex items-start gap-2">
                      <span className="text-[#52D0A0] mt-0.5 flex-shrink-0">✓</span>
                      <span>{t}</span>
                    </div>
                  ))}
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      <Divider />

      {/* ── 7. DATA EXPLORATION & UNDERSTANDING ─────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto w-full">
          <FadeIn className="text-center mb-14">
            <SectionLabel>Data Exploration</SectionLabel>
            <h2 className="font-display text-4xl md:text-5xl font-light mb-4 leading-tight">
              Understanding the data{' '}
              <span className="text-[#3ECFCF]">before the model.</span>
            </h2>
            <p className="text-[#8A93B2] text-lg max-w-2xl mx-auto">
              Rigorous EDA informed every modeling decision — from feature selection to
              class balancing and Z-score normalization.
            </p>
          </FadeIn>

          {/* Source distribution — wide */}
          <FadeIn delay={0.05} className="mb-10">
            <WideChartCard
              src="/figures/01_source_distribution.png"
              caption="Data sources: NHANES (73.6%) and Harvard Dataverse (24.8%) — cluster distribution varies meaningfully by source"
            />
          </FadeIn>

          {/* Cluster distribution — full width */}
          <FadeIn delay={0.1} className="mb-10">
            <WideChartCard
              src="/figures/01_cluster_distribution.png"
              caption="Disease cluster distribution across the full dataset"
            />
          </FadeIn>

          {/* Z-score distribution — full width */}
          <FadeIn delay={0.1} className="mb-10">
            <WideChartCard
              src="/figures/05_zscore_analysis.png"
              caption="Z-score distributions — normalization reveals population-level deviations per cluster"
            />
          </FadeIn>

          {/* Feature correlation — near-square, centered, capped width */}
          <FadeIn delay={0.1} className="mb-10">
            <div className="max-w-3xl mx-auto">
              <ChartCard
                src="/figures/02_feature_correlation.png"
                caption="Feature correlation matrix — Hemoglobin/Hematocrit tightly correlated (0.95); CRP and ESR independently informative"
              />
            </div>
          </FadeIn>

          {/* Key findings callout strip */}
          <FadeIn delay={0.15}>
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {
                  title: 'CRP & ESR are independent',
                  desc: 'Low correlation between each other despite both being inflammation markers — the model benefits from both.',
                  color: '#7B61FF',
                },
                {
                  title: 'Hemoglobin ↔ Hematocrit: r = 0.95',
                  desc: 'Near-perfect collinearity. Z-score features break this dependency by adjusting for population context.',
                  color: '#3ECFCF',
                },
                {
                  title: 'Neutrophil ↔ Lymphocyte: r = −0.84',
                  desc: 'Strong inverse relationship reflects the classic inflammatory shift — a key biomarker pattern for autoimmune detection.',
                  color: '#F4A261',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="p-4 rounded-xl border border-white/5 bg-[#13161F]/65"
                  style={{ borderTopColor: item.color, borderTopWidth: 2 }}
                >
                  <div className="font-medium text-sm mb-1" style={{ color: item.color }}>{item.title}</div>
                  <div className="text-[#8A93B2] text-xs leading-relaxed">{item.desc}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      <Divider />

      {/* ── 8. CLOSING CTA ───────────────────────────────────────────────── */}
      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 py-24 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% 50%, rgba(62,207,207,0.07) 0%, transparent 70%)'
        }} />
        <FadeIn className="relative z-10 max-w-3xl">
          <SectionLabel>Aura · Golden Byte 2026</SectionLabel>
          <h2 className="font-display text-5xl md:text-7xl font-light mb-6 leading-tight">
            Routine labs.{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] to-[#3ECFCF] bg-clip-text text-transparent">
              Extraordinary insight.
            </span>
          </h2>
          <p className="text-[#8A93B2] text-lg mb-12 max-w-xl mx-auto leading-relaxed">
            Aura sits at the intersection of clinical AI and patient equity — transforming data
            every physician already has into a life-changing early warning system.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="/"
              className="px-8 py-3.5 rounded-xl font-medium text-white transition-all hover:scale-105 active:scale-100"
              style={{ background: 'linear-gradient(135deg, #7B61FF, #2563EB)' }}
            >
              Try Aura Live
            </a>
            <a
              href="/clinician"
              className="px-8 py-3.5 rounded-xl font-medium border border-[#3ECFCF]/30 text-[#3ECFCF] hover:bg-[#3ECFCF]/10 transition-all hover:scale-105 active:scale-100"
            >
              Clinician Portal
            </a>
          </div>
          <div className="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {[
              { val: '0.90', label: 'AUC Score' },
              { val: '48K', label: 'Patients Trained' },
              { val: '$2K+', label: 'Saved / Patient' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="font-display text-3xl text-[#F0F2F8] font-light">{s.val}</div>
                <div className="text-[#8A93B2] text-xs tracking-widest uppercase mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </FadeIn>
      </section>

    </div>
  );
};
