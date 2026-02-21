import React from 'react';
import { motion } from 'motion/react';
import { Check } from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from '../../ui/Button';

interface StepSymptomsProps {
  symptoms: string;
  onSymptomsChange: (value: string) => void;
  selectedChips: string[];
  onToggleChip: (chip: string) => void;
  onNext: () => void;
}

const chips = ["Fatigue", "Joint Pain", "Rash", "Brain Fog", "GI Issues"];

export const StepSymptoms = ({
  symptoms, onSymptomsChange,
  selectedChips, onToggleChip,
  onNext,
}: StepSymptomsProps) => {
  return (
    <motion.div
      key="step2"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col items-center w-full"
    >
      <h2 className="text-2xl lg:text-3xl font-display mb-8 text-center bg-gradient-to-r from-white to-[#B0B8D0] bg-clip-text text-transparent">
        Describe your patterns
      </h2>

      <div className="w-full max-w-2xl">
        <textarea
          value={symptoms}
          onChange={(e) => onSymptomsChange(e.target.value)}
          placeholder="When did it start? Does it come and go? What makes it worse?"
          className="w-full h-48 bg-[#0A0D14] border border-[#2A2E3B] rounded-xl p-6 text-[#F0F2F8] focus:border-[#7B61FF] focus:outline-none resize-none placeholder:text-[#8A93B2]/40 text-lg leading-relaxed"
        />

        <div className="flex flex-wrap gap-3 mt-6">
          {chips.map((chip) => (
            <button
              key={chip}
              onClick={() => onToggleChip(chip)}
              className={clsx(
                "px-4 py-2 rounded-full border transition-all flex items-center gap-2",
                selectedChips.includes(chip)
                  ? "bg-[#7B61FF]/20 border-[#7B61FF] text-white"
                  : "bg-transparent border-[#2A2E3B] text-[#8A93B2] hover:border-[#8A93B2]"
              )}
            >
              {selectedChips.includes(chip) && (
                <motion.span initial={{ width: 0, opacity: 0 }} animate={{ width: "auto", opacity: 1 }}>
                  <Check className="w-3 h-3" />
                </motion.span>
              )}
              {chip}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8">
        <Button onClick={onNext}>Next Step</Button>
      </div>
    </motion.div>
  );
};
