import React from 'react';
import { motion } from 'motion/react';
import { FileX, LinkIcon, RefreshCw } from 'lucide-react';

interface ErrorCardProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  onManualEntry?: () => void;
  icon?: 'document' | 'link';
}

export const ErrorCard = ({
  title = "Something went wrong",
  message,
  onRetry,
  onManualEntry,
  icon = 'document',
}: ErrorCardProps) => {
  const IconComponent = icon === 'document' ? FileX : LinkIcon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative rounded-xl border border-[#E07070] p-6 bg-[#13161F] overflow-hidden"
      style={{
        boxShadow: 'inset 0 0 40px rgba(224, 112, 112, 0.06)',
      }}
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-[#E07070]/10 flex items-center justify-center flex-shrink-0">
          <IconComponent className="w-5 h-5 text-[#E07070]" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-[#F0F2F8] font-medium mb-1">{title}</h4>
          <p className="text-sm text-[#8A93B2] leading-relaxed">{message}</p>

          <div className="flex flex-wrap gap-3 mt-4">
            {onRetry && (
              <button
                onClick={onRetry}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#E07070]/10 border border-[#E07070]/30 text-[#E07070] text-sm hover:bg-[#E07070]/20 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Try Again
              </button>
            )}
            {onManualEntry && (
              <button
                onClick={onManualEntry}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A1D26] border border-[#2A2E3B] text-[#8A93B2] text-sm hover:text-white hover:border-[#8A93B2]/50 transition-colors"
              >
                Enter Manually
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};
