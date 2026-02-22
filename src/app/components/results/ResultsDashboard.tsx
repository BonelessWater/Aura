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
import { AppleWatchPanel } from './AppleWatchPanel';
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

const MiniChart = ({ data, color, label, unit, current, normal, description, onClick }: {
  data: { month: string; value: number }[]; color: string; label: string;
  unit: string; current: string; normal: string; description: string; onClick: () => void;
}) => {
  const first = data[0]?.value ?? 0;
  const last = data[data.length - 1]?.value ?? 0;
  const goingUp = last >= first;
  return (
    <button onClick={onClick} className="dashboard-card p-4 hover:border-white/[0.12] transition-all text-left w-full group space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[#F0F2F8]">{label}</span>
        <span className="text-[10px] text-[#8A93B2] group-hover:text-white transition-colors flex items-center gap-1">
          Tap to see graph
        </span>
      </div>

      {/* Trend indicator */}
      <div className="flex items-center gap-2">
        <div className="flex items-center justify-center w-8 h-8 rounded-full" style={{ backgroundColor: `${color}18` }}>
          {goingUp
            ? <TrendingUp className="w-4 h-4" style={{ color }} />
            : <TrendingUp className="w-4 h-4 rotate-180" style={{ color }} />}
        </div>
        <div>
          <p className="text-xs font-medium" style={{ color }}>
            {goingUp ? 'Going up' : 'Going down'}
          </p>
          <p className="text-[10px] text-[#8A93B2]">
            {current} {unit} &nbsp;&middot;&nbsp; normal: {normal}
          </p>
        </div>
      </div>

      {/* Plain description */}
      <p className="text-[11px] text-[#C8CDE0] leading-snug">{description}</p>
    </button>
  );
};


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
  const [expandedPatientMetric, setExpandedPatientMetric] = useState<string | null>(null);
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
    const sections = ['scores', 'lab-trends', 'next-steps', 'daily-notes', 'patient-data'];
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
    { id: 'patient-data', icon: Activity, label: "Patient Data" },
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

        {/* Glass pane — frosted layer over blood cell background */}
        <div className="fixed inset-0 pointer-events-none z-[1] bg-[#020005]/15" />

        {/* Content sits above glass pane */}
        <div className="relative z-[2] flex flex-col flex-1 overflow-hidden">

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
                    <div className="dashboard-card p-6 space-y-5">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h4 className="text-sm font-semibold text-[#F0F2F8]">Here's what went into your score</h4>
                          <p className="text-xs text-[#8A93B2] mt-0.5">We looked at 5 types of evidence and measured how strongly each one pointed to a pattern.</p>
                        </div>
                        <button onClick={() => setExpandedScore(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors shrink-0 mt-0.5">Close</button>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
                        {/* Patient-friendly evidence rows */}
                        <div className="space-y-4">
                          {[
                            { name: 'Your blood tests', detail: 'Markers like CRP, WBC, and ANA all pointed clearly in the same direction.', score: 94, weight: 35, color: '#7B61FF' },
                            { name: 'Your reported symptoms', detail: 'Joint pain, fatigue, and your rash pattern closely match known profiles.', score: 88, weight: 25, color: '#3ECFCF' },
                            { name: 'Photo analysis', detail: 'The facial rash you shared was identified as consistent with a malar rash.', score: 95, weight: 20, color: '#F4A261' },
                            { name: 'How long symptoms have lasted', detail: 'Symptoms building over 18+ months fits the timeline seen in research cases.', score: 90, weight: 12, color: '#52D0A0' },
                            { name: 'Published research match', detail: 'Cases with a similar profile appear frequently in autoimmune literature.', score: 87, weight: 8, color: '#E07070' },
                          ].map((item) => {
                            const signal = item.score >= 90 ? 'Very strong' : item.score >= 80 ? 'Strong' : 'Moderate';
                            return (
                              <div key={item.name} className="space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-[#F0F2F8] font-medium">{item.name}</span>
                                  <span className="text-[#8A93B2]">{item.weight}% of score</span>
                                </div>
                                <div className="h-1.5 w-full rounded-full bg-white/[0.07]">
                                  <motion.div
                                    className="h-1.5 rounded-full"
                                    style={{ backgroundColor: item.color }}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${item.score}%` }}
                                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                                  />
                                </div>
                                <div className="flex items-start justify-between gap-2 text-[10px]">
                                  <span className="text-[#8A93B2] leading-snug">{item.detail}</span>
                                  <span className="shrink-0 font-semibold" style={{ color: item.color }}>{signal}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Radar Chart — unchanged */}
                        <div>
                          <p className="text-xs text-[#8A93B2] mb-3">Pattern alignment across markers</p>
                          <div className="h-56">
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

                      <p className="text-xs text-[#8A93B2] pt-3 border-t border-white/[0.05]">
                        Blood tests carry the most weight because they give us the most objective evidence. No single factor decides your score — everything you shared added up together.
                      </p>
                    </div>
                  </motion.div>
                )}

                {expandedScore === 'secondary' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="dashboard-card p-6 space-y-5">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h4 className="text-sm font-semibold text-[#F0F2F8]">Why this condition came up — and what's still missing</h4>
                          <p className="text-xs text-[#8A93B2] mt-0.5">Out of everything we compared your data to, one condition matched most closely.</p>
                        </div>
                        <button onClick={() => setExpandedScore(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors shrink-0 mt-0.5">Close</button>
                      </div>

                      <p className="text-sm text-[#8A93B2] leading-relaxed">
                        <TooltipTerm term="Systemic Lupus Erythematosus (SLE)" def="An autoimmune disease where your immune system mistakenly attacks healthy tissue, causing widespread inflammation." /> was the closest match to your profile.
                        A 65% match means several key signs lined up — but not everything. Some important tests haven't been done yet, so we can't say more than that. Only a doctor can tell you what this means for you.
                      </p>

                      <div className="space-y-2">
                        {[
                          { label: 'Facial rash pattern', desc: 'Matches a type of rash strongly associated with Lupus.', status: 'Matched', color: '#52D0A0' },
                          { label: 'Inflammation levels (CRP)', desc: 'Your CRP has been rising steadily — a clear sign of ongoing inflammation.', status: 'Matched', color: '#52D0A0' },
                          { label: 'Low white blood cell count', desc: 'Your WBC has been declining, which sometimes occurs in this condition.', status: 'Partial', color: '#F4A261' },
                          { label: 'Anti-dsDNA antibody test', desc: "This specific blood test hasn't been run yet — it would significantly clarify the picture.", status: 'Not yet tested', color: '#8A93B2' },
                        ].map((item) => (
                          <div key={item.label} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                            <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: item.color }} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs font-medium text-[#F0F2F8]">{item.label}</span>
                                <span className="text-[10px] font-semibold shrink-0" style={{ color: item.color }}>{item.status}</span>
                              </div>
                              <p className="text-[11px] text-[#8A93B2] mt-0.5 leading-snug">{item.desc}</p>
                            </div>
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
              <h3 className="text-lg font-medium text-[#F0F2F8] mb-6">
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
                <h3 className="text-lg font-medium text-[#F0F2F8]">
                  Your Blood Work
                </h3>
                <span className="text-xs text-[#8A93B2]">18 months of tracking — tap any card to learn more</span>
              </div>

              {/* Mini chart grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MiniChart
                  data={crpTrendData} color="#E07070" label="Inflammation (CRP)"
                  unit="mg/L" current="14.1" normal="< 3.0"
                  description="Your inflammation marker has been steadily rising over the past 18 months and is currently well above the normal range."
                  onClick={() => setExpandedLab(expandedLab === 'crp' ? null : 'crp')}
                />
                <MiniChart
                  data={wbcTrendData} color="#3ECFCF" label="Immune Cells (WBC)"
                  unit="× 10⁹/L" current="2.8" normal="4.5 – 11.0"
                  description="Your white blood cell count has been gradually declining and is now below the healthy range. These cells are key to fighting infection."
                  onClick={() => setExpandedLab(expandedLab === 'wbc' ? null : 'wbc')}
                />
                <MiniChart
                  data={anaTrendData} color="#F4A261" label="Immune Activation (ANA)"
                  unit="titer" current="1:640" normal="< 1:80"
                  description="A marker that can indicate your immune system is reacting to your own cells. Yours has risen significantly and is above the threshold doctors watch closely."
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
                    <div className="dashboard-card p-6 space-y-5">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <h4 className="text-sm font-semibold text-[#F0F2F8]">
                            {expandedLab === 'crp' && 'Your inflammation level over time'}
                            {expandedLab === 'wbc' && 'Your immune cell count over time'}
                            {expandedLab === 'ana' && 'Your immune activation marker over time'}
                          </h4>
                          <p className="text-xs mt-0.5" style={{ color: expandedLab === 'crp' ? '#E07070' : expandedLab === 'wbc' ? '#3ECFCF' : '#F4A261' }}>
                            {expandedLab === 'crp' && 'Currently above normal — trending upward'}
                            {expandedLab === 'wbc' && 'Currently below normal — trending downward'}
                            {expandedLab === 'ana' && 'Currently above normal — trending upward'}
                          </p>
                        </div>
                        <button onClick={() => setExpandedLab(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors shrink-0 mt-0.5">Close</button>
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

                      <div className="space-y-3">
                        {/* Plain English explanation */}
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] text-sm text-[#8A93B2] leading-relaxed">
                          {expandedLab === 'crp' && (
                            <>
                              <p className="text-[#F0F2F8] font-medium text-xs mb-2">What this is</p>
                              CRP is a protein your liver releases when there's inflammation somewhere in your body. Think of it like a smoke alarm — the higher it goes, the more your body senses something is wrong.
                              Yours has been climbing steadily from <span className="text-[#F0F2F8] font-semibold">3.2</span> to <span className="text-[#E07070] font-semibold">14.1 mg/L</span> over 18 months.
                              Normal is below 3.0. A level that stays this high for this long is one of the clearest signals that your body has been under persistent stress — and it was a major factor in your score.
                            </>
                          )}
                          {expandedLab === 'wbc' && (
                            <>
                              <p className="text-[#F0F2F8] font-medium text-xs mb-2">What this is</p>
                              White blood cells are your body's defense system — they fight infection and keep you healthy. When the count is low, it can mean your immune system is overworked or attacking the wrong things.
                              Yours has dropped from <span className="text-[#F0F2F8] font-semibold">5.8</span> to <span className="text-[#3ECFCF] font-semibold">2.8</span> — now below the healthy range of 4.5–11.0.
                              A slow, steady decline like this is something doctors watch closely, particularly in people with autoimmune patterns.
                            </>
                          )}
                          {expandedLab === 'ana' && (
                            <>
                              <p className="text-[#F0F2F8] font-medium text-xs mb-2">What this is</p>
                              ANA stands for antinuclear antibodies — basically, proteins your immune system makes when it starts reacting to parts of your own cells instead of outside invaders.
                              Yours has risen from <span className="text-[#F0F2F8] font-semibold">1:80</span> to <span className="text-[#F4A261] font-semibold">1:640</span>. Anything above 1:160 is considered worth investigating.
                              Rising ANA on its own isn't a diagnosis — but combined with your other results, it's a pattern a doctor needs to look at.
                            </>
                          )}
                        </div>
                        {/* What to do */}
                        <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-[#7B61FF]/[0.06] border border-[#7B61FF]/20 text-xs text-[#8A93B2]">
                          <Info className="w-3.5 h-3.5 text-[#7B61FF] mt-0.5 shrink-0" />
                          <span>These numbers are from your uploaded records. A doctor can tell you exactly what they mean in the context of your full health history.</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="gradient-divider" />

            {/* ============ WHAT IT MEANS ============ */}
            <div id="next-steps" className="scroll-target">
              <div className="dashboard-card overflow-hidden">

                {/* Header */}
                <div className="px-8 pt-8 pb-6 border-b border-white/[0.05]">
                  <h3 className="text-lg font-semibold text-[#F0F2F8]">
                    What This Means For You
                  </h3>
                  <p className="text-sm text-[#8A93B2] mt-1.5">A plain-English summary of what AuRA found and what to do next.</p>
                </div>

                <div className="p-8 space-y-6">

                  {/* Finding — most prominent */}
                  <div className="rounded-2xl border border-[#3ECFCF]/20 bg-[#3ECFCF]/[0.04] p-5 space-y-2">
                    <p className="text-xs font-semibold text-[#3ECFCF] uppercase tracking-wider">What we found</p>
                    <p className="text-sm text-[#C8CDE0] leading-relaxed">
                      Your inflammation marker (CRP) has been rising steadily for 18 months, your immune cell count has been falling, and your immune activation marker (ANA) is significantly elevated. Together, this pattern closely matches what's seen in people with autoimmune conditions in published research.
                    </p>
                  </div>

                  {/* Recommended action */}
                  <div className="rounded-2xl border border-[#7B61FF]/20 bg-[#7B61FF]/[0.04] p-5 space-y-2">
                    <p className="text-xs font-semibold text-[#7B61FF] uppercase tracking-wider">Your recommended next step</p>
                    <p className="text-sm text-[#C8CDE0] leading-relaxed">
                      See a Rheumatologist. They specialize in exactly the kind of patterns we found and can order the specific tests needed to figure out what's really going on — things like anti-dsDNA and complement levels that haven't been checked yet.
                    </p>
                  </div>

                  {/* SOAP note callout */}
                  <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5 space-y-1">
                      <p className="text-sm font-semibold text-[#F0F2F8]">Your doctor summary is ready</p>
                      <p className="text-sm text-[#8A93B2] leading-relaxed">
                        We've prepared a structured clinical note from your labs, symptoms, and photos — formatted the way doctors expect to see it. Hand it to any doctor to get the conversation started faster.
                      </p>
                      <span
                        onClick={onViewSOAP}
                        className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 mt-2 rounded-lg bg-[#F4A261]/10 text-[#F4A261] hover:bg-[#F4A261]/20 transition-colors cursor-pointer"
                      >
                        View Doctor Summary <ChevronDown className="w-3 h-3 -rotate-90" />
                      </span>
                  </div>

                  {/* Reassurance block */}
                  <div className="rounded-2xl border border-[#E07070]/15 bg-[#E07070]/[0.04] p-5 space-y-3">
                    <p className="text-xs font-semibold text-[#E07070] uppercase tracking-wider">Important — please read this</p>
                    <div className="space-y-2 text-sm text-[#C8CDE0] leading-relaxed">
                      <p>
                        <span className="font-semibold text-[#F0F2F8]">This is not a diagnosis.</span> AuRA matches patterns in data — it cannot tell you what condition you have. Only a licensed doctor can do that after a proper clinical evaluation.
                      </p>
                      <p>
                        The 92% score means your data <span className="italic">strongly resembles</span> autoimmune profiles in research. The 65% SLE match means it was the closest fit we found — not that you have SLE. Other conditions can look exactly the same.
                      </p>
                    </div>
                  </div>

                  {/* References — compact footer */}
                  <div className="space-y-2 pt-1">
                    <p className="text-[10px] uppercase tracking-widest text-[#6A7390] font-medium">Research referenced</p>
                    <ul className="space-y-1.5">
                      {citations.map((cite) => (
                        <li key={cite.id} className="flex items-start gap-2">
                          <span className="font-mono text-[10px] text-[#F4A261] shrink-0 mt-0.5">[{cite.id}]</span>
                          <p className="text-[11px] text-[#6A7390] leading-snug">
                            {cite.title}
                            <span className="text-[#52536A]"> — {cite.journal}, {cite.year}</span>
                          </p>
                        </li>
                      ))}
                    </ul>
                  </div>

                </div>
              </div>
            </div>

            {/* ============ PATIENT DATA ============ */}
            <motion.div
              id="patient-data"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="scroll-target space-y-4"
            >
              {/* Header */}
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-medium text-[#F0F2F8]">Your Health Picture</h3>
                  <p className="text-sm text-[#8A93B2] mt-0.5">18 months of data. Your numbers tell a clear story — tap any card for the full graph.</p>
                </div>
                <span className="text-[10px] font-semibold bg-[#3ECFCF]/10 text-[#3ECFCF] border border-[#3ECFCF]/20 px-2.5 py-1 rounded-full">
                  9 data points tracked
                </span>
              </div>

              {/* Metric cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {([
                  {
                    id: 'pat-crp',
                    label: 'Inflammation',
                    sublabel: 'CRP level',
                    value: '14.1',
                    unit: 'mg/L',
                    normalRange: 'Normal: < 3.0',
                    status: 'Above Normal',
                    statusColor: '#E07070',
                    trend: 'up' as const,
                    trendLabel: '+340% over 18 months',
                    plainDesc: "Your body has been signalling inflammation for a long time. This number was already elevated when you started tracking — and it's still climbing.",
                    data: crpTrendData,
                    color: '#E07070',
                    chartTitle: 'Your inflammation level over time',
                    chartSubtitle: 'Steadily rising — now 4.7× the upper limit of normal',
                    explanation: 'CRP is a protein your liver releases when it detects inflammation. Yours rose from 3.2 to 14.1 mg/L over 18 months — a 340% increase. The normal ceiling is 3.0. A marker this consistently elevated, with no downturn, is one of the clearest signals in your data.',
                  },
                  {
                    id: 'pat-wbc',
                    label: 'Immune Defense',
                    sublabel: 'White Blood Cells',
                    value: '2.8',
                    unit: '× 10⁹/L',
                    normalRange: 'Normal: 4.5 – 11.0',
                    status: 'Below Normal',
                    statusColor: '#3ECFCF',
                    trend: 'down' as const,
                    trendLabel: '−52% over 18 months',
                    plainDesc: 'The cells that fight infections are running low and still dropping. A slow, steady decline like this over 18 months is harder to explain than a one-off dip.',
                    data: wbcTrendData,
                    color: '#3ECFCF',
                    chartTitle: 'Your immune cell count over time',
                    chartSubtitle: 'Slowly falling — now below the healthy minimum',
                    explanation: 'White blood cells are your immune defense. A healthy count sits between 4.5 and 11.0. Yours has dropped from 5.8 to 2.8 — a 52% fall over 18 months. The gradual, consistent direction of this decline, combined with your other results, is what makes it significant.',
                  },
                  {
                    id: 'pat-ana',
                    label: 'Immune Signal',
                    sublabel: 'ANA Titer',
                    value: '1:640',
                    unit: '',
                    normalRange: 'Normal: < 1:80',
                    status: 'Elevated',
                    statusColor: '#F4A261',
                    trend: 'up' as const,
                    trendLabel: '8× increase over 18 months',
                    plainDesc: 'A marker that can mean your immune system is reacting to your own cells. Yours went from the edge of normal to significantly elevated — and it keeps rising.',
                    data: anaTrendData,
                    color: '#F4A261',
                    chartTitle: 'Your immune activation marker over time',
                    chartSubtitle: 'Climbed from borderline to significantly elevated',
                    explanation: 'ANA (antinuclear antibodies) tests whether your immune system is making antibodies against your own cells. Yours rose from 1:80 — the edge of acceptable — to 1:640. Clinicians pay attention above 1:160. The consistent rise over time is what matters most here.',
                  },
                ] as const).map(metric => (
                  <button
                    key={metric.id}
                    onClick={() => setExpandedPatientMetric(expandedPatientMetric === metric.id ? null : metric.id)}
                    className="dashboard-card p-4 text-left hover:border-white/[0.12] transition-all group space-y-3 w-full"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-semibold text-[#F0F2F8]">{metric.label}</p>
                        <p className="text-[10px] text-[#555870]">{metric.sublabel}</p>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                        style={{ background: `${metric.statusColor}15`, color: metric.statusColor, border: `1px solid ${metric.statusColor}30` }}>
                        {metric.status}
                      </span>
                    </div>

                    <div className="flex items-end gap-1.5">
                      <span className="text-2xl font-mono font-bold" style={{ color: metric.statusColor }}>{metric.value}</span>
                      {metric.unit && <span className="text-[10px] text-[#555870] mb-1">{metric.unit}</span>}
                    </div>

                    <div className="flex items-center gap-1">
                      <span className="text-[10px] font-semibold" style={{ color: metric.statusColor }}>
                        {metric.trend === 'up' ? '↑' : '↓'} {metric.trendLabel}
                      </span>
                    </div>

                    <p className="text-[11px] text-[#8A93B2] leading-snug">{metric.plainDesc}</p>

                    <p className="text-[10px] text-[#4A5070] group-hover:text-[#7B61FF] transition-colors">
                      {expandedPatientMetric === metric.id ? 'Hide graph ↑' : 'See graph →'}
                    </p>
                  </button>
                ))}
              </div>

              {/* Expanded graph panel */}
              <AnimatePresence>
                {expandedPatientMetric && (() => {
                  const metrics = [
                    { id: 'pat-crp', data: crpTrendData, color: '#E07070', chartTitle: 'Your inflammation level over time', chartSubtitle: 'Steadily rising — now 4.7× the upper limit of normal', explanation: 'CRP is a protein your liver releases when it detects inflammation. Yours rose from 3.2 to 14.1 mg/L over 18 months — a 340% increase. The normal ceiling is 3.0. A marker this consistently elevated, with no downturn, is one of the clearest signals in your data.' },
                    { id: 'pat-wbc', data: wbcTrendData, color: '#3ECFCF', chartTitle: 'Your immune cell count over time', chartSubtitle: 'Slowly falling — now below the healthy minimum', explanation: 'White blood cells are your immune defense. A healthy count sits between 4.5 and 11.0. Yours has dropped from 5.8 to 2.8 — a 52% fall over 18 months. The gradual, consistent direction of this decline, combined with your other results, is what makes it significant.' },
                    { id: 'pat-ana', data: anaTrendData, color: '#F4A261', chartTitle: 'Your immune activation marker over time', chartSubtitle: 'Climbed from borderline to significantly elevated', explanation: 'ANA tests whether your immune system is making antibodies against your own cells. Yours rose from 1:80 to 1:640. Clinicians pay attention above 1:160. The consistent rise over time is what matters most here.' },
                  ];
                  const m = metrics.find(x => x.id === expandedPatientMetric);
                  if (!m) return null;
                  return (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="dashboard-card p-6 space-y-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h4 className="text-sm font-semibold text-[#F0F2F8]">{m.chartTitle}</h4>
                            <p className="text-xs mt-0.5" style={{ color: m.color }}>{m.chartSubtitle}</p>
                          </div>
                          <button onClick={() => setExpandedPatientMetric(null)} className="text-xs text-[#8A93B2] hover:text-white transition-colors shrink-0 mt-0.5">Close</button>
                        </div>
                        <div className="h-52">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={m.data} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                              <defs>
                                <linearGradient id={`pg-${m.id}`} x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="0%" stopColor={m.color} stopOpacity={0.3} />
                                  <stop offset="100%" stopColor={m.color} stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid stroke="#1A1D26" strokeDasharray="3 3" />
                              <XAxis dataKey="month" tick={{ fill: '#8A93B2', fontSize: 11 }} axisLine={false} tickLine={false} />
                              <YAxis tick={{ fill: '#8A93B2', fontSize: 11 }} axisLine={false} tickLine={false} />
                              <Area type="monotone" dataKey="value" stroke={m.color} strokeWidth={2} fill={`url(#pg-${m.id})`}
                                dot={{ fill: '#0A0D14', stroke: m.color, strokeWidth: 2, r: 4 }}
                                activeDot={{ r: 6 }}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] text-xs text-[#8A93B2] leading-relaxed">
                          <p className="text-[#F0F2F8] font-medium text-xs mb-2">What this means</p>
                          {m.explanation}
                        </div>
                      </div>
                    </motion.div>
                  );
                })()}
              </AnimatePresence>

              {/* Live heart rate — unchanged */}
              <div className="dashboard-card p-6">
                <p className="text-xs font-semibold text-[#F0F2F8] mb-1">Live Vitals</p>
                <p className="text-[11px] text-[#555870] mb-4">Real-time data from your wearable</p>
                <AppleWatchPanel />
              </div>
            </motion.div>

            {/* ============ RECOMMENDED DOCTOR ============ */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="dashboard-card p-6 border-[#52D0A0]/20"
            >
              <h4 className="font-medium text-[#52D0A0] mb-4">
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
                <h4 className="font-medium text-[#3ECFCF]">
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
        </div>{/* end z-[2] content wrapper */}
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
