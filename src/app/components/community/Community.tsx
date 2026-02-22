import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Heart, MessageSquare, Share2, Plus, ShieldAlert, X, MapPin, Star,
  ArrowBigUp, ArrowBigDown, TrendingUp, Clock, Flame, Search,
  Users, Bookmark, Award
} from 'lucide-react';
import { clsx } from 'clsx';

interface CommunityProps {
  onClose: () => void;
}

const categories = [
  { id: 'all', label: 'All', icon: Flame, color: '#F4A261' },
  { id: 'specialists', label: 'Find a Doctor', icon: MapPin, color: '#52D0A0' },
  { id: 'stories', label: 'My Journey', icon: Heart, color: '#E07070' },
  { id: 'research', label: 'Research', icon: TrendingUp, color: '#7B61FF' },
  { id: 'tips', label: 'Tips & Advice', icon: Award, color: '#3ECFCF' },
  { id: 'support', label: 'Support', icon: Users, color: '#2563EB' },
];

const threads = [
  {
    id: 1, category: 'specialists',
    title: 'Best Rheumatologists in Atlanta, GA?',
    author: 'Lupus_fighter_ATL', avatarColor: '#52D0A0',
    content: 'Just got flagged with a 92% autoimmune pattern match. Looking for a good rheumatologist in the Atlanta metro area — preferably in-network with Aetna. Any recommendations?',
    upvotes: 84, comments: 23, time: '2h ago', pinned: true,
    flair: 'Atlanta, GA', flairColor: '#52D0A0',
    replies: [
      { author: 'Joint_journal', content: 'Dr. Elena Rossi at Emory is incredible. She took the time to actually read my Aura summary. Accepts Aetna PPO.', upvotes: 41, time: '1h ago', avatarColor: '#F4A261' },
      { author: 'CRP_watcher', content: 'I second Dr. Rossi. Also, Dr. James Chen at Grady does lupus-specific work. Both are fantastic.', upvotes: 28, time: '45m ago', avatarColor: '#7B61FF' },
    ],
  },
  {
    id: 2, category: 'specialists',
    title: 'Immunologist recommendations — NYC / Tri-State?',
    author: 'Rash_detective', avatarColor: '#3ECFCF',
    content: 'My AuRA results suggest autoimmune involvement but my GP is dismissing them. Need a specialist in the NYC area who takes patient-driven data seriously. HSS? NYU Langone?',
    upvotes: 127, comments: 45, time: '5h ago', pinned: false,
    flair: 'New York, NY', flairColor: '#2563EB',
    replies: [
      { author: 'Butterfly_warrior', content: 'Dr. Sarah Kim at HSS is phenomenal. She actually asked me to bring my AuRA SOAP note to our second visit.', upvotes: 63, time: '3h ago', avatarColor: '#E07070' },
    ],
  },
  {
    id: 3, category: 'stories',
    title: 'Finally got my diagnosis after 3 years — AuRA helped',
    author: 'Butterfly_warrior', avatarColor: '#E07070',
    content: "After three years of being told it's \"just stress,\" I showed my rheumatologist the SOAP note and clinical summary from AuRA. She ordered an ANA panel that same day. Positive. Anti-dsDNA positive. I finally have answers. Don't give up.",
    upvotes: 342, comments: 67, time: '1d ago', pinned: false,
    flair: 'Success Story', flairColor: '#52D0A0',
    replies: [],
  },
  {
    id: 4, category: 'research',
    title: 'New study links sustained CRP elevation to earlier Lupus onset',
    author: 'CRP_tracker', avatarColor: '#7B61FF',
    content: 'Published in Rheumatology last week — patients with CRP trending above 8 mg/L for 12+ months had 3.2x higher odds of SLE dx within 2 years. Exactly the pattern AuRA flagged for me.',
    upvotes: 219, comments: 34, time: '8h ago', pinned: false,
    flair: 'Published Research', flairColor: '#7B61FF',
    replies: [],
  },
  {
    id: 5, category: 'tips',
    title: 'How I got my GP to take the SOAP note seriously',
    author: 'Joint_journal', avatarColor: '#F4A261',
    content: "Tip: print the SOAP note, don't just show your phone. I formatted mine as a PDF and brought it with my latest lab results. My GP was skeptical at first but said the structured format was actually helpful.",
    upvotes: 156, comments: 42, time: '12h ago', pinned: false,
    flair: 'Pro Tip', flairColor: '#3ECFCF',
    replies: [],
  },
  {
    id: 6, category: 'specialists',
    title: 'Lupus-friendly dermatologists in Chicago?',
    author: 'Malar_monitor', avatarColor: '#F4A261',
    content: "My AuRA results show a strong malar rash match and I need a dermatologist who understands autoimmune skin conditions. Chicago area, ideally north side.",
    upvotes: 38, comments: 11, time: '6h ago', pinned: false,
    flair: 'Chicago, IL', flairColor: '#F4A261',
    replies: [],
  },
  {
    id: 7, category: 'support',
    title: "Feeling overwhelmed after seeing my results",
    author: 'Newly_flagged', avatarColor: '#2563EB',
    content: "Just ran my first analysis and got a 78% pattern match. I know it's not a diagnosis, but seeing those numbers made everything feel real. How do you all cope with the uncertainty?",
    upvotes: 89, comments: 31, time: '3h ago', pinned: false,
    flair: 'Emotional Support', flairColor: '#2563EB',
    replies: [],
  },
];

