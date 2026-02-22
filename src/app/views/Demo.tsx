import React, { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Navbar } from '../components/layout/Navbar';

const API_BASE = 'http://localhost:8000';

interface DemoCase {
  case_id: string;
  clinical_text: string;
  age: number | null;
  sex: string | null;
  ground_truth: string;
}

interface PredictionResult {
  diagnosis: string;
  inference_time: number;
}

type CaseState = 'idle' | 'loading' | 'done' | 'error';

export const Demo = () => {
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [caseState, setCaseState] = useState<CaseState>('idle');
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [fetchError, setFetchError] = useState('');
  const [stats, setStats] = useState({ total: 0, correct: 0 });

  // Fetch cases on mount
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await fetch(`${API_BASE}/demo/cases?limit=30&seed=${Date.now() % 10000}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setCases(data.cases || []);
      } catch (e) {
        setFetchError(`Failed to load cases: ${e instanceof Error ? e.message : String(e)}`);
      }
    };
    fetchCases();
  }, []);

  const currentCase = cases[currentIdx] ?? null;

  const runDiagnosis = useCallback(async () => {
    if (!currentCase) return;
    setCaseState('loading');
    setPrediction(null);
    setErrorMsg('');

    try {
      const res = await fetch(`${API_BASE}/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: currentCase.clinical_text }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`HTTP ${res.status}: ${detail.slice(0, 200)}`);
      }
      const result: PredictionResult = await res.json();
      setPrediction(result);
      setCaseState('done');

      const isCorrect =
        result.diagnosis.toLowerCase().trim() ===
        currentCase.ground_truth.toLowerCase().trim();
      setStats((s) => ({
        total: s.total + 1,
        correct: s.correct + (isCorrect ? 1 : 0),
      }));
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setCaseState('error');
    }
  }, [currentCase]);

  const goTo = (idx: number) => {
    setCurrentIdx(idx);
    setCaseState('idle');
    setPrediction(null);
    setErrorMsg('');
  };

  const isMatch =
    prediction &&
    currentCase &&
    prediction.diagnosis.toLowerCase().trim() ===
      currentCase.ground_truth.toLowerCase().trim();

  // Truncate clinical text for display (show first N chars with expand)
  const [expanded, setExpanded] = useState(false);
  useEffect(() => setExpanded(false), [currentIdx]);
  const TEXT_PREVIEW = 600;
  const clinicalText = currentCase?.clinical_text ?? '';
  const needsTruncation = clinicalText.length > TEXT_PREVIEW;
  const displayText = expanded ? clinicalText : clinicalText.slice(0, TEXT_PREVIEW);

  return (
    <div className="relative min-h-screen text-[#F0F2F8] font-sans overflow-x-hidden">
      <Navbar />

      {/* Frosted overlay */}
      <div className="fixed inset-0 pointer-events-none z-[1] backdrop-blur-sm bg-[#020005]/30" />

      <div className="relative z-[2] pt-24 pb-16 px-4 md:px-8 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-center mb-10"
        >
          <span className="inline-block px-3 py-1 rounded-full text-xs font-mono tracking-widest uppercase border border-[#3ECFCF]/30 text-[#3ECFCF] bg-[#3ECFCF]/8 mb-4">
            Live Inference
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-light tracking-tight mb-3">
            Clinical Diagnosis{' '}
            <span className="bg-gradient-to-r from-[#7B61FF] to-[#3ECFCF] bg-clip-text text-transparent">
              Demo
            </span>
          </h1>
          <p className="text-[#8A93B2] text-base max-w-2xl mx-auto">
            MediPhi-Instruct fine-tuned on 250K PMC case reports with constrained
            decoding. Real patient cases from PubMed Central.
          </p>
        </motion.div>

        {/* Stats bar */}
        {stats.total > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-center gap-8 mb-8"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#3ECFCF]" />
              <span className="text-sm text-[#8A93B2]">
                Predictions: <span className="text-[#F0F2F8] font-mono">{stats.total}</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#52D0A0]" />
              <span className="text-sm text-[#8A93B2]">
                Correct: <span className="text-[#52D0A0] font-mono">{stats.correct}</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#7B61FF]" />
              <span className="text-sm text-[#8A93B2]">
                Accuracy:{' '}
                <span className="text-[#7B61FF] font-mono">
                  {((stats.correct / stats.total) * 100).toFixed(0)}%
                </span>
              </span>
            </div>
          </motion.div>
        )}

        {/* Error state */}
        {fetchError && (
          <div className="p-6 rounded-2xl border border-[#E07070]/30 bg-[#E07070]/8 text-center">
            <p className="text-[#E07070] mb-2 font-medium">Could not load cases</p>
            <p className="text-[#8A93B2] text-sm">{fetchError}</p>
          </div>
        )}

        {/* Loading state */}
        {!fetchError && cases.length === 0 && (
          <div className="flex flex-col items-center gap-4 py-20">
            <div className="w-8 h-8 border-2 border-[#7B61FF]/30 border-t-[#7B61FF] rounded-full animate-spin" />
            <p className="text-[#8A93B2] text-sm">Loading cases from Databricks...</p>
          </div>
        )}

        {/* Main case card */}
        {currentCase && (
          <AnimatePresence mode="wait">
            <motion.div
              key={currentCase.case_id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="rounded-2xl border border-[#7B61FF]/15 bg-[#13161F]/65 backdrop-blur-md overflow-hidden"
            >
              {/* Case header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-[#8A93B2]">
                    Case {currentIdx + 1} of {cases.length}
                  </span>
                  {currentCase.age && currentCase.sex && (
                    <span className="text-xs px-2 py-0.5 rounded-full border border-[#3ECFCF]/20 text-[#3ECFCF] bg-[#3ECFCF]/5">
                      {currentCase.age}{currentCase.sex?.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <span className="text-xs font-mono text-[#8A93B2]/50">
                  ID: {currentCase.case_id}
                </span>
              </div>

              {/* Clinical text */}
              <div className="px-6 py-5">
                <h3 className="text-xs font-mono tracking-widest uppercase text-[#8A93B2] mb-3">
                  Clinical Presentation
                </h3>
                <p className="text-sm text-[#F0F2F8]/85 leading-relaxed whitespace-pre-wrap">
                  {displayText}
                  {needsTruncation && !expanded && '...'}
                </p>
                {needsTruncation && (
                  <button
                    onClick={() => setExpanded(!expanded)}
                    className="mt-2 text-xs text-[#7B61FF] hover:text-[#7B61FF]/80 transition-colors"
                  >
                    {expanded ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>

              {/* Action area */}
              <div className="px-6 py-5 border-t border-white/5">
                {caseState === 'idle' && (
                  <button
                    onClick={runDiagnosis}
                    className="w-full py-3 rounded-xl font-medium text-white transition-all hover:scale-[1.01] active:scale-[0.99]"
                    style={{
                      background: 'linear-gradient(135deg, #7B61FF, #2563EB)',
                    }}
                  >
                    Run Diagnosis
                  </button>
                )}

                {caseState === 'loading' && (
                  <div className="flex flex-col items-center gap-3 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 border-2 border-[#7B61FF]/30 border-t-[#7B61FF] rounded-full animate-spin" />
                      <span className="text-sm text-[#8A93B2]">
                        Running inference on GPU...
                      </span>
                    </div>
                    <div className="w-full h-1 rounded-full bg-[#1A1D2A] overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: 'linear-gradient(90deg, #7B61FF, #3ECFCF)' }}
                        initial={{ width: '0%' }}
                        animate={{ width: '90%' }}
                        transition={{ duration: 8, ease: 'linear' }}
                      />
                    </div>
                  </div>
                )}

                {caseState === 'error' && (
                  <div className="text-center py-3">
                    <p className="text-[#E07070] text-sm mb-2">{errorMsg}</p>
                    <button
                      onClick={runDiagnosis}
                      className="text-xs text-[#7B61FF] hover:underline"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {caseState === 'done' && prediction && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                    className="space-y-4"
                  >
                    {/* Prediction */}
                    <div
                      className="p-4 rounded-xl border"
                      style={{
                        borderColor: isMatch
                          ? 'rgba(82, 208, 160, 0.3)'
                          : 'rgba(244, 162, 97, 0.3)',
                        background: isMatch
                          ? 'rgba(82, 208, 160, 0.06)'
                          : 'rgba(244, 162, 97, 0.06)',
                      }}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="text-xs font-mono tracking-widest uppercase text-[#8A93B2] mb-1">
                            Model Prediction
                          </div>
                          <div
                            className="text-lg font-medium capitalize"
                            style={{ color: isMatch ? '#52D0A0' : '#F4A261' }}
                          >
                            {prediction.diagnosis}
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-xs text-[#8A93B2]">Inference</div>
                          <div className="text-sm font-mono text-[#3ECFCF]">
                            {prediction.inference_time.toFixed(2)}s
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Ground truth reveal */}
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ delay: 0.4, duration: 0.4 }}
                      className="overflow-hidden"
                    >
                      <div className="p-4 rounded-xl border border-white/5 bg-[#0A0D14]/50 flex items-center justify-between">
                        <div>
                          <div className="text-xs font-mono tracking-widest uppercase text-[#8A93B2] mb-1">
                            Actual Diagnosis
                          </div>
                          <div className="text-base text-[#F0F2F8] capitalize">
                            {currentCase.ground_truth}
                          </div>
                        </div>
                        <div
                          className="px-3 py-1 rounded-full text-xs font-mono font-medium"
                          style={{
                            color: isMatch ? '#52D0A0' : '#F4A261',
                            background: isMatch
                              ? 'rgba(82, 208, 160, 0.12)'
                              : 'rgba(244, 162, 97, 0.12)',
                            border: `1px solid ${isMatch ? 'rgba(82, 208, 160, 0.25)' : 'rgba(244, 162, 97, 0.25)'}`,
                          }}
                        >
                          {isMatch ? 'MATCH' : 'MISMATCH'}
                        </div>
                      </div>
                    </motion.div>
                  </motion.div>
                )}
              </div>

              {/* Navigation */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-white/5">
                <button
                  onClick={() => goTo(Math.max(0, currentIdx - 1))}
                  disabled={currentIdx === 0}
                  className="flex items-center gap-2 text-sm text-[#8A93B2] hover:text-[#F0F2F8] disabled:opacity-30 disabled:hover:text-[#8A93B2] transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Previous
                </button>

                {/* Dot indicators */}
                <div className="flex items-center gap-1.5 overflow-hidden max-w-[200px]">
                  {cases.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => goTo(i)}
                      className={`w-1.5 h-1.5 rounded-full transition-all flex-shrink-0 ${
                        i === currentIdx
                          ? 'bg-[#7B61FF] w-4'
                          : 'bg-[#8A93B2]/30 hover:bg-[#8A93B2]/50'
                      }`}
                    />
                  ))}
                </div>

                <button
                  onClick={() => goTo(Math.min(cases.length - 1, currentIdx + 1))}
                  disabled={currentIdx === cases.length - 1}
                  className="flex items-center gap-2 text-sm text-[#8A93B2] hover:text-[#F0F2F8] disabled:opacity-30 disabled:hover:text-[#8A93B2] transition-colors"
                >
                  Next
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </motion.div>
          </AnimatePresence>
        )}

        {/* Model info footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          {[
            { label: 'Base Model', value: 'MediPhi-Instruct', color: '#7B61FF' },
            { label: 'Parameters', value: '3.8B (QLoRA)', color: '#3ECFCF' },
            { label: 'Training Data', value: '250K Cases', color: '#F4A261' },
            { label: 'Decoding', value: 'Constrained Trie', color: '#52D0A0' },
          ].map((item) => (
            <div
              key={item.label}
              className="p-3 rounded-xl border border-white/5 bg-[#13161F]/50 text-center"
            >
              <div className="font-mono text-sm font-medium" style={{ color: item.color }}>
                {item.value}
              </div>
              <div className="text-[#8A93B2] text-xs mt-0.5">{item.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
};
