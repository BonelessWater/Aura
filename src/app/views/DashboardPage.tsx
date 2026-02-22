import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { ResultsDashboard } from '../components/results/ResultsDashboard';
import { SOAPNote } from '../components/results/SOAPNote';
import { SpecialistMap } from '../components/specialist/SpecialistMap';
import { Community } from '../components/community/Community';

export const DashboardPage = () => {
    const [showSOAP, setShowSOAP] = useState(false);
    const [showSpecialists, setShowSpecialists] = useState(false);
    const [showCommunity, setShowCommunity] = useState(false);

    return (
        <>
            <ResultsDashboard
                onViewSOAP={() => setShowSOAP(true)}
                onViewSpecialists={() => setShowSpecialists(true)}
                onViewCommunity={() => setShowCommunity(true)}
            />

            {/* Overlays */}
            <SOAPNote isOpen={showSOAP} onClose={() => setShowSOAP(false)} />

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
                    <>
                        {/* Dark backdrop with pulse */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className="fixed inset-0 z-[79] bg-[#0A0D14]/95"
                        />

                        {/* ECG pulse line that sweeps across */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="fixed inset-0 z-[79] pointer-events-none flex items-center justify-center overflow-hidden"
                        >
                            <svg
                                viewBox="0 0 1200 120"
                                className="w-full h-24 absolute top-1/2 -translate-y-1/2"
                                preserveAspectRatio="none"
                            >
                                <motion.path
                                    d="M0,60 L300,60 L340,60 L360,20 L380,100 L400,10 L420,90 L440,60 L480,60 L1200,60"
                                    fill="none"
                                    stroke="#E07070"
                                    strokeWidth="2"
                                    initial={{ pathLength: 0, opacity: 0 }}
                                    animate={{ pathLength: 1, opacity: [0, 1, 1, 0] }}
                                    transition={{ duration: 0.8, ease: "easeInOut", opacity: { times: [0, 0.1, 0.7, 1], duration: 0.8 } }}
                                    style={{ filter: 'drop-shadow(0 0 8px rgba(224, 112, 112, 0.8)) drop-shadow(0 0 20px rgba(224, 112, 112, 0.4))' }}
                                />
                                {/* Trailing glow */}
                                <motion.path
                                    d="M0,60 L300,60 L340,60 L360,20 L380,100 L400,10 L420,90 L440,60 L480,60 L1200,60"
                                    fill="none"
                                    stroke="#E07070"
                                    strokeWidth="6"
                                    initial={{ pathLength: 0, opacity: 0 }}
                                    animate={{ pathLength: 1, opacity: [0, 0.3, 0.3, 0] }}
                                    transition={{ duration: 0.8, ease: "easeInOut", opacity: { times: [0, 0.1, 0.7, 1], duration: 0.8 } }}
                                    style={{ filter: 'blur(4px)' }}
                                />
                            </svg>
                        </motion.div>

                        {/* Forums content — scales up after pulse */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.96, filter: 'blur(8px)' }}
                            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                            exit={{ opacity: 0, scale: 0.96, filter: 'blur(8px)' }}
                            transition={{
                                duration: 0.5,
                                delay: 0.4,
                                ease: [0.22, 1, 0.36, 1],
                            }}
                            className="fixed inset-0 z-[80]"
                        >
                            <Community onClose={() => setShowCommunity(false)} />
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </>
    );
};
