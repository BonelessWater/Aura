import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { FileText, Search, Activity, PenTool, CheckCircle2 } from 'lucide-react';

interface ProcessingProps {
  onComplete: () => void;
}

/*
  Monitor positions — each object describes where the content sits
  INSIDE the monitor screen in the lab-scene.jpg image.
  Coordinates are viewport-relative percentages.
*/
const MONITOR_POSITIONS = [
  // Upper-left monitor (Step 1)
  { top: '10%', left: '8%',  width: '14%' },
  // Lower-left monitor (Step 2)
  { top: '44%', left: '8%',  width: '16%' },
  // Upper-right monitor (Step 3) — shifted right
  { top: '13%', left: '78%', width: '14%' },
  // Lower-right monitor (Step 4)
  { top: '44%', left: '74%', width: '16%' },
];

export const Processing = ({ onComplete }: ProcessingProps) => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    { icon: FileText, label: "Parsing & Translating Files",        duration: 1500 },
    { icon: Search,   label: "Searching 180,000 PubMed Abstracts", duration: 2000 },
    { icon: Activity, label: "Scoring Alignment",                  duration: 1800 },
    { icon: PenTool,  label: "Drafting Documents",                 duration: 1200 },
  ];

  useEffect(() => {
    let currentStep = 0;
    const processStep = () => {
      if (currentStep >= steps.length) {
        setTimeout(onComplete, 800);
        return;
      }
      setActiveStep(currentStep);
      setTimeout(() => {
        currentStep++;
        processStep();
      }, steps[currentStep].duration);
    };
    processStep();
  }, []);

  const progress = ((activeStep + 1) / steps.length) * 100;

  return (
    <div className="relative flex items-center justify-center min-h-screen w-full overflow-hidden">

      {/* ── Full-screen lab scene — dimmed for text readability ── */}
      <div className="absolute inset-0 z-0">
        <img
          src="/assets/lab-scene.jpg"
          alt=""
          className="w-full h-full object-cover object-center"
          style={{ filter: 'brightness(0.55)' }}
          draggable={false}
        />
      </div>

      {/* ── Subtle animated laser sweep ── */}
      <motion.div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background:
            'linear-gradient(180deg, transparent 0%, rgba(37,99,235,0.03) 48%, rgba(37,99,235,0.08) 50%, rgba(37,99,235,0.03) 52%, transparent 100%)',
        }}
        animate={{ y: ['-100%', '100%'] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
      />

      {/* ── CENTER — title + overall progress ── */}
      <div
        className="absolute z-10 flex flex-col items-center"
        style={{ top: '10%', left: '50%', transform: 'translateX(-50%)' }}
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-2 mb-1"
        >
          <motion.div
            className="w-2 h-2 rounded-full bg-[#2563EB]"
            animate={{ opacity: [1, 0.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          <span
            className="text-[10px] uppercase tracking-[0.25em] font-mono text-[#2563EB]"
            style={{ textShadow: '0 0 8px rgba(37,99,235,0.8)' }}
          >
            AURA — LIVE ANALYSIS
          </span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="text-xl md:text-2xl font-display font-bold text-white text-center"
          style={{
            textShadow:
              '0 0 12px rgba(37,99,235,0.6), 0 0 30px rgba(37,99,235,0.3), 0 2px 4px rgba(0,0,0,0.8)',
          }}
        >
          Analyzing your data…
        </motion.h2>

        <motion.span
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-2xl md:text-3xl font-mono font-bold text-[#2563EB] mt-1"
          style={{
            textShadow:
              '0 0 14px rgba(37,99,235,0.9), 0 0 40px rgba(37,99,235,0.4)',
          }}
        >
          {Math.round(progress)}%
        </motion.span>
      </div>

      {/* ── 4 MONITORS — one step per monitor ── */}
      {steps.map((step, index) => {
        const Icon = step.icon;
        const pos = MONITOR_POSITIONS[index];
        const status =
          index < activeStep
            ? 'completed'
            : index === activeStep
              ? 'active'
              : 'pending';

        return (
          <motion.div
            key={index}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 + index * 0.15, duration: 0.6 }}
            className="absolute z-10 flex flex-col items-center justify-center p-2"
            style={{
              top: pos.top,
              left: pos.left,
              width: pos.width,
            }}
          >
            {/* Step badge */}
            <span
              className="text-[9px] md:text-[11px] uppercase tracking-[0.2em] font-mono font-bold mb-2 self-start"
              style={{
                color: status === 'completed' ? '#2563EB' : status === 'active' ? '#7B61FF' : 'rgba(200,210,230,0.4)',
                textShadow: '0 0 10px currentColor, 0 0 20px currentColor',
              }}
            >
              STEP {index + 1}
            </span>

            {/* Icon centered */}
            <div
              className="mb-2"
              style={{
                filter:
                  status === 'completed'
                    ? 'drop-shadow(0 0 12px rgba(37,99,235,1)) drop-shadow(0 0 4px rgba(37,99,235,0.8))'
                    : status === 'active'
                      ? 'drop-shadow(0 0 12px rgba(123,97,255,1)) drop-shadow(0 0 4px rgba(123,97,255,0.8))'
                      : 'drop-shadow(0 0 4px rgba(200,210,230,0.3))',
              }}
            >
              {status === 'completed' ? (
                <CheckCircle2 className="w-6 h-6 md:w-7 md:h-7 text-[#2563EB]" />
              ) : (
                <Icon
                  className={`w-6 h-6 md:w-7 md:h-7 ${
                    status === 'active'
                      ? 'text-[#7B61FF] animate-pulse'
                      : 'text-[#C0C7DC]/40'
                  }`}
                />
              )}
            </div>

            {/* Label — centered, highly visible */}
            <span
              className={`text-[11px] md:text-sm font-bold leading-snug text-center ${
                status === 'pending' ? 'text-[#C0C7DC]/40' : 'text-white'
              }`}
              style={{
                textShadow:
                  status !== 'pending'
                    ? '0 0 12px rgba(37,99,235,0.8), 0 0 24px rgba(37,99,235,0.4), 0 2px 6px rgba(0,0,0,1)'
                    : '0 1px 4px rgba(0,0,0,0.8)',
              }}
            >
              {step.label}
            </span>

            {/* Neon progress bar */}
            <div className="h-1 w-full mt-2 rounded-full overflow-hidden bg-white/10">
              <motion.div
                className="h-full rounded-full"
                style={{
                  background:
                    status === 'completed'
                      ? 'linear-gradient(90deg, #2563EB, #2563EB)'
                      : 'linear-gradient(90deg, #7B61FF, #2563EB)',
                  boxShadow:
                    status !== 'pending'
                      ? '0 0 8px rgba(37,99,235,0.7), 0 0 20px rgba(37,99,235,0.3)'
                      : 'none',
                }}
                initial={{ width: '0%' }}
                animate={{
                  width:
                    status === 'completed'
                      ? '100%'
                      : status === 'active'
                        ? '100%'
                        : '0%',
                }}
                transition={{
                  duration: status === 'active' ? step.duration / 1000 : 0.5,
                  ease: 'linear',
                }}
              />
            </div>

            {/* Status text */}
            <span
              className="text-[8px] md:text-[10px] font-mono font-bold mt-1 uppercase tracking-wider"
              style={{
                color:
                  status === 'completed'
                    ? '#2563EB'
                    : status === 'active'
                      ? '#7B61FF'
                      : 'rgba(200,210,230,0.3)',
                textShadow:
                  status !== 'pending'
                    ? '0 0 8px currentColor, 0 0 16px currentColor'
                    : 'none',
              }}
            >
              {status === 'completed'
                ? '✓ COMPLETE'
                : status === 'active'
                  ? 'PROCESSING…'
                  : 'STANDBY'}
            </span>
          </motion.div>
        );
      })}

      {/* ── Footer ── */}
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ delay: 1 }}
        className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 text-[10px] font-mono text-[#8A93B2]"
        style={{ textShadow: '0 1px 4px rgba(0,0,0,0.9)' }}
      >
        Usually ready in 45–90 seconds
      </motion.span>
    </div>
  );
};
