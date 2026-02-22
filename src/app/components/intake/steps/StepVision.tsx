import React, { useRef } from 'react';
import { motion } from 'motion/react';
import { Camera, CheckCircle2 } from 'lucide-react';
import { Button } from '../../ui/button';
import { usePatientStore } from '../../../../api/hooks/usePatientStore';

interface StepVisionProps {
  onComplete: () => void;
}

export const StepVision = ({ onComplete }: StepVisionProps) => {
  const images = usePatientStore((s) => s.images);
  const setImages = usePatientStore((s) => s.setImages);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected) return;
    setImages([...images, ...Array.from(selected)]);
    e.target.value = '';
  };

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

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/heic"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="w-full max-w-2xl">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full h-40 bg-[#1A1D26] border border-[#2A2E3B] rounded-xl flex flex-col items-center justify-center gap-4 hover:border-[#7B61FF] hover:bg-[#7B61FF]/5 transition-all group"
        >
          <div className="w-12 h-12 rounded-full bg-[#7B61FF]/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <Camera className="w-6 h-6 text-[#7B61FF]" />
          </div>
          <span className="font-medium">Upload Photo</span>
          <span className="text-xs text-[#8A93B2]/60">JPG, PNG, or HEIC</span>
        </button>

        {/* Show selected images */}
        {images.length > 0 && (
          <div className="mt-4 space-y-2">
            {images.map((img, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-[#1A1D26] border border-[#2A2E3B] rounded-lg">
                <CheckCircle2 className="w-4 h-4 text-[#3ECFCF] flex-shrink-0" />
                <span className="text-sm text-[#F0F2F8] truncate">{img.name}</span>
              </div>
            ))}
          </div>
        )}
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
