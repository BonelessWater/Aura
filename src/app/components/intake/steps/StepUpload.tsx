import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Upload, Check, FileText } from 'lucide-react';
import { Button } from '../../ui/Button';
import { ErrorCard } from '../../shared/ErrorCard';

interface StepUploadProps {
  files: { name: string; status: 'parsing' | 'done' | 'error'; errorMsg?: string }[];
  fileError: string | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onFileUpload: () => void;
  onDrop: (e: React.DragEvent) => void;
  onClearError: () => void;
  onNext: () => void;
  onSkipToSymptoms: () => void;
}

export const StepUpload = ({
  files, fileError, fileInputRef,
  onFileChange, onFileUpload, onDrop,
  onClearError, onNext, onSkipToSymptoms,
}: StepUploadProps) => {
  const doneCount = files.filter(f => f.status === 'done').length;

  return (
    <motion.div
      key="step1"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col items-center w-full"
    >
      <h2 className="text-2xl lg:text-3xl font-display mb-2 text-center bg-gradient-to-r from-white to-[#B0B8D0] bg-clip-text text-transparent">
        Upload your labs &amp; notes
      </h2>
      <p className="text-sm text-[#6B7394] text-center mb-8">
        The more years of data you upload, the clearer the pattern becomes.
      </p>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        multiple
        className="hidden"
        onChange={onFileChange}
      />
      <div
        onClick={onFileUpload}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="w-full max-w-lg h-56 border-2 border-dashed border-[#7B61FF]/20 rounded-2xl flex flex-col items-center justify-center cursor-pointer hover:bg-[#7B61FF]/8 hover:border-[#7B61FF]/50 hover:scale-[1.01] transition-all duration-300 group relative overflow-hidden bg-[#0A0D14]/50"
      >
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <Upload className="w-12 h-12 text-[#7B61FF] mb-4 group-hover:scale-110 transition-transform" />
        </motion.div>
        <p className="text-[#8A93B2]">Drag &amp; drop PDF, JPG, or PNG</p>
        <p className="text-xs text-[#8A93B2]/60 mt-2">Max 50MB per file</p>
      </div>

      {/* Uploaded Files List */}
      <div className="w-full max-w-lg mt-5 space-y-2.5">
        {fileError && (
          <ErrorCard
            title="File validation failed"
            message={fileError}
            icon="document"
            onRetry={() => { onClearError(); onFileUpload(); }}
            onManualEntry={() => { onClearError(); onSkipToSymptoms(); }}
          />
        )}
        <AnimatePresence>
          {files.map((file, idx) => (
            <motion.div
              key={file.name + idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between p-4 bg-[#1A1D26] border border-[#2A2E3B] rounded-lg relative overflow-hidden"
            >
              {file.status === 'parsing' && (
                <motion.div
                  className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-[#3ECFCF] to-[#7B61FF]"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 1.2, ease: 'linear' }}
                />
              )}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#7B61FF]/20 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-[#7B61FF]" />
                </div>
                <div>
                  <span className="text-sm font-medium">{file.name}</span>
                  {file.status === 'parsing' && <span className="block text-xs text-[#8A93B2]">Parsing…</span>}
                </div>
              </div>
              {file.status === 'done' && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring" }}
                >
                  <Check className="w-5 h-5 text-[#3ECFCF]" />
                </motion.div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="mt-8">
        <Button
          onClick={onNext}
          disabled={doneCount === 0}
          className={doneCount === 0 ? "opacity-50 cursor-not-allowed" : undefined}
        >
          Next Step
        </Button>
      </div>
    </motion.div>
  );
};
