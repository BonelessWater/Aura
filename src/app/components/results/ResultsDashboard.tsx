import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '../ui/Button';
import { 
  Menu, X, Home, FileText, Users, MapPin, 
  ChevronRight, Check, Copy, AlertCircle, Info,
  Settings, BarChart3, MessageSquare, Compass, BookOpen
} from 'lucide-react';
import { clsx } from 'clsx';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useNavigate } from 'react-router';
import { DailyNotes } from './DailyNotes';
import { DoctorHoverHelper } from './DoctorHoverHelper';
import { AppleWatchPanel } from './AppleWatchPanel';

interface ResultsDashboardProps {
  onViewSOAP: () => void;
  onViewSpecialists: () => void;
  onViewCommunity: () => void;
}

const ArcGauge = ({ score, label, color, delay = 0, small = false }: { score: number; label: string; color: string; delay?: number; small?: boolean }) => {
  const radius = small ? 30 : 50;
  const stroke = small ? 6 : 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className={clsx("relative flex flex-col items-center", small ? "w-32" : "w-48")}>
      <div className={clsx("relative flex items-center justify-center", small ? "w-[80px] h-[80px]" : "w-[120px] h-[120px]")}>
        <svg className="transform -rotate-90 w-full h-full overflow-visible">
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            stroke="#1A1D26"
            strokeWidth={stroke}
            fill="transparent"
          />
          <motion.circle
            cx="50%"
            cy="50%"
            r={radius}
            stroke={color}
            strokeWidth={stroke}
            fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, delay, ease: [0.22, 1, 0.36, 1] }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <motion.span 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            transition={{ delay: delay + 0.5 }}
            className={clsx("font-mono font-bold text-white", small ? "text-xl" : "text-4xl")}
          >
            {score}%
          </motion.span>
        </div>
      </div>
      <span className={clsx("mt-4 text-center font-medium", small ? "text-xs text-[#F4A261]" : "text-sm text-[#7B61FF]")}>
        {label}
      </span>
    </div>
  );
};

