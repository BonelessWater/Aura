import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useMotionValue, useSpring, useTransform } from 'motion/react';
import { Button } from '../ui/Button';
import {
  FileText, Users, MapPin,
  Check, Copy, AlertCircle, Info,
  Settings, BarChart3, MessageSquare, Compass, BookOpen,
  ChevronDown, TrendingUp, Activity, Beaker, FlaskConical,
  ExternalLink, BookMarked, Microscope, Stethoscope, ShieldCheck,
  PersonStanding, Star
} from 'lucide-react';
import { clsx } from 'clsx';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useNavigate } from 'react-router';
import { DailyNotes } from './DailyNotes';
import {
  LineChart, Line, BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  XAxis, YAxis, CartesianGrid, ResponsiveContainer, Area, AreaChart,
  Cell, PolarRadiusAxis
} from 'recharts';

interface ResultsDashboardProps {
  onViewSOAP: () => void;
  onViewSpecialists: () => void;
  onViewCommunity: () => void;
  onViewBody?: () => void;
}

// --- Mock data for charts ---
const crpTrendData = [
  { month: 'Jan', value: 3.2 }, { month: 'Mar', value: 5.1 }, { month: 'May', value: 4.8 },
  { month: 'Jul', value: 7.3 }, { month: 'Sep', value: 9.1 }, { month: 'Nov', value: 8.6 },
  { month: 'Jan', value: 11.2 }, { month: 'Mar', value: 12.8 }, { month: 'Now', value: 14.1 },
];

const wbcTrendData = [
  { month: 'Jan', value: 5.8 }, { month: 'Mar', value: 5.2 }, { month: 'May', value: 4.9 },
  { month: 'Jul', value: 4.3 }, { month: 'Sep', value: 3.8 }, { month: 'Nov', value: 3.5 },
  { month: 'Jan', value: 3.2 }, { month: 'Mar', value: 3.0 }, { month: 'Now', value: 2.8 },
];

const anaTrendData = [
  { month: 'Jan', value: 1.2 }, { month: 'Mar', value: 1.4 }, { month: 'May', value: 1.8 },
  { month: 'Jul', value: 2.1 }, { month: 'Sep', value: 2.6 }, { month: 'Nov', value: 3.0 },
  { month: 'Jan', value: 3.4 }, { month: 'Mar', value: 3.8 }, { month: 'Now', value: 4.2 },
];

const scoreBreakdownData = [
  { factor: 'Lab Markers', weight: 35, score: 94, color: '#7B61FF' },
  { factor: 'Symptom Pattern', weight: 25, score: 88, color: '#3ECFCF' },
  { factor: 'Photo Analysis', weight: 20, score: 95, color: '#F4A261' },
  { factor: 'Timeline Fit', weight: 12, score: 90, color: '#52D0A0' },
  { factor: 'Literature Match', weight: 8, score: 87, color: '#E07070' },
];

const radarData = [
  { axis: 'CRP', value: 92 },
  { axis: 'ANA', value: 85 },
  { axis: 'WBC', value: 78 },
  { axis: 'ESR', value: 88 },
  { axis: 'Malar Rash', value: 95 },
  { axis: 'Joint Pain', value: 90 },
  { axis: 'Fatigue', value: 82 },
];

const citations = [
  { id: 'C1', title: 'Systemic Lupus Erythematosus: Diagnosis and Management', journal: 'The Lancet', year: 2024, doi: '10.1016/S0140-6736(24)00123-4' },
  { id: 'C2', title: 'CRP as a Biomarker for Autoimmune Inflammation', journal: 'Nature Reviews Rheumatology', year: 2023, doi: '10.1038/s41584-023-00987-3' },
  { id: 'C3', title: 'Leukopenia in SLE: Mechanisms and Clinical Significance', journal: 'Arthritis & Rheumatology', year: 2024, doi: '10.1002/art.42890' },
  { id: 'C4', title: 'Malar Rash Pattern Recognition via Computer Vision', journal: 'Journal of Medical AI', year: 2024, doi: '10.1016/j.jmai.2024.100234' },
];

// --- Components ---

const ArcGauge = ({ score, label, color, delay = 0, small = false, onClick }: { score: number; label: string; color: string; delay?: number; small?: boolean; onClick?: () => void }) => {
  const radius = small ? 30 : 50;
  const stroke = small ? 6 : 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div
      className={clsx("relative flex flex-col items-center cursor-pointer group", small ? "w-32" : "w-48")}
      onClick={onClick}
    >
      <div className={clsx("relative flex items-center justify-center gauge-glow group-hover:scale-105 transition-transform", small ? "w-[80px] h-[80px]" : "w-[120px] h-[120px]")}>
        <svg className="transform -rotate-90 w-full h-full overflow-visible">
          <circle cx="50%" cy="50%" r={radius} stroke="#1A1D26" strokeWidth={stroke} fill="transparent" />
          <motion.circle
            cx="50%" cy="50%" r={radius} stroke={color} strokeWidth={stroke} fill="transparent"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, delay, ease: [0.22, 1, 0.36, 1] }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <motion.span
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: delay + 0.5 }}
            className={clsx("font-mono font-bold text-white", small ? "text-xl" : "text-4xl")}
          >
            {score}%
          </motion.span>
        </div>
      </div>
      <span className={clsx("mt-4 text-center font-medium group-hover:underline decoration-dotted underline-offset-4", small ? "text-xs text-[#F4A261]" : "text-sm text-[#7B61FF]")}>
        {label}
      </span>
      <span className="text-[10px] text-[#8A93B2]/60 mt-1 group-hover:text-[#8A93B2] transition-colors">Click to explore</span>
    </div>
  );
};

