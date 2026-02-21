import React from 'react';
import { motion } from 'motion/react';
import { Button } from '../ui/Button';
import { Sparkles } from 'lucide-react';

export const Hero = ({ onStart }: { onStart: () => void }) => {
  return (
    <section className="relative h-screen flex flex-col items-center justify-start pt-6 px-4 md:px-12 max-w-[1600px] mx-auto overflow-hidden">

      {/* ─── AURA Ribbon Logo ─── */}
      <div className="flex flex-col items-center justify-center mb-4 relative">
        {/* Soft glow behind logo */}
        <motion.div
          className="absolute w-[320px] h-[100px] rounded-full pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse, rgba(37,99,235,0.2) 0%, rgba(123,97,255,0.08) 40%, transparent 70%)',
            filter: 'blur(35px)',
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
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="h-16 md:h-20 w-auto object-contain select-none"
          style={{ filter: 'drop-shadow(0 0 20px rgba(37,99,235,0.35)) drop-shadow(0 0 60px rgba(37,99,235,0.15)) brightness(1.1) contrast(1.05)' }}
          draggable={false}
        />

        {/* Thin gradient line under */}
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="mt-2 h-[1px] w-32 bg-gradient-to-r from-transparent via-[#2563EB]/30 to-transparent"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 w-full">

        {/* Left Content */}
        <div className="lg:col-span-3 flex flex-col justify-center space-y-6 z-10">

          {/* Tag */}
          <div className="flex items-center space-x-2 text-[#5B8DEF] font-mono text-sm tracking-widest uppercase">
            <span>Private. Local. Cited.</span>
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.8, repeat: Infinity }}
              className="w-2 h-4 bg-[#2563EB]"
            />
          </div>

          {/* Heading */}
          <h1 className="text-5xl md:text-7xl font-semibold leading-[1.1] text-white font-display">
            {["Your", "symptoms", "have", "a", "pattern.", "We", "find", "it."].map((word, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: i * 0.08, ease: "easeOut" }}
                className="inline-block mr-[0.25em]"
              >
                {word}
              </motion.span>
            ))}
          </h1>

          {/* Subcopy */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-xl text-[#C0C7DC] max-w-lg leading-relaxed drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]"
          >
            Aura runs entirely on your device. Upload your labs and notes—our local AI finds the connections others miss.
          </motion.p>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
            className="flex flex-col sm:flex-row items-start sm:items-center gap-4 pt-2"
          >
            <Button
              onClick={onStart}
              className="h-[52px] px-8 text-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white shadow-[0_0_20px_rgba(37,99,235,0.35)] hover:shadow-[0_0_28px_rgba(37,99,235,0.5)] transition-all"
            >
              Upload My Labs
            </Button>
          </motion.div>
        </div>

        {/* Right Content — Chibi Neon Doctor Character */}
        <div className="lg:col-span-2 relative h-[500px] flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.5 }}
            className="relative w-full h-full flex items-center justify-center"
          >
            {/* Ambient glow layers behind the image */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full bg-[#7B61FF]/[0.10] blur-[100px] pointer-events-none" />
            <div className="absolute top-[55%] left-[54%] -translate-x-1/2 -translate-y-1/2 w-[180px] h-[180px] rounded-full bg-[#F4A261]/[0.08] blur-[70px] pointer-events-none" />

            {/* Character image */}
            <motion.img
              src="/assets/doctor-hero-neon.png"
              alt="Cute chibi neon doctor holding a glowing heart"
              className="relative z-10 max-h-[520px] w-auto object-contain drop-shadow-[0_0_20px_rgba(123,97,255,0.2)]"
              style={{ imageRendering: 'auto' }}
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              draggable={false}
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
};
