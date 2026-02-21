import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Check } from 'lucide-react';
import { clsx } from 'clsx';

interface IntakeLayoutProps {
  step: number;
  doctorImage: string;
  greeting: string;
  tip: React.ReactNode;
  children: React.ReactNode;
}

export const IntakeLayout = ({ step, doctorImage, greeting, tip, children }: IntakeLayoutProps) => {
  return (
    <div className="w-full min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-6xl flex flex-col lg:flex-row items-end lg:items-end gap-0 relative">

        {/* ─── Left: Doctor character — BIG presence ─── */}
        <div className="hidden lg:flex flex-col items-center shrink-0 w-[420px] relative z-10">

          {/* Speech bubble floating above her */}
          <AnimatePresence mode="wait">
            <motion.div
              key={`narration-${step}`}
              initial={{ opacity: 0, y: 12, scale: 0.93 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.93 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="relative w-[340px] ml-4 mb-4"
            >
              <div className="bg-[#111420]/90 backdrop-blur-md border border-[#7B61FF]/20 rounded-2xl rounded-bl-sm px-6 py-5 shadow-2xl shadow-[#7B61FF]/10">
                <p className="text-lg font-bold text-[#2563EB] mb-1.5 tracking-wide">{greeting}</p>
                <p className="text-[13px] text-[#9BA3C0] leading-[1.75]">{tip}</p>
              </div>
              {/* Tail */}
              <div className="absolute -bottom-2 left-12 w-4 h-4 bg-[#111420]/90 border-b border-l border-[#7B61FF]/20 rotate-[-45deg]" />
            </motion.div>
          </AnimatePresence>

          {/* Glow behind character */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[320px] h-[320px] rounded-full bg-[#7B61FF]/8 blur-[80px] pointer-events-none" />

          {/* Character — crossfades between images */}
          <AnimatePresence mode="wait">
            <motion.img
              key={doctorImage}
              src={doctorImage}
              alt="Aura doctor guide"
              className="relative w-[380px] h-auto object-contain drop-shadow-[0_0_40px_rgba(123,97,255,0.35)]"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1, y: [0, -6, 0] }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.5, y: { duration: 5, repeat: Infinity, ease: "easeInOut" } }}
              draggable={false}
            />
          </AnimatePresence>
        </div>

        {/* ─── Right: Glass wizard panel ─── */}
        <div className="flex-1 min-w-0 lg:-ml-6 relative z-20">
          <div className="bg-[#0E1118]/80 backdrop-blur-xl border border-[#1E2235] rounded-3xl p-8 lg:p-10 shadow-2xl shadow-black/40">

            {/* Progress Rail — inside the card */}
            <div className="flex items-center justify-center gap-0 mb-10 relative max-w-xs mx-auto">
              <div className="absolute top-1/2 left-6 right-6 h-px bg-[#1E2235] -translate-y-1/2" />
              <motion.div
                className="absolute top-1/2 left-6 h-px bg-gradient-to-r from-[#7B61FF] to-[#2563EB] -translate-y-1/2 origin-left"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: (step - 1) / 2 }}
                style={{ width: 'calc(100% - 3rem)' }}
                transition={{ duration: 0.5 }}
              />
              {[1, 2, 3].map((s) => (
                <div key={s} className="relative z-10 flex-1 flex justify-center">
                  <motion.div
                    className={clsx(
                      "w-9 h-9 rounded-full flex items-center justify-center border-2 text-sm font-semibold transition-colors duration-300",
                      step === s ? "border-[#7B61FF] bg-[#7B61FF] text-white shadow-lg shadow-[#7B61FF]/30" :
                      step > s ? "border-[#2563EB] bg-[#2563EB] text-[#0A0D14]" :
                      "border-[#2A2E3B] bg-[#0E1118] text-[#8A93B2]"
                    )}
                    layout
                  >
                    {step > s ? <Check className="w-4 h-4" /> : <span>{s}</span>}
                  </motion.div>
                </div>
              ))}
            </div>

            {/* Mobile: narration strip */}
            <div className="lg:hidden mb-8">
              <AnimatePresence mode="wait">
                <motion.div
                  key={`mobile-narration-${step}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="flex items-start gap-4 bg-[#111420]/80 border border-[#7B61FF]/15 rounded-2xl p-4"
                >
                  <img src={doctorImage} alt="" className="w-14 h-14 object-contain shrink-0" />
                  <div>
                    <p className="text-sm font-bold text-[#2563EB] mb-1">{greeting}</p>
                    <p className="text-[13px] text-[#9BA3C0] leading-relaxed">{tip}</p>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Step content */}
            <AnimatePresence mode="wait">
              {children}
            </AnimatePresence>

          </div>
        </div>
      </div>
    </div>
  );
};
