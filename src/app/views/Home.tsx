import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Hero } from '../components/home/Hero';
import { IntakeWizard } from '../components/intake/IntakeWizard';
import { Processing } from '../components/processing/Processing';
import { ResultsDashboard } from '../components/results/ResultsDashboard';
import { SOAPNote } from '../components/results/SOAPNote';
import { SpecialistMap } from '../components/specialist/SpecialistMap';
import { Community } from '../components/community/Community';
import { ErrorBoundary } from '../components/shared/ErrorBoundary';
import { useResults } from '../../api/hooks/useResults';

export const Home = () => {
  const [view, setView] = useState<'hero' | 'intake' | 'processing' | 'results'>('hero');
  const [showSOAP, setShowSOAP] = useState(false);
  const [showSpecialists, setShowSpecialists] = useState(false);
  const [showCommunity, setShowCommunity] = useState(false);

  const { data: results } = useResults();

  const handleStart = () => setView('intake');
  const handleIntakeComplete = () => setView('processing');
  const handleProcessingComplete = () => setView('results');

  return (
    <div className="relative min-h-screen text-[#F0F2F8] font-sans overflow-x-hidden">
      
      <AnimatePresence mode="wait">
        {view === 'hero' && (
          <motion.div 
            key="hero"
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <Hero onStart={handleStart} />
          </motion.div>
        )}

        {view === 'intake' && (
          <motion.div
            key="intake"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <ErrorBoundary label="Intake Error">
              <IntakeWizard onComplete={handleIntakeComplete} />
            </ErrorBoundary>
          </motion.div>
        )}

        {view === 'processing' && (
          <motion.div
            key="processing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ErrorBoundary label="Processing Error">
              <Processing onComplete={handleProcessingComplete} />
            </ErrorBoundary>
          </motion.div>
        )}

        {view === 'results' && (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full h-full"
          >
            <ErrorBoundary label="Results Error">
              <ResultsDashboard
                onViewSOAP={() => setShowSOAP(true)}
                onViewSpecialists={() => setShowSpecialists(true)}
                onViewCommunity={() => setShowCommunity(true)}
              />
            </ErrorBoundary>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overlays */}
      <SOAPNote
        isOpen={showSOAP}
        onClose={() => setShowSOAP(false)}
        soapNote={results?.translator_output?.soap_note ?? null}
      />
      
      <AnimatePresence>
        {showSpecialists && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[70]"
          >
            <SpecialistMap onClose={() => setShowSpecialists(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showCommunity && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: "0%" }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-0 z-[80]"
          >
            <Community onClose={() => setShowCommunity(false)} />
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};
