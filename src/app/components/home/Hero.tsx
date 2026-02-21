import React from 'react';
import { motion } from 'motion/react';
import { Button } from '../ui/Button';
// Icons removed — trust chips no longer shown

export const Hero = ({ onStart }: { onStart: () => void }) => {
  return (
    <section className="relative min-h-screen flex items-center justify-center px-4 md:px-12 max-w-[1400px] mx-auto overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 w-full pt-20">
        
        {/* Left Content */}
        <div className="lg:col-span-3 flex flex-col justify-center space-y-8 z-10">
          
          {/* Tag */}
          <div className="flex items-center space-x-2 text-[#3ECFCF] font-mono text-sm tracking-widest uppercase">
            <span>Private. Local. Cited.</span>
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.8, repeat: Infinity }}
              className="w-2 h-4 bg-[#3ECFCF]"
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
            className="flex flex-col sm:flex-row items-start sm:items-center gap-6 pt-4"
          >
            <Button 
              onClick={onStart} 
              className="h-[52px] px-8 text-lg bg-[#00B4D8] hover:bg-[#0096B7] text-white shadow-[0_0_20px_rgba(0,180,216,0.35)] hover:shadow-[0_0_28px_rgba(0,180,216,0.5)] transition-all"
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
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] h-[340px] rounded-full bg-[#7B61FF]/[0.10] blur-[100px] pointer-events-none" />
            <div className="absolute top-[55%] left-[54%] -translate-x-1/2 -translate-y-1/2 w-[200px] h-[200px] rounded-full bg-[#F4A261]/[0.08] blur-[70px] pointer-events-none" />

            {/* Character image — 2x retina, transparent background */}
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