type SortMode = 'hot' | 'new' | 'top';

export const Community = ({ onClose }: CommunityProps) => {
  const [activeCategory, setActiveCategory] = useState('all');
  const [sortMode, setSortMode] = useState<SortMode>('hot');
  const [expandedThread, setExpandedThread] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [votes, setVotes] = useState<Record<number, number>>({});

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleVote = (threadId: number, direction: 1 | -1) => {
    setVotes(prev => ({ ...prev, [threadId]: (prev[threadId] || 0) === direction ? 0 : direction }));
  };

  const filteredThreads = threads
    .filter(t => activeCategory === 'all' || t.category === activeCategory)
    .filter(t => !searchQuery || t.title.toLowerCase().includes(searchQuery.toLowerCase()) || t.content.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      if (sortMode === 'top') return b.upvotes - a.upvotes;
      return (b.upvotes + b.comments * 2) - (a.upvotes + a.comments * 2);
    });

  return (
    <div className="fixed inset-0 z-50 bg-[#0A0D14] overflow-hidden">
      {/* Background ambient glow — matches the dashboard's floating cells vibe */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-[#7B61FF]/[0.04] blur-[120px]" />
        <div className="absolute bottom-[-15%] right-[-10%] w-[400px] h-[400px] rounded-full bg-[#8C0716]/[0.06] blur-[100px]" />
        <div className="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-[#3ECFCF]/[0.03] blur-[80px]" />
      </div>

      <div className="relative max-w-4xl mx-auto h-full flex flex-col">

        {/* ══════ HEADER ══════ */}
        <div className="flex-shrink-0 border-b border-white/[0.06]">
          {/* Title bar */}
          <div className="px-6 pt-5 pb-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Animated pulse icon */}
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7B61FF]/20 to-[#3ECFCF]/20 border border-white/[0.08] flex items-center justify-center">
                  <Users className="w-5 h-5 text-[#3ECFCF]" />
                </div>
                <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#52D0A0] border-2 border-[#0A0D14]" />
              </div>
              <div>
                <h2 className="text-lg font-display font-semibold text-white tracking-wide">
                  {'AuRA Forums'.split('').map((char, i) => (
                    <motion.span
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.5 + i * 0.03, duration: 0.3 }}
                      className={char === 'u' ? 'text-white/40' : ''}
                    >
                      {char}
                    </motion.span>
                  ))}
                </h2>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="text-[11px] text-[#8A93B2] tracking-wide"
                >
                  1,247 members · <span className="text-[#52D0A0]">89 online</span>
                </motion.p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[#8A93B2] hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Search */}
          <div className="px-6 pb-3">
            <div className="relative group">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8A93B2]/60 group-focus-within:text-[#7B61FF] transition-colors" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search threads..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-sm text-white placeholder-[#8A93B2]/40 focus:outline-none focus:border-[#7B61FF]/40 focus:bg-white/[0.05] focus:shadow-[0_0_20px_rgba(123,97,255,0.08)] transition-all"
              />
            </div>
          </div>

          {/* Category pills */}
          <div className="px-6 pb-3 flex gap-2 overflow-x-auto scrollbar-hide">
            {categories.map((cat, i) => (
              <motion.button
                key={cat.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + i * 0.05 }}
                onClick={() => setActiveCategory(cat.id)}
                className={clsx(
                  "flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[11px] font-semibold whitespace-nowrap transition-all border tracking-wide uppercase",
                  activeCategory === cat.id
                    ? "border-transparent shadow-lg"
                    : "border-white/[0.06] bg-white/[0.02] text-[#8A93B2] hover:text-white hover:bg-white/[0.05] hover:border-white/[0.1]"
                )}
                style={activeCategory === cat.id ? {
                  backgroundColor: `${cat.color}15`,
                  color: cat.color,
                  borderColor: `${cat.color}30`,
                  boxShadow: `0 0 20px ${cat.color}15`,
                } : {}}
              >
                <cat.icon className="w-3.5 h-3.5" />
                {cat.label}
              </motion.button>
            ))}
          </div>

          {/* Sort + divider */}
          <div className="px-6 pb-3 flex items-center gap-1 border-t border-white/[0.04] pt-3">
            {([
              { mode: 'hot' as SortMode, icon: Flame, label: 'Hot' },
              { mode: 'new' as SortMode, icon: Clock, label: 'New' },
              { mode: 'top' as SortMode, icon: TrendingUp, label: 'Top' },
            ]).map(s => (
              <button
                key={s.mode}
                onClick={() => setSortMode(s.mode)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all",
                  sortMode === s.mode
                    ? "bg-white/[0.08] text-white shadow-sm"
                    : "text-[#8A93B2]/60 hover:text-[#8A93B2] hover:bg-white/[0.03]"
                )}
              >
                <s.icon className="w-3 h-3" />
                {s.label}
              </button>
            ))}
            <div className="ml-auto text-[10px] text-[#8A93B2]/40 tracking-wide">
              {filteredThreads.length} threads
            </div>
          </div>
        </div>

        {/* ══════ THREAD FEED ══════ */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 scrollbar-hide">

          {/* Moderation notice */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#3ECFCF]/[0.04] border border-[#3ECFCF]/[0.08]"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-[#3ECFCF]/60 flex-shrink-0" />
            <p className="text-[10px] text-[#3ECFCF]/60 tracking-wide">Navigation space, not diagnosis. Medical advice is auto-removed.</p>
          </motion.div>

          {filteredThreads.length === 0 && (
            <div className="text-center py-20 text-[#8A93B2]/40 text-sm">No threads match your filters.</div>
          )}

          {filteredThreads.map((thread, i) => {
            const userVote = votes[thread.id] || 0;
            const isExpanded = expandedThread === thread.id;
            const catDef = categories.find(c => c.id === thread.category);

            return (
              <motion.div
                key={thread.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 + i * 0.06, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                <div
                  className={clsx(
                    "rounded-2xl border transition-all duration-300 overflow-hidden backdrop-blur-sm",
                    isExpanded
                      ? "bg-white/[0.04] border-[#7B61FF]/20 shadow-[0_0_30px_rgba(123,97,255,0.06)]"
                      : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1] hover:shadow-[0_4px_20px_rgba(0,0,0,0.3)]"
                  )}
                >
                  <div className="flex">
                    {/* Vote column */}
                    <div className="flex flex-col items-center gap-0 px-3 py-4 border-r border-white/[0.04]">
                      <button
                        onClick={() => handleVote(thread.id, 1)}
                        className={clsx(
                          "p-1 rounded-lg transition-all",
                          userVote === 1
                            ? "text-[#7B61FF] bg-[#7B61FF]/10"
                            : "text-[#8A93B2]/30 hover:text-[#7B61FF] hover:bg-[#7B61FF]/5"
                        )}
                      >
                        <ArrowBigUp className={clsx("w-5 h-5", userVote === 1 && "fill-current")} />
                      </button>
                      <span className={clsx(
                        "text-xs font-bold font-mono tabular-nums my-0.5",
                        userVote === 1 ? "text-[#7B61FF]" : userVote === -1 ? "text-[#E07070]" : "text-[#F0F2F8]/70"
                      )}>
                        {thread.upvotes + userVote}
                      </span>
                      <button
                        onClick={() => handleVote(thread.id, -1)}
                        className={clsx(
                          "p-1 rounded-lg transition-all",
                          userVote === -1
                            ? "text-[#E07070] bg-[#E07070]/10"
                            : "text-[#8A93B2]/30 hover:text-[#E07070] hover:bg-[#E07070]/5"
                        )}
                      >
                        <ArrowBigDown className={clsx("w-5 h-5", userVote === -1 && "fill-current")} />
                      </button>
                    </div>

                    {/* Content */}
                    <div
                      className="flex-1 p-4 cursor-pointer"
                      onClick={() => setExpandedThread(isExpanded ? null : thread.id)}
                    >
                      {/* Meta */}
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        {thread.pinned && (
                          <span className="text-[9px] px-2 py-0.5 rounded-md bg-[#F4A261]/10 text-[#F4A261] font-bold uppercase tracking-[0.1em] border border-[#F4A261]/20">Pinned</span>
                        )}
                        <span
                          className="text-[9px] px-2 py-0.5 rounded-md border font-semibold tracking-wide"
                          style={{ color: thread.flairColor, borderColor: `${thread.flairColor}25`, backgroundColor: `${thread.flairColor}08` }}
                        >
                          {thread.flair}
                        </span>
                        <span className="text-[10px] text-[#8A93B2]/50">
                          by <span className="text-[#F0F2F8]/50">{thread.author}</span> · {thread.time}
                        </span>
                      </div>

                      {/* Title */}
                      <h3 className={clsx(
                        "text-[13px] font-semibold mb-2 leading-snug transition-colors",
                        isExpanded ? "text-white" : "text-[#F0F2F8]/90"
                      )}>
                        {thread.title}
                      </h3>

                      {/* Preview */}
                      <p className={clsx(
                        "text-[12px] text-[#8A93B2]/70 leading-relaxed",
                        !isExpanded && "line-clamp-2"
                      )}>
                        {thread.content}
                      </p>

                      {/* Actions */}
                      <div className="flex items-center gap-5 mt-3">
                        {[
                          { icon: MessageSquare, label: `${thread.comments}`, hoverColor: 'hover:text-[#3ECFCF]' },
                          { icon: Share2, label: 'Share', hoverColor: 'hover:text-[#7B61FF]' },
                          { icon: Bookmark, label: 'Save', hoverColor: 'hover:text-[#F4A261]' },
                        ].map((action, ai) => (
                          <button
                            key={ai}
                            className={clsx("flex items-center gap-1.5 text-[10px] text-[#8A93B2]/40 transition-colors", action.hoverColor)}
                          >
                            <action.icon className="w-3.5 h-3.5" />
                            {action.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Expanded replies */}
                  <AnimatePresence>
                    {isExpanded && thread.replies.length > 0 && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="border-t border-white/[0.04] px-5 py-4 space-y-4 ml-[52px]">
                          {thread.replies.map((reply, ri) => (
                            <motion.div
                              key={ri}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: ri * 0.1, duration: 0.3 }}
                              className="flex gap-3"
                            >
                              <div className="flex flex-col items-center pt-0.5">
                                <div
                                  className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 border border-white/[0.06]"
                                  style={{ background: `linear-gradient(135deg, ${reply.avatarColor}15, ${reply.avatarColor}30)` }}
                                >
                                  <span className="text-[9px] font-bold" style={{ color: reply.avatarColor }}>{reply.author[0]}</span>
                                </div>
                                <div className="w-px flex-1 bg-white/[0.04] mt-1.5" />
                              </div>
                              <div className="flex-1 pb-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-[11px] font-semibold text-[#F0F2F8]/80">{reply.author}</span>
                                  <span className="text-[9px] text-[#8A93B2]/40">{reply.time}</span>
                                </div>
                                <p className="text-[11px] text-[#8A93B2]/70 leading-relaxed">{reply.content}</p>
                                <div className="flex items-center gap-3 mt-2">
                                  <button className="flex items-center gap-1 text-[9px] text-[#8A93B2]/30 hover:text-[#7B61FF] transition-colors">
                                    <ArrowBigUp className="w-3.5 h-3.5" /> {reply.upvotes}
                                  </button>
                                  <button className="text-[9px] text-[#8A93B2]/30 hover:text-[#3ECFCF] transition-colors">Reply</button>
                                </div>
                              </div>
                            </motion.div>
                          ))}

                          {/* Reply box */}
                          <div className="flex items-start gap-3 pt-3 border-t border-white/[0.04]">
                            <div className="w-7 h-7 rounded-lg bg-[#7B61FF]/10 border border-[#7B61FF]/20 flex items-center justify-center flex-shrink-0">
                              <span className="text-[9px] font-bold text-[#7B61FF]">Y</span>
                            </div>
                            <input
                              placeholder="Add a comment..."
                              className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-3.5 py-2 text-[11px] text-white placeholder-[#8A93B2]/30 focus:outline-none focus:border-[#7B61FF]/30 focus:shadow-[0_0_16px_rgba(123,97,255,0.06)] transition-all"
                            />
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            );
          })}

          {/* Bottom spacer for FAB */}
          <div className="h-20" />
        </div>

        {/* ══════ FAB ══════ */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.2, type: 'spring', stiffness: 200, damping: 20 }}
          className="absolute bottom-6 right-6 z-50"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-0 overflow-hidden h-11 rounded-2xl bg-gradient-to-r from-[#7B61FF] to-[#7B61FF]/80 text-white shadow-[0_0_30px_rgba(123,97,255,0.25)] hover:shadow-[0_0_40px_rgba(123,97,255,0.4)] transition-shadow group pr-4 pl-4 border border-[#7B61FF]/30"
          >
            <Plus className="w-4 h-4 flex-shrink-0" />
            <span className="max-w-0 group-hover:max-w-xs transition-all duration-300 overflow-hidden whitespace-nowrap opacity-0 group-hover:opacity-100 group-hover:ml-2 text-[12px] font-semibold tracking-wide">
              New Thread
            </span>
          </motion.button>
        </motion.div>

      </div>
    </div>
  );
};