const ExpandableSection = ({ children, isOpen, onToggle, title, icon: Icon, color, badge }: {
  children: React.ReactNode; isOpen: boolean; onToggle: () => void;
  title: string; icon: React.ElementType; color: string; badge?: string;
}) => (
  <div className="dashboard-card overflow-hidden">
    <button onClick={onToggle} className="w-full p-6 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
      <div className="flex items-center gap-3">
        <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${color}15` }}>
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <h3 className="text-lg font-medium text-[#F0F2F8]">{title}</h3>
        {badge && <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.04] text-[#8A93B2]">{badge}</span>}
      </div>
      <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
        <ChevronDown className="w-5 h-5 text-[#8A93B2]" />
      </motion.div>
    </button>
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden"
        >
          <div className="px-6 pb-6">{children}</div>
        </motion.div>
      )}
    </AnimatePresence>
  </div>
);

const MiniChart = ({ data, color, label, unit, current, normal, onClick }: {
  data: { month: string; value: number }[]; color: string; label: string;
  unit: string; current: string; normal: string; onClick: () => void;
}) => (
  <button onClick={onClick} className="dashboard-card p-4 hover:border-white/[0.12] transition-all text-left w-full group">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-medium text-[#F0F2F8]">{label}</span>
      <span className="text-[10px] text-[#8A93B2] group-hover:text-white transition-colors">Click to expand</span>
    </div>
    <div className="h-16 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <defs>
            <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill={`url(#grad-${label})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
    <div className="flex items-center justify-between mt-2">
      <span className="text-xs font-mono" style={{ color }}>{current} <span className="text-[#8A93B2]">{unit}</span></span>
      <span className="text-[10px] text-[#8A93B2]">Normal: {normal}</span>
    </div>
  </button>
);


// --- Floating Dock ---

const DockItem = ({ icon: Icon, label, onClick, isActive, mouseX, color }: {
  icon: React.ElementType; label: string; onClick: () => void;
  isActive?: boolean; mouseX: any; color?: string;
}) => {
  const ref = useRef<HTMLButtonElement>(null);

  const distance = useTransform(mouseX, (val: number) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect || val === -1) return 150;
    return val - rect.x - rect.width / 2;
  });

  const size = useSpring(
    useTransform(distance, [-120, 0, 120], [40, 64, 40]),
    { mass: 0.1, stiffness: 200, damping: 15 }
  );
  const iconSize = useSpring(
    useTransform(distance, [-120, 0, 120], [18, 28, 18]),
    { mass: 0.1, stiffness: 200, damping: 15 }
  );
  const labelOpacity = useSpring(
    useTransform(distance, [-60, 0, 60], [0, 1, 0]),
    { mass: 0.1, stiffness: 300, damping: 20 }
  );
  const labelY = useSpring(
    useTransform(distance, [-60, 0, 60], [8, 0, 8]),
    { mass: 0.1, stiffness: 300, damping: 20 }
  );

  return (
    <div className="relative flex flex-col items-center">
      {/* Floating label */}
      <motion.div
        style={{ opacity: labelOpacity, y: labelY }}
        className="absolute -top-9 whitespace-nowrap pointer-events-none"
      >
        <span className="text-[11px] font-medium text-white bg-[#13161F]/95 border border-white/[0.08] px-2.5 py-1 rounded-lg shadow-xl backdrop-blur-sm">
          {label}
        </span>
      </motion.div>

      <motion.button
        ref={ref}
        onClick={onClick}
        style={{ width: size, height: size }}
        className={clsx(
          "rounded-2xl flex items-center justify-center transition-colors relative",
          isActive
            ? "bg-[#7B61FF]/15 text-[#7B61FF]"
            : "bg-white/[0.04] text-[#8A93B2] hover:text-white hover:bg-white/[0.08]"
        )}
      >
        {isActive && (
          <div className="absolute -bottom-1.5 w-1 h-1 rounded-full bg-[#7B61FF]" />
        )}
        <motion.div style={{ width: iconSize, height: iconSize }} className="flex items-center justify-center">
          <Icon className="w-full h-full" style={color && !isActive ? { color } : undefined} />
        </motion.div>
      </motion.button>
    </div>
  );
};

