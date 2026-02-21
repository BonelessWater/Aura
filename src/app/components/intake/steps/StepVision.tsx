import React from 'react';
import { motion } from 'motion/react';
import { Camera, PlayCircle } from 'lucide-react';
import { Button } from '../../ui/Button';

interface StepVisionProps {
  onComplete: () => void;
}

export const StepVision = ({ onComplete }: StepVisionProps) => {
  return (
    <motion.div
      key="step3"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col items-center w-full"
    >
      <h2 className="text-2xl lg:text-3xl font-display mb-8 text-center bg-gradient-to-r from-white to-[#B0B8D0] bg-clip-text text-transparent">
        Add visual context
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
        <button className="h-40 bg-[#1A1D26] border border-[#2A2E3B] rounded-xl flex flex-col items-center justify-center gap-4 hover:border-[#7B61FF] hover:bg-[#7B61FF]/5 transition-all group">
          <div className="w-12 h-12 rounded-full bg-[#7B61FF]/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <Camera className="w-6 h-6 text-[#7B61FF]" />
          </div>
          <span className="font-medium">Take Photo</span>
        </button>

        <button className="h-40 bg-[#1A1D26] border border-[#2A2E3B] rounded-xl flex flex-col items-center justify-center gap-4 hover:border-[#2563EB] hover:bg-[#2563EB]/5 transition-all group">
          <div className="w-12 h-12 rounded-full bg-[#2563EB]/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <PlayCircle className="w-6 h-6 text-[#2563EB]" />
          </div>
          <span className="font-medium">Record Video</span>
        </button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="mt-8 p-4 bg-[#F4A261]/10 border border-[#F4A261]/30 rounded-lg max-w-md text-center"
      >
        <p className="text-[#F4A261] text-sm font-medium">
          ✨ Aura's Vision Model translates what it sees into clinical language before processing.
        </p>
      </motion.div>

      <div className="mt-12">
        <Button onClick={onComplete} variant="secondary">Start Analysis</Button>
      </div>
    </motion.div>
  );
};
