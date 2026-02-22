import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate } from 'react-router';
import { ResultsDashboard } from '../components/results/ResultsDashboard';
import { SOAPNote } from '../components/results/SOAPNote';
import { SpecialistMap } from '../components/specialist/SpecialistMap';

export const DashboardPage = () => {
    const navigate = useNavigate();
    const [showSOAP, setShowSOAP] = useState(false);
    const [showSpecialists, setShowSpecialists] = useState(false);
    const [showForumECG, setShowForumECG] = useState(false);

    const handleViewCommunity = () => {
        setShowForumECG(true);
        setTimeout(() => navigate('/forum'), 900);
    };

    return (
        <>
            <ResultsDashboard
                onViewSOAP={() => setShowSOAP(true)}
                onViewSpecialists={() => setShowSpecialists(true)}
                onViewCommunity={handleViewCommunity}
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
                {showForumECG && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className="fixed inset-0 z-[79] bg-[#0A0D14]/90"
                        />
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="fixed inset-0 z-[79] pointer-events-none flex items-center justify-center overflow-hidden"
                        >
                            <svg viewBox="0 0 1200 120" className="w-full h-24 absolute top-1/2 -translate-y-1/2" preserveAspectRatio="none">
                                <motion.path
                                    d="M0,60 L300,60 L340,60 L360,20 L380,100 L400,10 L420,90 L440,60 L480,60 L1200,60"
                                    fill="none" stroke="#3ECFCF" strokeWidth="2"
                                    initial={{ pathLength: 0, opacity: 0 }}
                                    animate={{ pathLength: 1, opacity: [0, 1, 1, 0] }}
                                    transition={{ duration: 0.8, ease: "easeInOut", opacity: { times: [0, 0.1, 0.7, 1], duration: 0.8 } }}
                                    style={{ filter: 'drop-shadow(0 0 8px rgba(62,207,207,0.8)) drop-shadow(0 0 20px rgba(62,207,207,0.4))' }}
                                />
                                <motion.path
                                    d="M0,60 L300,60 L340,60 L360,20 L380,100 L400,10 L420,90 L440,60 L480,60 L1200,60"
                                    fill="none" stroke="#3ECFCF" strokeWidth="6"
                                    initial={{ pathLength: 0, opacity: 0 }}
                                    animate={{ pathLength: 1, opacity: [0, 0.3, 0.3, 0] }}
                                    transition={{ duration: 0.8, ease: "easeInOut", opacity: { times: [0, 0.1, 0.7, 1], duration: 0.8 } }}
                                    style={{ filter: 'blur(4px)' }}
                                />
                            </svg>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </>
    );
};