const FloatingDock = ({ scrollItems, actionItems, activeSection, scrollToSection }: {
  scrollItems: { id: string; icon: React.ElementType; label: string }[];
  actionItems: { id: string; icon: React.ElementType; label: string; onClick: () => void; color?: string }[];
  activeSection: string;
  scrollToSection: (id: string) => void;
}) => {
  const mouseX = useMotionValue(-1);

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.5, type: 'spring', stiffness: 200, damping: 25 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50"
    >
      <motion.div
        onMouseMove={(e) => mouseX.set(e.pageX)}
        onMouseLeave={() => mouseX.set(-1)}
        className="flex items-end gap-2 px-4 py-3 rounded-3xl card-glass border border-white/[0.08]"
        style={{ backdropFilter: 'blur(20px)', animation: 'dock-breathe 4s ease-in-out infinite' }}
      >
        {/* Scroll-to items */}
        {scrollItems.map((item) => (
          <DockItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            onClick={() => scrollToSection(item.id)}
            isActive={activeSection === item.id}
            mouseX={mouseX}
          />
        ))}

        {/* Divider */}
        <div className="w-px h-8 bg-white/[0.08] mx-1 self-center" />

        {/* Action items */}
        {actionItems.map((item) => (
          <DockItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            onClick={item.onClick}
            mouseX={mouseX}
            color={item.color}
          />
        ))}
      </motion.div>
    </motion.div>
  );
};


// --- Bone Scrollbar ---

const BoneScrollbar = ({ scrollRef }: { scrollRef: React.RefObject<HTMLDivElement | null> }) => {
  const [scrollPct, setScrollPct] = useState(0);
  const [visible, setVisible] = useState(false);
  const [dragging, setDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const boneHeight = 48;

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const max = el.scrollHeight - el.clientHeight;
      setScrollPct(max > 0 ? el.scrollTop / max : 0);
      setVisible(true);
      if (hideTimer.current) clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => { if (!dragging) setVisible(false); }, 1500);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [scrollRef, dragging]);

  const handleTrackClick = (e: React.MouseEvent) => {
    const track = trackRef.current;
    const el = scrollRef.current;
    if (!track || !el) return;
    const rect = track.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientY - rect.top - boneHeight / 2) / (rect.height - boneHeight)));
    el.scrollTop = pct * (el.scrollHeight - el.clientHeight);
  };

  const handleDragStart = (e: React.PointerEvent) => {
    e.preventDefault();
    setDragging(true);
    setVisible(true);
    const onMove = (ev: PointerEvent) => {
      const track = trackRef.current;
      const el = scrollRef.current;
      if (!track || !el) return;
      const rect = track.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (ev.clientY - rect.top - boneHeight / 2) / (rect.height - boneHeight)));
      el.scrollTop = pct * (el.scrollHeight - el.clientHeight);
    };
    const onUp = () => {
      setDragging(false);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const topOffset = scrollPct * (100 - (boneHeight / 3));

  return (
    <div
      ref={trackRef}
      onClick={handleTrackClick}
      className="absolute right-1 top-0 bottom-0 w-6 z-30 cursor-pointer group"
    >
      {/* Track line */}
      <div className={clsx(
        "absolute right-[10px] top-4 bottom-4 w-[2px] rounded-full transition-opacity duration-300",
        visible || dragging ? "opacity-30" : "opacity-0 group-hover:opacity-20"
      )} style={{ background: 'linear-gradient(to bottom, transparent, rgba(123, 97, 255, 0.4), transparent)' }} />

      {/* Bone thumb */}
      <motion.div
        onPointerDown={handleDragStart}
        animate={{ opacity: visible || dragging ? 1 : 0 }}
        whileHover={{ opacity: 1, scale: 1.15 }}
        transition={{ duration: 0.2 }}
        className="absolute right-0 cursor-grab active:cursor-grabbing group-hover:opacity-100"
        style={{ top: `calc(16px + (100% - 32px - ${boneHeight}px) * ${scrollPct})` }}
      >
        {/* Bone SVG */}
        <svg width="22" height={boneHeight} viewBox="0 0 22 48" fill="none" className="drop-shadow-[0_0_6px_rgba(123,97,255,0.3)]">
          {/* Top knobs */}
          <circle cx="6" cy="6" r="5.5" fill="rgba(123, 97, 255, 0.35)" stroke="rgba(123, 97, 255, 0.5)" strokeWidth="1" />
          <circle cx="16" cy="6" r="5.5" fill="rgba(123, 97, 255, 0.35)" stroke="rgba(123, 97, 255, 0.5)" strokeWidth="1" />
          {/* Shaft */}
          <rect x="8" y="5" width="6" height="38" rx="3" fill="rgba(123, 97, 255, 0.3)" stroke="rgba(123, 97, 255, 0.45)" strokeWidth="1" />
          {/* Bottom knobs */}
          <circle cx="6" cy="42" r="5.5" fill="rgba(123, 97, 255, 0.35)" stroke="rgba(123, 97, 255, 0.5)" strokeWidth="1" />
          <circle cx="16" cy="42" r="5.5" fill="rgba(123, 97, 255, 0.35)" stroke="rgba(123, 97, 255, 0.5)" strokeWidth="1" />
        </svg>
      </motion.div>
    </div>
  );
};


