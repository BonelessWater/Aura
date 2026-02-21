import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Star, MapPin, X } from 'lucide-react';
import { clsx } from 'clsx';

interface SpecialistMapProps {
  onClose: () => void;
}

const specialists = [
  { id: 1, name: "Dr. Elena Rossi", specialty: "Rheumatology • Complex Diagnostics", dist: "2.4 mi", rating: 4.9, lat: 50, lng: 40, inNetwork: true },
  { id: 2, name: "Dr. James Chen", specialty: "Rheumatology • Lupus / SLE", dist: "5.1 mi", rating: 4.8, lat: 30, lng: 70, inNetwork: true },
  { id: 3, name: "Dr. Sarah Miller", specialty: "Clinical Immunology", dist: "8.3 mi", rating: 4.7, lat: 70, lng: 60, inNetwork: false },
  { id: 4, name: "Dr. David Kim", specialty: "Dermatology • Autoimmune", dist: "12.0 mi", rating: 4.9, lat: 60, lng: 20, inNetwork: true },
];

export const SpecialistMap = ({ onClose }: SpecialistMapProps) => {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [filterInNetwork, setFilterInNetwork] = useState(false);
  const [maxDistance, setMaxDistance] = useState<number | null>(null); // null = all

  const distanceOptions = [
    { label: 'Any Distance', value: null },
    { label: '< 5 mi', value: 5 },
    { label: '< 10 mi', value: 10 },
  ];

  const filteredSpecialists = specialists.filter(s => {
    if (filterInNetwork && !s.inNetwork) return false;
    if (maxDistance !== null && parseFloat(s.dist) > maxDistance) return false;
    return true;
  });

  // Close on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex bg-[#0A0D14]/90 backdrop-blur-sm">
      <div className="flex w-full h-full max-w-[1400px] mx-auto bg-[#0A0D14] shadow-2xl overflow-hidden relative border-l border-r border-[#1A1D26]">
        
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 z-50 p-2 bg-[#0A0D14]/80 text-white rounded-full hover:bg-[#1A1D26] transition-colors border border-[#2A2E3B]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Left List */}
        <div className="w-full md:w-[45%] h-full flex flex-col border-r border-[#1A1D26] bg-[#0A0D14] z-10 relative">
          <div className="p-6 border-b border-[#1A1D26]">
            <h2 className="text-2xl font-display font-medium text-white mb-2">Specialist Network</h2>
            <p className="text-sm text-[#8A93B2] mb-4">Matches based on your Systemic Autoimmune profile.</p>
            
            {/* Filter Chips */}
            <div className="flex flex-wrap gap-2">
              {distanceOptions.map(opt => (
                <button
                  key={String(opt.value)}
                  onClick={() => setMaxDistance(opt.value)}
                  className={clsx(
                    "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                    maxDistance === opt.value
                      ? "bg-[#7B61FF]/15 border-[#7B61FF]/40 text-[#7B61FF]"
                      : "border-[#2A2E3B] text-[#8A93B2] hover:text-white hover:border-[#8A93B2]/50"
                  )}
                >
                  {opt.label}
                </button>
              ))}
              <button
                onClick={() => setFilterInNetwork(!filterInNetwork)}
                className={clsx(
                  "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                  filterInNetwork
                    ? "bg-[#3ECFCF]/15 border-[#3ECFCF]/40 text-[#3ECFCF]"
                    : "border-[#2A2E3B] text-[#8A93B2] hover:text-white hover:border-[#8A93B2]/50"
                )}
              >
                In-Network Only
              </button>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {filteredSpecialists.length === 0 && (
              <div className="text-center py-12 text-[#8A93B2] text-sm">
                No specialists match your current filters. Try adjusting distance or network preferences.
              </div>
            )}
            {filteredSpecialists.map((spec) => (
              <motion.div
                key={spec.id}
                onMouseEnter={() => setHoveredId(spec.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={clsx(
                  "p-5 rounded-xl border transition-all cursor-pointer group relative overflow-hidden",
                  hoveredId === spec.id 
                    ? "bg-[#1A1D26] border-[#7B61FF]" 
                    : "bg-[#13161F] border-[#2A2E3B] hover:border-[#8A93B2]/50"
                )}
              >
                {hoveredId === spec.id && (
                   <motion.div 
                     layoutId="highlight"
                     className="absolute left-0 top-0 bottom-0 w-1 bg-[#7B61FF]" 
                   />
                )}
                
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium text-lg text-[#F0F2F8] group-hover:text-[#7B61FF] transition-colors">{spec.name}</h3>
                  <div className="flex items-center gap-1 text-[#F4A261] bg-[#F4A261]/10 px-2 py-0.5 rounded text-xs font-bold">
                    <Star className="w-3 h-3 fill-current" /> {spec.rating}
                  </div>
                </div>
                
                <p className="text-sm text-[#8A93B2] mb-3">{spec.specialty}</p>
                
                <div className="flex items-center justify-between mt-4">
                   <span className="text-xs text-[#8A93B2] flex items-center gap-1">
                     <MapPin className="w-3 h-3" /> {spec.dist}
                   </span>
                   <span className={clsx(
                     "text-xs px-2 py-1 rounded border",
                     spec.inNetwork
                       ? "bg-[#3ECFCF]/10 text-[#3ECFCF] border-[#3ECFCF]/20"
                       : "bg-[#E07070]/10 text-[#E07070] border-[#E07070]/20"
                   )}>
                     {spec.inNetwork ? 'In Network' : 'Out of Network'}
                   </span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right Map (Mock) */}
        <div className="hidden md:block w-[55%] h-full relative bg-[#15171e] overflow-hidden">
          {/* Map Base - Dark Grid */}
          <div className="absolute inset-0 opacity-20" 
               style={{ 
                 backgroundImage: 'radial-gradient(#2A2E3B 1px, transparent 1px)', 
                 backgroundSize: '30px 30px' 
               }} 
          />
          
          {/* User Location */}
          <div className="absolute top-[80%] left-[50%] transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group">
             <div className="w-4 h-4 rounded-full bg-[#3ECFCF] shadow-[0_0_20px_#3ECFCF] animate-pulse" />
             <span className="mt-2 text-xs font-medium text-[#3ECFCF] bg-[#0A0D14]/80 px-2 py-1 rounded">You</span>
          </div>

          {/* Specialist Pins */}
          {filteredSpecialists.map((spec) => {
            const isHovered = hoveredId === spec.id;
            
            return (
              <div key={spec.id} className="absolute inset-0 pointer-events-none">
                {/* Connecting Line */}
                <svg className="absolute inset-0 pointer-events-none w-full h-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <AnimatePresence>
                    {hoveredId === spec.id && (
                      <motion.path
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 1 }}
                        exit={{ opacity: 0 }}
                        d={`M 50 80 Q 50 ${(spec.lat + 80) / 2} ${spec.lng} ${spec.lat}`} 
                        fill="none"
                        stroke="#7B61FF"
                        strokeWidth="0.5"
                        strokeDasharray="1 1"
                        className="drop-shadow-[0_0_8px_rgba(123,97,255,0.5)]"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </AnimatePresence>
                </svg>

                {/* Pin */}
                <motion.div
                  className="absolute cursor-pointer pointer-events-auto"
                  style={{ top: `${spec.lat}%`, left: `${spec.lng}%` }}
                  animate={{ scale: isHovered ? 1.4 : 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                >
                  <div className={clsx(
                    "relative flex items-center justify-center w-10 h-10 -translate-x-1/2 -translate-y-1/2",
                    isHovered ? "z-50" : "z-10"
                  )}>
                    {/* Glow */}
                    <div className={clsx(
                      "absolute inset-0 rounded-full blur-md transition-colors duration-300",
                      isHovered ? "bg-[#7B61FF]/60" : "bg-[#7B61FF]/20"
                    )} />
                    
                    {/* Hexagon Shape */}
                    <div className="relative w-8 h-8 bg-[#1A1D26] flex items-center justify-center hexagon clip-path-polygon-[25%_0%,_75%_0%,_100%_50%,_75%_100%,_25%_100%,_0%_50%] border-2 border-[#7B61FF]">
                       <div className="absolute inset-0 bg-[#7B61FF] opacity-20" />
                       <MapPin className="w-4 h-4 text-[#7B61FF]" />
                    </div>
                  </div>
                  
                  <AnimatePresence>
                    {isHovered && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute top-6 left-1/2 -translate-x-1/2 bg-[#0A0D14] border border-[#2A2E3B] px-3 py-1.5 rounded-lg whitespace-nowrap z-50 shadow-xl"
                      >
                        <span className="text-sm font-medium text-white">{spec.name}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