export const ResultsDashboard = ({ onViewSOAP, onViewSpecialists, onViewCommunity }: ResultsDashboardProps) => {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState('scores');
  const navigate = useNavigate();
  const mainRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const handleCopy = () => {
    navigator.clipboard?.writeText("I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos.");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Track which section is in view for sidebar highlight
  useEffect(() => {
    const container = mainRef.current;
    if (!container) return;
    const sections = ['scores', 'translation', 'next-steps', 'daily-notes', 'patient-data'];
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { root: container, rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const sidebarItems = [
    { id: 'scores', icon: BarChart3, label: "Your Scores", scrollTo: 'scores' },
    { id: 'translation', icon: Compass, label: "Translation", scrollTo: 'translation' },
    { id: 'next-steps', icon: MessageSquare, label: "Next Steps", scrollTo: 'next-steps' },
    { id: 'daily-notes', icon: BookOpen, label: "Daily Notes", scrollTo: 'daily-notes' },
    { id: 'patient-data', icon: BarChart3, label: "Patient Data", scrollTo: 'patient-data' },
    { id: 'soap', icon: FileText, label: "SOAP Note", onClick: onViewSOAP },
    { id: 'specialists', icon: MapPin, label: "Specialists", onClick: onViewSpecialists },
    { id: 'community', icon: Users, label: "Community", onClick: onViewCommunity },
    { id: 'vault', icon: Settings, label: "The Vault", href: "/vault" },
  ];

  return (
    <Tooltip.Provider>
      <div ref={wrapperRef} className="flex h-screen bg-[#0A0D14] overflow-hidden relative">
        <DoctorHoverHelper containerRef={wrapperRef} />
        
        {/* Sidebar */}
        <div className="w-20 lg:w-[300px] border-r border-[#1A1D26] flex flex-col bg-[#0A0D14] z-20">
          <div className="p-6">
            <h1 className="text-xl font-display font-bold text-white hidden lg:block">Aura</h1>
          </div>
          
          <nav className="flex-1 px-4 space-y-2">
             {sidebarItems.map((item) => {
               const isActive = item.scrollTo ? activeSection === item.scrollTo : false;
               return (
                 <button
                   key={item.id}
                   onClick={item.onClick || (item.href ? () => navigate(item.href!) : item.scrollTo ? () => scrollToSection(item.scrollTo!) : undefined)}
                   className={clsx(
                     "w-full flex items-center gap-3 p-3 rounded-lg transition-all group relative",
                     isActive 
                       ? "bg-[#7B61FF]/10 text-[#7B61FF]" 
                       : "text-[#8A93B2] hover:bg-[#1A1D26] hover:text-white"
                   )}
                 >
                   {isActive && (
                     <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#7B61FF] rounded-r-full" />
                   )}
                   <item.icon className="w-5 h-5" />
                   <span className="hidden lg:block font-medium">{item.label}</span>
                 </button>
               );
             })}
          </nav>
        </div>

        {/* Main Content */}
        <div ref={mainRef} className="flex-1 overflow-y-auto p-6 lg:p-10 relative scroll-smooth">
          
          <div className="max-w-5xl mx-auto space-y-8">
            
            {/* Header / Scores */}
            <div id="scores" className="scroll-target grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Score Card 1 */}
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 flex flex-col items-center justify-center relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-4">
                  <Info className="w-4 h-4 text-[#8A93B2]" />
                </div>
                <ArcGauge score={92} label="Systemic Autoimmune Alignment" color="#7B61FF" delay={0.2} />
              </motion.div>

              {/* Score Card 2 */}
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 flex flex-col items-center justify-center relative overflow-hidden"
              >
                 <div className="absolute bottom-4 left-0 right-0 text-center">
                    <span className="text-xs text-[#E07070] bg-[#E07070]/10 px-2 py-1 rounded">
                      This is a pattern match, not a diagnosis.
                    </span>
                 </div>
                 <ArcGauge score={65} label="SLE Pattern Similarity" color="#F4A261" delay={0.4} small />
              </motion.div>
            </div>

            {/* Trust / Safety Callout */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex items-start gap-3 p-4 rounded-xl bg-[#E07070]/5 border border-[#E07070]/15"
            >
              <AlertCircle className="w-5 h-5 text-[#E07070] flex-shrink-0 mt-0.5" />
              <div className="text-sm text-[#8A93B2] leading-relaxed">
                <p className="font-medium text-[#F0F2F8] mb-1">This is not a medical diagnosis.</p>
                <p>Aura identifies statistical patterns in your data by matching them against published medical literature. 
                Only a licensed physician can interpret these findings in the context of your full medical history. 
                These scores should be used to inform — not replace — a clinical conversation.</p>
              </div>
            </motion.div>

            {/* Translation Panel */}
            <motion.div 
              id="translation"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="scroll-target bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-8"
            >
              <h3 className="text-lg font-medium text-[#F0F2F8] mb-6 flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#3ECFCF]" />
                Clinical Translation
              </h3>
              
              <div className="space-y-6 text-[#8A93B2] leading-loose text-lg font-light">
                <p>
                  Patient presents with chronic <TooltipTerm term="joint inflammation" def="Swelling, pain, and stiffness in one or more joints caused by immune system activity." /> and <TooltipTerm term="malar rash" def="A butterfly-shaped rash across the cheeks and nose, a hallmark sign of Lupus." />. 
                  Longitudinal blood work shows a sustained upward trend in <TooltipTerm term="CRP" def="C-Reactive Protein — an inflammatory marker. Persistent elevation suggests chronic systemic inflammation." /> over 18 months. 
                  Currently experiencing <TooltipTerm term="leukopenia" def="A lower-than-normal white blood cell count, commonly seen in autoimmune conditions like Lupus." /> and persistent fatigue affecting daily tasks.
                </p>
                <p>
                   Lab ratios combined with visual evidence align with a <span className="text-[#F0F2F8] font-medium border-b border-[#7B61FF]">Systemic Autoimmune</span> profile. 
                   Secondary literature flags suggest <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where the immune system attacks healthy tissue, causing widespread inflammation." /> as a potential etiology requiring specialist confirmation.
                </p>
              </div>
            </motion.div>

            {/* What This Means / What This Does Not Mean */}
            <div id="next-steps" className="scroll-target grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#13161F] border border-[#3ECFCF]/20 rounded-2xl p-6">
                <h4 className="text-sm font-medium text-[#3ECFCF] mb-3 uppercase tracking-wider">What this means</h4>
                <ul className="space-y-2 text-sm text-[#8A93B2] leading-relaxed">
                  <li>• Your lab trends and symptoms match patterns seen in peer-reviewed autoimmune research.</li>
                  <li>• A specialist (Rheumatologist) is the right next step to confirm or rule out these patterns.</li>
                  <li>• The SOAP note gives your doctor a structured starting point backed by cited literature.</li>
                </ul>
              </div>
              <div className="bg-[#13161F] border border-[#E07070]/15 rounded-2xl p-6">
                <h4 className="text-sm font-medium text-[#E07070] mb-3 uppercase tracking-wider">What this does not mean</h4>
                <ul className="space-y-2 text-sm text-[#8A93B2] leading-relaxed">
                  <li>• This is <strong className="text-[#F0F2F8]">not</strong> a diagnosis of Lupus or any specific disease.</li>
                  <li>• Pattern similarity scores reflect statistical alignment, not clinical certainty.</li>
                  <li>• Only a doctor with access to your full history can make a diagnosis.</li>
                </ul>
              </div>
            </div>

            {/* GP Script Callout */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-[#0A0D14] border border-[#3ECFCF]/30 rounded-xl p-6"
            >
              <div className="flex justify-between items-start mb-4">
                <h4 className="font-medium text-[#3ECFCF]">What to say at your next appointment</h4>
              </div>
              
              <p className="text-sm text-[#8A93B2] mb-4 italic">
                "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
              </p>

              <Button 
                onClick={handleCopy} 
                variant="secondary"
                className="w-full text-sm py-2 h-10"
                icon={false}
              >
                {copied ? (
                   <motion.div 
                     initial={{ scale: 0.5 }} 
                     animate={{ scale: 1 }} 
                     className="flex items-center gap-2"
                   >
                     <Check className="w-4 h-4" /> Copied
                   </motion.div>
                ) : (
                   <div className="flex items-center gap-2">
                     <Copy className="w-4 h-4" /> Copy Script
                   </div>
                )}
              </Button>
            </motion.div>

            {/* Daily Notes */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-8"
            >
              <DailyNotes />
            </motion.div>

            {/* Patient Data — Apple Watch */}
            <motion.div
              id="patient-data"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-8"
            >
              <h3 className="text-lg font-medium text-[#F0F2F8] mb-6 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-[#E07070]" />
                Patient Data
              </h3>
              <AppleWatchPanel />
            </motion.div>

          </div>
        </div>
      </div>
    </Tooltip.Provider>
  );
};

const TooltipTerm = ({ term, def }: { term: string; def: string }) => (
  <Tooltip.Root>
    <Tooltip.Trigger asChild>
      <span className="cursor-help border-b border-dashed border-[#F4A261] text-[#F0F2F8] hover:text-[#F4A261] transition-colors pb-0.5">
        {term}
      </span>
    </Tooltip.Trigger>
    <Tooltip.Portal>
      <Tooltip.Content 
        className="bg-[#1A1D26] text-white px-4 py-2 rounded-lg text-sm shadow-xl border border-[#2A2E3B] max-w-xs z-50"
        sideOffset={5}
      >
        {def}
        <Tooltip.Arrow className="fill-[#2A2E3B]" />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
);