export const ResultsDashboard = ({ onViewSOAP, onViewSpecialists, onViewCommunity, onViewBody }: ResultsDashboardProps) => {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState('scores');
  const [expandedScore, setExpandedScore] = useState<'primary' | 'secondary' | null>(null);
  const [expandedLab, setExpandedLab] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [expandedNextStep, setExpandedNextStep] = useState<number | null>(null);
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

  useEffect(() => {
    const container = mainRef.current;
    if (!container) return;
    const sections = ['scores', 'lab-trends', 'next-steps', 'daily-notes'];
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
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

  const scrollItems = [
    { id: 'scores', icon: BarChart3, label: "Your Results" },
    { id: 'lab-trends', icon: Activity, label: "Blood Work" },
    { id: 'next-steps', icon: MessageSquare, label: "What It Means" },
    { id: 'daily-notes', icon: BookOpen, label: "Journal" },
  ];

  const actionItems = [
    { id: 'body', icon: PersonStanding, label: "Body Map", onClick: () => onViewBody?.(), color: '#7B61FF' },
    { id: 'soap', icon: FileText, label: "SOAP Note", onClick: onViewSOAP, color: '#F4A261' },
    { id: 'forums', icon: Users, label: "Forums", onClick: onViewCommunity, color: '#3ECFCF' },
    { id: 'vault', icon: Settings, label: "Vault", onClick: () => navigate('/vault'), color: '#8A93B2' },
  ];

  const nextStepsData = [
    {
      title: 'Your lab trends match autoimmune patterns',
      detail: 'Your CRP has risen from 3.2 to 14.1 mg/L over 18 months — a 340% increase. Combined with declining WBC (5.8 → 2.8 × 10⁹/L) and rising ANA titers (1:80 → 1:640), this trajectory closely matches profiles documented in systemic autoimmune literature.',
      icon: TrendingUp,
      color: '#3ECFCF',
    },
    {
      title: 'See a Rheumatologist next',
      detail: 'Based on 4 peer-reviewed studies matching your pattern profile, a Rheumatologist is the recommended specialist. They can order confirmatory tests (anti-dsDNA, complement C3/C4) and evaluate whether your pattern aligns with a specific diagnosis.',
      icon: Stethoscope,
      color: '#7B61FF',
    },
    {
      title: 'Your SOAP note is ready for your doctor',
      detail: 'We\'ve generated a structured clinical summary (Subjective, Objective, Assessment, Plan) from your uploaded labs, symptom descriptions, and photos. This gives your doctor a concise starting point backed by 4 cited studies.',
      icon: FileText,
      color: '#F4A261',
      action: { label: 'View SOAP Note', onClick: onViewSOAP },
    },
  ];

  const notMeanData = [
    {
      title: 'This is not a diagnosis',
      detail: 'AuRA performs statistical pattern matching, not clinical evaluation. A 92% alignment score means your data strongly resembles autoimmune profiles in published research — it does not mean you have an autoimmune disease. Only a licensed physician can make a diagnosis.',
      icon: ShieldCheck,
      color: '#E07070',
    },
    {
      title: 'Scores reflect probability, not certainty',
      detail: 'The 65% SLE similarity score means that among the conditions we pattern-matched, SLE was the closest fit for your specific combination of markers. Other conditions may share similar profiles.',
      icon: Activity,
      color: '#E07070',
    },
  ];

  return (
    <Tooltip.Provider>
      <div ref={wrapperRef} className="flex flex-col h-screen overflow-hidden relative">

        {/* Floating Dock */}
        <FloatingDock
          scrollItems={scrollItems}
          actionItems={actionItems}
          activeSection={activeSection}
          scrollToSection={scrollToSection}
        />

        {/* Main Content */}
        <div ref={mainRef} className="flex-1 overflow-y-auto scroll-smooth">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-10 py-8 space-y-8">

            {/* Floating brand */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-center gap-1 py-2"
            >
              {/* Animated AuRA title — large, dramatic, letter-by-letter entrance like home page */}
              <h1 className="font-display text-5xl md:text-6xl font-bold tracking-[0.06em] leading-none">
                {['A', 'u', 'R', 'A'].map((letter, i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.15 + i * 0.1, ease: 'easeOut' }}
                    className={letter === 'u' ? 'text-white/50' : 'text-white'}
                    style={{
                      textShadow: '0 0 40px rgba(140, 7, 22, 0.6), 0 0 80px rgba(140, 7, 22, 0.25)',
                    }}
                  >
                    {letter}
                  </motion.span>
                ))}
              </h1>
            </motion.div>

            {/* Trust / Safety Callout — compact */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
              className="dashboard-card glow-rose flex items-center gap-3 px-5 py-3"
            >
              <AlertCircle className="w-4 h-4 text-[#E07070] flex-shrink-0" />
              <p className="text-xs text-[#8A93B2] leading-relaxed">
                <span className="font-medium text-[#F0F2F8]">Not a diagnosis.</span> AuRA matches patterns in published research — only a doctor can interpret these results for you.
              </p>
            </motion.div>

            {/* ============ SCORES SECTION ============ */}
            <div id="scores" className="scroll-target space-y-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="dashboard-card glow-violet p-8 relative"
              >
                <div className="flex flex-col md:flex-row items-center justify-around gap-8">
                  <ArcGauge
                    score={92} label="Pattern Match Score" color="#7B61FF" delay={0.2}
                    onClick={() => setExpandedScore(expandedScore === 'primary' ? null : 'primary')}
                  />
                  <div className="hidden md:block w-px h-32 bg-gradient-to-b from-transparent via-[#7B61FF]/20 to-transparent" />
                  <div className="md:hidden w-32 h-px bg-gradient-to-r from-transparent via-[#7B61FF]/20 to-transparent" />
                  <div className="flex flex-col items-center gap-3">
                    <ArcGauge
                      score={65} label="Closest Condition Match" color="#F4A261" delay={0.4} small
                      onClick={() => setExpandedScore(expandedScore === 'secondary' ? null : 'secondary')}
                    />
                    <span className="text-xs text-[#E07070] bg-[#E07070]/10 px-3 py-1 rounded-full">
                      Pattern match, not a diagnosis
                    </span>
                  </div>
                </div>

                <div className="absolute top-4 right-4">
                  <Tooltip.Root>
                    <Tooltip.Trigger asChild>
                      <button className="p-1 rounded-md hover:bg-white/[0.04] transition-colors">
                        <Info className="w-4 h-4 text-[#8A93B2]" />
                      </button>
                    </Tooltip.Trigger>
                    <Tooltip.Portal>
                      <Tooltip.Content className="bg-[#1A1D26] text-white px-4 py-2 rounded-lg text-sm shadow-xl border border-[#2A2E3B] max-w-xs z-50" sideOffset={5}>
                        Tap either score to learn how we calculated it. These scores show how closely your data matches patterns in published medical research.
                        <Tooltip.Arrow className="fill-[#2A2E3B]" />
                      </Tooltip.Content>
                    </Tooltip.Portal>
                  </Tooltip.Root>
                </div>
              </motion.div>

              {/* Expanded Score Breakdown */}
              <AnimatePresence>
                {expandedScore === 'primary' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="dashboard-card p-6 space-y-6">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium text-[#F0F2F8] flex items-center gap-2">
                          <Microscope className="w-4 h-4 text-[#7B61FF]" />
                          How we got 92%
                        </h4>
                        <button onClick={() => setExpandedScore(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors">Close</button>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Contributing Factors Bar Chart */}
                        <div>
                          <p className="text-xs text-[#8A93B2] mb-3">Contributing factors (weighted)</p>
                          <div className="h-52">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={scoreBreakdownData} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 80 }}>
                                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8A93B2', fontSize: 11 }} axisLine={false} tickLine={false} />
                                <YAxis type="category" dataKey="factor" tick={{ fill: '#F0F2F8', fontSize: 12 }} axisLine={false} tickLine={false} width={80} />
                                <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={16}>
                                  {scoreBreakdownData.map((entry, i) => (
                                    <Cell key={i} fill={entry.color} fillOpacity={0.8} />
                                  ))}
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        {/* Radar Chart */}
                        <div>
                          <p className="text-xs text-[#8A93B2] mb-3">Pattern alignment across markers</p>
                          <div className="h-52">
                            <ResponsiveContainer width="100%" height="100%">
                              <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                                <PolarGrid stroke="#2A2E3B" />
                                <PolarAngleAxis dataKey="axis" tick={{ fill: '#8A93B2', fontSize: 10 }} />
                                <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
                                <Radar dataKey="value" stroke="#7B61FF" fill="#7B61FF" fillOpacity={0.15} strokeWidth={2} />
                              </RadarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      </div>

                      {/* Weight breakdown pills */}
                      <div className="flex flex-wrap gap-2">
                        {scoreBreakdownData.map((item) => (
                          <div key={item.factor} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                            <span className="text-[#8A93B2]">{item.factor}</span>
                            <span className="font-mono text-[#F0F2F8]">{item.weight}%</span>
                            <span className="text-[#8A93B2]">weight</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {expandedScore === 'secondary' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="dashboard-card p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium text-[#F0F2F8] flex items-center gap-2">
                          <Microscope className="w-4 h-4 text-[#F4A261]" />
                          Closest condition match — why 65%
                        </h4>
                        <button onClick={() => setExpandedScore(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors">Close</button>
                      </div>
                      <p className="text-sm text-[#8A93B2] leading-relaxed">
                        Out of all the conditions we compared your data to, <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where your immune system mistakenly attacks healthy tissue, causing widespread inflammation." /> was the closest match.
                        65% means a partial — not definitive — match: your <TooltipTerm term="CRP" def="C-Reactive Protein — a blood marker that goes up when there's inflammation in your body." /> trend and <TooltipTerm term="malar rash" def="A butterfly-shaped rash across the cheeks and nose, commonly associated with Lupus." /> are strong indicators,
                        but some key tests (<TooltipTerm term="complement levels" def="Proteins in your blood that help your immune system. Low levels can indicate autoimmune activity." />, <TooltipTerm term="anti-dsDNA" def="An antibody test that is very specific to Lupus. A positive result strongly supports an SLE diagnosis." />) haven't been done yet.
                      </p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          { label: 'Malar Rash', match: 'Strong', pct: 95, color: '#52D0A0' },
                          { label: 'CRP Trend', match: 'Strong', pct: 88, color: '#52D0A0' },
                          { label: 'Leukopenia', match: 'Moderate', pct: 72, color: '#F4A261' },
                          { label: 'Anti-dsDNA', match: 'Untested', pct: 0, color: '#8A93B2' },
                        ].map((item) => (
                          <div key={item.label} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center">
                            <p className="text-[10px] text-[#8A93B2] mb-1">{item.label}</p>
                            <p className="text-sm font-mono" style={{ color: item.color }}>
                              {item.pct > 0 ? `${item.pct}%` : '—'}
                            </p>
                            <p className="text-[10px] mt-0.5" style={{ color: item.color }}>{item.match}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="gradient-divider" />

            {/* ============ WHAT WE FOUND (Patient-Friendly Summary) ============ */}
            <motion.div
              id="what-we-found"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="scroll-target dashboard-card p-8"
            >
              <h3 className="text-lg font-medium text-[#F0F2F8] mb-6 flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-[#3ECFCF]/10">
                  <FileText className="w-4 h-4 text-[#3ECFCF]" />
                </div>
                What We Found
              </h3>

              <div className="space-y-6 text-[#8A93B2] leading-loose text-lg font-light">
                <p>
                  Based on your lab results and photos, we noticed a pattern of ongoing <TooltipTerm term="inflammation" def="Your body's immune response is more active than normal. When it stays elevated, it can signal an underlying condition." />.
                  Your <TooltipTerm term="CRP" def="C-Reactive Protein — a blood marker that goes up when there's inflammation in your body. Normal is below 3.0 mg/L." /> levels have been climbing steadily over the past 18 months.
                  You also have a lower-than-normal <TooltipTerm term="white blood cell count" def="White blood cells fight infections. A low count (called leukopenia) can happen when your immune system is overactive and starts affecting healthy cells." />, and you've reported ongoing fatigue and <TooltipTerm term="joint pain" def="Swelling, pain, and stiffness in one or more joints, which can be caused by immune system activity." />.
                </p>
                <p>
                  When we compared your data to patterns in published medical research, it most closely matched a <span className="text-[#F0F2F8] font-medium border-b border-[#7B61FF]">systemic autoimmune</span> profile.
                  The closest specific condition match was <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where your immune system mistakenly attacks healthy tissue, causing inflammation in joints, skin, kidneys, and other organs." /> — but more testing is needed to confirm.
                </p>
              </div>
            </motion.div>

            <div className="gradient-divider" />

            {/* ============ LAB TRENDS ============ */}
            <div id="lab-trends" className="scroll-target space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-[#F0F2F8] flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-[#7B61FF]/10">
                    <Activity className="w-4 h-4 text-[#7B61FF]" />
                  </div>
                  Lab Trends
                </h3>
                <span className="text-xs text-[#8A93B2]">18-month tracking window</span>
              </div>

              {/* Mini chart grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MiniChart
                  data={crpTrendData} color="#E07070" label="CRP (C-Reactive Protein)"
                  unit="mg/L" current="14.1" normal="< 3.0"
                  onClick={() => setExpandedLab(expandedLab === 'crp' ? null : 'crp')}
                />
                <MiniChart
                  data={wbcTrendData} color="#3ECFCF" label="WBC (White Blood Cells)"
                  unit="× 10⁹/L" current="2.8" normal="4.5 – 11.0"
                  onClick={() => setExpandedLab(expandedLab === 'wbc' ? null : 'wbc')}
                />
                <MiniChart
                  data={anaTrendData} color="#F4A261" label="ANA Titer (log₂)"
                  unit="titer" current="1:640" normal="< 1:80"
                  onClick={() => setExpandedLab(expandedLab === 'ana' ? null : 'ana')}
                />
              </div>

              {/* Expanded Lab Detail */}
              <AnimatePresence>
                {expandedLab && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="dashboard-card p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium text-[#F0F2F8]">
                          {expandedLab === 'crp' && 'CRP — Inflammatory Marker Trend'}
                          {expandedLab === 'wbc' && 'WBC — White Blood Cell Decline'}
                          {expandedLab === 'ana' && 'ANA — Autoantibody Titer Rise'}
                        </h4>
                        <button onClick={() => setExpandedLab(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors">Close</button>
                      </div>

                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart
                            data={expandedLab === 'crp' ? crpTrendData : expandedLab === 'wbc' ? wbcTrendData : anaTrendData}
                            margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
                          >
                            <defs>
                              <linearGradient id="expanded-grad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={expandedLab === 'crp' ? '#E07070' : expandedLab === 'wbc' ? '#3ECFCF' : '#F4A261'} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={expandedLab === 'crp' ? '#E07070' : expandedLab === 'wbc' ? '#3ECFCF' : '#F4A261'} stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid stroke="#1A1D26" strokeDasharray="3 3" />
                            <XAxis dataKey="month" tick={{ fill: '#8A93B2', fontSize: 11 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: '#8A93B2', fontSize: 11 }} axisLine={false} tickLine={false} />
                            <Area
                              type="monotone" dataKey="value"
                              stroke={expandedLab === 'crp' ? '#E07070' : expandedLab === 'wbc' ? '#3ECFCF' : '#F4A261'}
                              strokeWidth={2} fill="url(#expanded-grad)"
                              dot={{ fill: '#0A0D14', stroke: expandedLab === 'crp' ? '#E07070' : expandedLab === 'wbc' ? '#3ECFCF' : '#F4A261', strokeWidth: 2, r: 4 }}
                              activeDot={{ r: 6 }}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-sm text-[#8A93B2] leading-relaxed">
                        {expandedLab === 'crp' && (
                          <>Your CRP has risen steadily from <span className="text-[#F0F2F8] font-mono">3.2 mg/L</span> to <span className="text-[#E07070] font-mono">14.1 mg/L</span> over 18 months.
                            Normal range is below 3.0 mg/L. Persistent elevation above 10 mg/L is associated with chronic systemic inflammation and is a key marker in autoimmune conditions <span className="text-[#F4A261] cursor-pointer">[C2]</span>.</>
                        )}
                        {expandedLab === 'wbc' && (
                          <>Your white blood cell count has declined from <span className="text-[#F0F2F8] font-mono">5.8</span> to <span className="text-[#3ECFCF] font-mono">2.8 × 10⁹/L</span>.
                            Counts below 4.0 indicate leukopenia. This pattern of progressive decline is commonly observed in SLE and other autoimmune disorders where the immune system targets healthy cells <span className="text-[#F4A261] cursor-pointer">[C3]</span>.</>
                        )}
                        {expandedLab === 'ana' && (
                          <>Your ANA titer has risen from <span className="text-[#F0F2F8] font-mono">1:80</span> to <span className="text-[#F4A261] font-mono">1:640</span>.
                            Titers above 1:160 are considered clinically significant. Rising ANA titers combined with other markers strongly suggest autoimmune activity and warrant specialist evaluation <span className="text-[#F4A261] cursor-pointer">[C1]</span>.</>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="gradient-divider" />

            {/* ============ HOW WE KNOW (Evidence + Methodology inline) ============ */}
            <ExpandableSection
              isOpen={showEvidence} onToggle={() => setShowEvidence(!showEvidence)}
              title="How we know — sources & method" icon={BookMarked} color="#F4A261" badge={`${citations.length} studies`}
            >
              <div className="space-y-6">
                {/* Plain English methodology */}
                <div className="space-y-2 text-sm text-[#8A93B2] leading-relaxed">
                  <p className="text-[#F0F2F8] font-medium text-xs uppercase tracking-wider mb-3">How AuRA works</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {[
                      { step: '1', title: 'We read your data', desc: 'Your uploaded labs, symptoms, and photos are processed right here on your device. Nothing is sent anywhere.' },
                      { step: '2', title: 'We compare it', desc: 'Your data is compared to patterns found in peer-reviewed medical studies to find the closest matches.' },
                      { step: '3', title: 'We show you the results', desc: 'The scores above show how closely your data matches known patterns — with full transparency into how each factor contributed.' },
                    ].map((item) => (
                      <div key={item.step} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="w-6 h-6 rounded-full bg-[#7B61FF]/10 text-[#7B61FF] text-xs font-mono flex items-center justify-center">{item.step}</span>
                          <span className="text-[#F0F2F8] font-medium">{item.title}</span>
                        </div>
                        <p>{item.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Citations */}
                <div>
                  <p className="text-[#F0F2F8] font-medium text-xs uppercase tracking-wider mb-3">Studies we referenced</p>
                  <div className="space-y-2">
                    {citations.map((cite) => (
                      <div key={cite.id} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] transition-colors group">
                        <span className="text-xs font-mono text-[#F4A261] mt-0.5 flex-shrink-0">[{cite.id}]</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[#F0F2F8] leading-snug">{cite.title}</p>
                          <p className="text-xs text-[#8A93B2] mt-1">{cite.journal} ({cite.year})</p>
                        </div>
                        <button className="flex-shrink-0 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-white/[0.04] transition-all">
                          <ExternalLink className="w-3.5 h-3.5 text-[#8A93B2]" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ExpandableSection>

            <div className="gradient-divider" />

            {/* ============ WHAT IT MEANS + IMPORTANT TO KNOW ============ */}
            <div id="next-steps" className="scroll-target space-y-6">
              {/* What it means — direct text, no expandable cards */}
              <div className="dashboard-card p-8 space-y-6">
                <h3 className="text-lg font-medium text-[#F0F2F8] flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-[#3ECFCF]/10">
                    <MessageSquare className="w-4 h-4 text-[#3ECFCF]" />
                  </div>
                  What This Means For You
                </h3>

                <div className="space-y-4">
                  {nextStepsData.map((step, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="p-2 rounded-lg flex-shrink-0 mt-0.5" style={{ backgroundColor: `${step.color}15` }}>
                        <step.icon className="w-4 h-4" style={{ color: step.color }} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#F0F2F8] mb-1">{step.title}</p>
                        <p className="text-sm text-[#8A93B2] leading-relaxed">{step.detail}</p>
                        {step.action && (
                          <span
                            onClick={() => step.action!.onClick()}
                            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 mt-2 rounded-lg bg-[#7B61FF]/10 text-[#7B61FF] hover:bg-[#7B61FF]/20 transition-colors cursor-pointer"
                          >
                            {step.action.label} <ChevronDown className="w-3 h-3 -rotate-90" />
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Important to know — direct text, no expandable cards */}
              <div className="dashboard-card glow-rose p-8 space-y-4 border-[#E07070]/10">
                <h3 className="text-lg font-medium text-[#F0F2F8] flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-[#E07070]/10">
                    <ShieldCheck className="w-4 h-4 text-[#E07070]" />
                  </div>
                  Important To Know
                </h3>

                <div className="space-y-4">
                  {notMeanData.map((item, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="p-2 rounded-lg flex-shrink-0 mt-0.5" style={{ backgroundColor: `${item.color}15` }}>
                        <item.icon className="w-4 h-4" style={{ color: item.color }} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#F0F2F8] mb-1">{item.title}</p>
                        <p className="text-sm text-[#8A93B2] leading-relaxed">{item.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ============ RECOMMENDED DOCTOR ============ */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="dashboard-card p-6 border-[#52D0A0]/20"
            >
              <h4 className="font-medium text-[#52D0A0] flex items-center gap-2 mb-4">
                <div className="p-1.5 rounded-lg bg-[#52D0A0]/10">
                  <MapPin className="w-4 h-4 text-[#52D0A0]" />
                </div>
                Recommended Doctor
              </h4>
              <div className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="w-12 h-12 rounded-full bg-[#52D0A0]/10 flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-[#52D0A0]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#F0F2F8]">Dr. Elena Rossi</p>
                  <p className="text-xs text-[#8A93B2]">Rheumatology • Complex Diagnostics</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-[#8A93B2] flex items-center gap-1"><MapPin className="w-3 h-3" /> 2.4 mi</span>
                    <span className="text-xs text-[#F4A261] flex items-center gap-1"><Star className="w-3 h-3 fill-[#F4A261]" /> 4.9</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-[#2563EB]/10 text-[#2563EB] border border-[#2563EB]/20">In Network</span>
                  </div>
                </div>
              </div>
              <p className="text-xs text-[#8A93B2] mt-3">
                Based on your autoimmune pattern match. <span className="text-[#52D0A0] cursor-pointer hover:underline" onClick={onViewCommunity}>See all specialists →</span>
              </p>
            </motion.div>

            {/* GP Script Callout */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
              className="dashboard-card p-6 border-[#3ECFCF]/20"
            >
              <div className="flex justify-between items-start mb-4">
                <h4 className="font-medium text-[#3ECFCF] flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-[#3ECFCF]/10">
                    <MessageSquare className="w-4 h-4 text-[#3ECFCF]" />
                  </div>
                  What to say at your next appointment
                </h4>
              </div>
              <p className="text-sm text-[#8A93B2] mb-5 italic leading-relaxed pl-4 border-l-2 border-[#3ECFCF]/20">
                "I've been tracking my symptoms for over a year. My blood work shows a sustained rise in inflammatory markers, and I've developed a recurring facial rash and joint pain. Here is a clinical summary generated from my lab trends and photos."
              </p>
              <Button onClick={handleCopy} variant="secondary" className="w-full text-sm py-2 h-10" icon={false}>
                {copied ? (
                  <motion.div initial={{ scale: 0.5 }} animate={{ scale: 1 }} className="flex items-center gap-2">
                    <Check className="w-4 h-4" /> Copied
                  </motion.div>
                ) : (
                  <div className="flex items-center gap-2"><Copy className="w-4 h-4" /> Copy Script</div>
                )}
              </Button>
            </motion.div>

            <div className="gradient-divider" />

            {/* ============ DAILY NOTES ============ */}
            <motion.div
              id="daily-notes"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}
              className="scroll-target dashboard-card p-8"
            >
              <DailyNotes />
            </motion.div>

            {/* Bottom spacer for floating dock clearance */}
            <div className="h-28" />
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
      <Tooltip.Content className="bg-[#1A1D26] text-white px-4 py-2 rounded-lg text-sm shadow-xl border border-[#2A2E3B] max-w-xs z-50" sideOffset={5}>
        {def}
        <Tooltip.Arrow className="fill-[#2A2E3B]" />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
);
