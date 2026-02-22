import React from 'react';
import { motion } from 'motion/react';
import { useNavigate, useLocation } from 'react-router';

/** Generative abstract avatar SVG based on a seed string */
const GenerativeAvatar = ({ seed, size = 36 }: { seed: string; size?: number }) => {
  // Simple deterministic hash from seed
  const hash = seed.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const hue1 = (hash * 37) % 360;
  const hue2 = (hash * 73) % 360;
  const r1 = 6 + (hash % 5);
  const r2 = 4 + ((hash * 3) % 6);
  const cx2 = 22 + (hash % 10);
  const cy2 = 10 + ((hash * 2) % 14);

  return (
    <svg width={size} height={size} viewBox="0 0 36 36" className="rounded-full">
      <rect width="36" height="36" rx="18" fill={`hsl(${hue1}, 40%, 15%)`} />
      <circle cx="18" cy="18" r={r1} fill={`hsl(${hue1}, 60%, 55%)`} opacity="0.7" />
      <circle cx={cx2} cy={cy2} r={r2} fill={`hsl(${hue2}, 50%, 60%)`} opacity="0.5" />
      <circle cx={12} cy={24} r={3 + (hash % 3)} fill={`hsl(${hue1}, 70%, 70%)`} opacity="0.3" />
    </svg>
  );
};

export const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const isHome = location.pathname === '/';
  const isVault = location.pathname === '/vault';
  const isPresent = location.pathname === '/present';

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 z-[100] h-16 flex items-center justify-between px-6 md:px-10 bg-[#0A0D14]/60 backdrop-blur-xl border-b border-white/[0.04]"
    >
      {/* Left: Logo */}
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 group"
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#7B61FF] to-[#2563EB] flex items-center justify-center">
          <span className="text-white text-sm font-mono font-bold">A</span>
        </div>
        <span className="font-display text-lg text-white/90 tracking-wide hidden sm:inline group-hover:text-white transition-colors">
          Aura
        </span>
      </button>

      {/* Center: Present link */}
      <button
        onClick={() => navigate('/present')}
        className={`hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all ${
          isPresent
            ? 'bg-[#7B61FF]/20 text-[#7B61FF] border border-[#7B61FF]/30'
            : 'text-[#8A93B2] hover:text-[#F0F2F8] hover:bg-white/5'
        }`}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="opacity-70">
          <rect x="1" y="1" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
          <path d="M4 6l2-2 2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Present
      </button>

      {/* Right: Avatar */}
      <button
        onClick={() => navigate(isVault ? '/' : '/vault')}
        className={`relative rounded-full transition-all ${isVault
            ? 'ring-2 ring-[#2563EB] ring-offset-2 ring-offset-[#0A0D14]'
            : 'hover:ring-2 hover:ring-[#7B61FF]/50 hover:ring-offset-2 hover:ring-offset-[#0A0D14]'
          }`}
      >
        <GenerativeAvatar seed="aura_user_42" size={36} />
        {/* Online indicator */}
        <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-[#52D0A0] rounded-full border-2 border-[#0A0D14]" />
      </button>
    </motion.nav>
  );
};

export { GenerativeAvatar };
