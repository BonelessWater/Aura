import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowUp, ArrowDown, MessageSquare, Share2, Bookmark,
  ShieldAlert, X, ArrowRight, Plus, Flame, Clock,
  TrendingUp, Zap, AlertTriangle, Award, Eye, EyeOff,
  Search, MoreHorizontal,
  AlignLeft, ImageIcon, Link2,
} from 'lucide-react';
import { useNavigate } from 'react-router';
import { clsx } from 'clsx';

/* ─────────────────── Types ─────────────────── */
interface CommunityProps { onClose: () => void; }

interface Post {
  id: number;
  author: string;
  avatarColor: string;
  anonymous: boolean;
  flair: string;
  flairColor: string;
  sub: string;
  subIcon: string;
  subColor: string;
  title: string;
  body: string;
  votes: number;
  comments: number;
  time: string;
  pinned?: boolean;
  cw?: string;
}

/* ─────────────────── Mock data ─────────────────── */
const MATCHED_SUB = {
  name: 'AutoimmuneAllies',
  displayName: 'Autoimmune Allies',
  color: '#7B61FF',
  glow: 'rgba(123,97,255,0.22)',
  bannerGradient: 'linear-gradient(135deg, #1a1040 0%, #2d1b6e 40%, #0f0b2a 100%)',
  icon: '🛡️',
  members: 14_820,
  online: 412,
  description: 'Why you were matched: Sustained ANA elevation, malar rash pattern, and inflammatory lab trend overlap with this community\'s most common symptom clusters.',
};

const POSTS: Post[] = [
  {
    id: 1, author: 'Butterfly_w', avatarColor: '#7B61FF', anonymous: false,
    flair: 'Win 🎉', flairColor: '#6BCB77',
    sub: 'AutoimmuneAllies', subIcon: '🛡️', subColor: '#7B61FF',
    title: 'Finally got my GP to order an ANA panel after showing them the SOAP note. The malar rash photo was what convinced them.',
    body: "Don't give up on getting the right tests. The Aura report was the difference — having the trend chart made it impossible to dismiss.",
    votes: 47, comments: 14, time: '2h ago', pinned: true,
  },
  {
    id: 2, author: 'CRP_tracker', avatarColor: '#3ECFCF', anonymous: false,
    flair: 'Research', flairColor: '#3ECFCF',
    sub: 'LabDecoded', subIcon: '🔬', subColor: '#3ECFCF',
    title: 'New Rheumatology paper links sustained NLR elevation with earlier Lupus onset — exactly the trend Aura flagged for me.',
    body: 'Sharing the DOI in comments. If your NLR has been trending up over 3+ months, this is worth bringing to your rheum.',
    votes: 156, comments: 42, time: '5h ago',
  },
  {
    id: 3, author: 'joint_journal', avatarColor: '#F4A261', anonymous: false,
    flair: 'Success Story', flairColor: '#F4A261',
    sub: 'ReferralRoulette', subIcon: '🎲', subColor: '#F4A261',
    title: 'Got my Rheumatology appointment. Specialist said the clinical summary was the clearest patient-initiated referral she\'d seen.',
    body: 'Keep documenting your patterns. The more specific your language, the harder it is to dismiss.',
    votes: 89, comments: 12, time: '1d ago',
  },
  {
    id: 4, author: 'anon_patient', avatarColor: '#B784F7', anonymous: true,
    flair: 'Venting', flairColor: '#E07070',
    sub: 'AnxiousAndFighting', subIcon: '💜', subColor: '#B784F7',
    title: '[CW: Dismissal] Third GP in a row said it\'s anxiety. My NLR has been elevated for 8 months.',
    body: 'I have every report printed. I have the trend graph. They still look at me like I\'m making it up.',
    votes: 312, comments: 67, time: '3h ago', cw: 'Medical dismissal',
  },
];

const subs = [
  { id: 'all', name: 'All Communities', displayName: 'All Communities', color: '#7B61FF', members: 57_000 },
  { id: 'autoimmune', name: 'AutoimmuneAllies', displayName: 'Autoimmune Allies', color: '#7B61FF', members: 14_820 },
  { id: 'labs', name: 'LabDecoded', displayName: 'Lab Decoded', color: '#3ECFCF', members: 21_100 },
  { id: 'referrals', name: 'ReferralRoulette', displayName: 'Referral Roulette', color: '#F4A261', members: 9_340 },
  { id: 'flares', name: 'FlareDiary', displayName: 'Flare Diary', color: '#E07070', members: 7_560 },
  { id: 'wins', name: 'SymptomWins', displayName: 'Symptom Wins', color: '#6BCB77', members: 5_200 },
  { id: 'anxiety', name: 'AnxiousAndFighting', displayName: 'Anxious & Fighting', color: '#B784F7', members: 12_400 },
];

/* ─────────────────── Helpers ─────────────────── */
function fmtNum(n: number) { return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n); }

function AvatarBlob({ color, size = 32, letter }: { color: string; size?: number; letter?: string }) {
  return (
    <div className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, background: `linear-gradient(135deg, ${color}40, ${color}70)`, boxShadow: `0 0 8px ${color}40` }}>
      {letter
        ? <span style={{ fontSize: size * 0.42, color: 'white', fontWeight: 700, lineHeight: 1 }}>{letter.toUpperCase()}</span>
        : <svg width={size} height={size} viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="8" fill={color} opacity="0.7" />
            <circle cx="28" cy="12" r="4" fill={color} opacity="0.4" />
            <circle cx="10" cy="28" r="6" fill={color} opacity="0.3" />
          </svg>
      }
    </div>
  );
}

/* ─────────────────── Vote Rail ─────────────────── */
function VoteRail({ votes: init }: { votes: number }) {
  const [votes, setVotes] = useState(init);
  const [voted, setVoted] = useState<'up' | 'down' | null>(null);
  function vote(d: 'up' | 'down') {
    if (voted === d) { setVotes(init); setVoted(null); }
    else { setVotes(init + (d === 'up' ? 1 : -1)); setVoted(d); }
  }
  return (
    <div className="flex flex-col items-center gap-0.5 py-1.5">
      <motion.button whileTap={{ scale: 0.75 }} onClick={e => { e.stopPropagation(); vote('up'); }}
        className={clsx('p-1 rounded transition-colors', voted === 'up' ? 'text-[#FF6B35]' : 'text-[#555870] hover:text-[#FF6B35] hover:bg-[#FF6B35]/10')}>
        <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
      </motion.button>
      <span className="text-[11px] font-bold tabular-nums leading-none"
        style={{ color: voted === 'up' ? '#FF6B35' : voted === 'down' ? '#7B61FF' : '#6B7280' }}>
        {fmtNum(votes)}
      </span>
      <motion.button whileTap={{ scale: 0.75 }} onClick={e => { e.stopPropagation(); vote('down'); }}
        className={clsx('p-1 rounded transition-colors', voted === 'down' ? 'text-[#7B61FF]' : 'text-[#555870] hover:text-[#7B61FF] hover:bg-[#7B61FF]/10')}>
        <ArrowDown className="w-4 h-4" strokeWidth={2.5} />
      </motion.button>
    </div>
  );
}

/* ─────────────────── Post Card ─────────────────── */
function PostCard({ post, onExpand }: { post: Post; onExpand: () => void }) {
  const [saved, setSaved] = useState(false);
  const [cwOpen, setCwOpen] = useState(!post.cw);

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className={clsx('flex rounded-md border overflow-hidden cursor-pointer group transition-all duration-150',
        post.pinned ? 'border-[#7B61FF]/35' : 'border-[#1C1F2E] hover:border-[#7B61FF]/25')}
      style={{ background: 'rgba(15,18,24,0.9)', backdropFilter: 'blur(4px)', boxShadow: '0 1px 8px rgba(0,0,0,0.3)' }}
      onClick={onExpand}>

      {/* Vote strip */}
      <div className="w-10 flex-shrink-0 flex flex-col items-center pt-1 rounded-l-md"
        style={{ background: 'rgba(255,255,255,0.015)' }} onClick={e => e.stopPropagation()}>
        <VoteRail votes={post.votes} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 px-3 py-2.5">
        {post.pinned && (
          <div className="flex items-center gap-1 text-[10px] text-[#7B61FF]/60 font-semibold mb-1">
            <Award className="w-3 h-3" /> Pinned
          </div>
        )}

        {/* Meta */}
        <div className="flex flex-wrap items-center gap-1 text-[11px] text-[#555870] mb-1">
          <span className="font-semibold" style={{ color: post.subColor }}>r/{post.sub}</span>
          <span className="text-[#2E3248]">·</span>
          <span className="flex items-center gap-1">
            <AvatarBlob color={post.avatarColor} size={14} letter={post.author[0]} />
            {post.anonymous ? 'u/Anonymous' : `u/${post.author}`}
          </span>
          <span className="text-[#2E3248]">·</span>
          <span>{post.time}</span>
          {post.flair && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
              style={{ background: `${post.flairColor}15`, color: post.flairColor, border: `1px solid ${post.flairColor}28` }}>
              {post.flair}
            </span>
          )}
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold text-[#DDE1F0] group-hover:text-white leading-snug mb-1.5 transition-colors">
          {post.title}
        </h3>

        {/* CW / body */}
        {post.cw && !cwOpen ? (
          <button onClick={e => { e.stopPropagation(); setCwOpen(true); }}
            className="flex items-center gap-1.5 text-[11px] text-[#F4A261] px-2.5 py-1.5 rounded mb-1.5"
            style={{ background: 'rgba(244,162,97,0.06)', border: '1px solid rgba(244,162,97,0.18)' }}>
            <AlertTriangle className="w-3 h-3 flex-shrink-0" /> CW: {post.cw} — tap to reveal
          </button>
        ) : (
          <p className="text-xs text-[#6B7280] leading-relaxed line-clamp-2 mb-2">{post.body}</p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-0 -ml-1.5" onClick={e => e.stopPropagation()}>
          <button onClick={onExpand}
            className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
            <MessageSquare className="w-3.5 h-3.5" /> {post.comments} Comments
          </button>
          <button className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
            <Share2 className="w-3.5 h-3.5" /> Share
          </button>
          <button onClick={() => setSaved(!saved)}
            className={clsx('flex items-center gap-1.5 text-[11px] font-semibold hover:bg-white/5 px-2 py-1 rounded transition-colors',
              saved ? 'text-[#F4A261]' : 'text-[#555870] hover:text-[#8A93B2]')}>
            <Bookmark className={clsx('w-3.5 h-3.5', saved && 'fill-current')} />
            {saved ? 'Saved' : 'Save'}
          </button>
          <button className="ml-auto p-1.5 text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 rounded transition-colors">
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

/* ─────────────────── Compose Modal ─────────────────── */
function ComposeModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'post' | 'image' | 'link'>('post');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [cw, setCw] = useState('');

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      style={{ background: 'rgba(8,11,18,0.92)', backdropFilter: 'blur(10px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>

      <motion.div initial={{ y: 20, opacity: 0, scale: 0.97 }} animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 20, opacity: 0 }} transition={{ type: 'spring', damping: 28 }}
        className="w-full max-w-lg">

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-black text-[#F0F2F8]">Create a Post</h2>
          <button onClick={onClose} className="p-1.5 rounded-full hover:bg-white/8 text-[#6B7280] hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Community chip */}
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
            style={{ background: 'rgba(123,97,255,0.12)', border: '1px solid rgba(123,97,255,0.3)', color: '#7B61FF' }}>
            🛡️ r/AutoimmuneAllies
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex rounded-t-md overflow-hidden" style={{ border: '1px solid #1C1F2E', borderBottom: 'none', background: 'rgba(15,18,24,0.9)' }}>
          {[{ id: 'post', label: 'Post', icon: AlignLeft }, { id: 'image', label: 'Image', icon: ImageIcon }, { id: 'link', label: 'Link', icon: Link2 }].map(t => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id as any)}
                className={clsx('flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-bold border-b-2 transition-all',
                  tab === t.id ? 'border-[#7B61FF] text-[#F0F2F8]' : 'border-transparent text-[#555870] hover:text-[#8A93B2]')}
                style={tab === t.id ? { background: 'rgba(123,97,255,0.06)' } : {}}>
                <Icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            );
          })}
        </div>

        <div className="p-4 space-y-3 rounded-b-md" style={{ background: 'rgba(15,18,24,0.9)', border: '1px solid #1C1F2E' }}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" maxLength={300}
            className="w-full rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none focus:border-[#7B61FF]/50 transition-colors"
            style={{ background: '#0A0D14', border: '1px solid #1E2130' }} />

          {tab === 'post' && (
            <textarea value={body} onChange={e => setBody(e.target.value)} placeholder="What are you going through?" rows={5}
              className="w-full rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] resize-none focus:outline-none focus:border-[#7B61FF]/50 transition-colors"
              style={{ background: '#0A0D14', border: '1px solid #1E2130' }} />
          )}
          {tab === 'link' && (
            <input placeholder="URL"
              className="w-full rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none focus:border-[#7B61FF]/50 transition-colors"
              style={{ background: '#0A0D14', border: '1px solid #1E2130' }} />
          )}
          {tab === 'image' && (
            <div className="rounded-lg p-8 text-center text-[#4A5070] cursor-pointer transition-colors"
              style={{ border: '2px dashed #1E2130' }}>
              <ImageIcon className="w-7 h-7 mx-auto mb-2 opacity-30" />
              <p className="text-xs">Drop image or click to upload</p>
            </div>
          )}

          <input value={cw} onChange={e => setCw(e.target.value)}
            placeholder="Content warning (optional)"
            className="w-full rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none transition-colors"
            style={{ background: '#0A0D14', border: '1px solid #1E2130' }} />

          <div className="flex items-center justify-between pt-1 border-t border-[#1E2130]">
            <button onClick={() => setAnonymous(!anonymous)}
              className={clsx('flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-all',
                anonymous ? 'text-[#7B61FF] border-[#7B61FF]/40' : 'text-[#4A5070] border-[#2A2E3B] hover:border-[#3A3E50]')}
              style={anonymous ? { background: 'rgba(123,97,255,0.1)' } : {}}>
              {anonymous ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {anonymous ? 'Anonymous' : 'Post as you'}
            </button>
            <div className="flex gap-2">
              <button onClick={onClose} className="text-xs border border-[#2A2E3B] text-[#8A93B2] px-3 py-1.5 rounded-full hover:border-[#3A3E50] transition-colors">
                Cancel
              </button>
              <button disabled={!title.trim()} onClick={onClose}
                className="text-xs font-black bg-[#7B61FF] hover:bg-[#6B51EF] disabled:opacity-30 disabled:cursor-not-allowed text-white px-4 py-1.5 rounded-full transition-colors"
                style={{ boxShadow: '0 0 12px rgba(123,97,255,0.3)' }}>
                Post
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ─────────────────── Main component ─────────────────── */
type SortMode = 'hot' | 'new' | 'top' | 'rising';

export const Community = ({ onClose }: CommunityProps) => {
  const navigate = useNavigate();
  const [sort, setSort] = useState<SortMode>('hot');
  const [activeSub, setActiveSub] = useState<string>('all');
  const [showCompose, setShowCompose] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' && !showCompose) onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose, showCompose]);

  const SORT_OPTS: { id: SortMode; label: string; icon: React.ElementType }[] = [
    { id: 'hot', label: 'Hot', icon: Flame },
    { id: 'new', label: 'New', icon: Clock },
    { id: 'top', label: 'Top', icon: TrendingUp },
    { id: 'rising', label: 'Rising', icon: Zap },
  ];

  const displayed = POSTS
    .filter(p => search ? (p.title + p.body + p.author).toLowerCase().includes(search.toLowerCase()) : true)
    .sort((a, b) => a.pinned ? -1 : sort === 'new' ? b.id - a.id : b.votes - a.votes);

  const currentSub = subs.find(s => s.id === activeSub) ?? subs[0];

  return (
    <>
      <div
        className="fixed inset-0 z-50 overflow-hidden flex flex-col"
        style={{ background: 'rgba(8,11,18,0.96)', backdropFilter: 'blur(2px)' }}
      >
        {/* ── Top bar ── */}
        <div className="flex-shrink-0 flex items-center gap-2 px-4 h-11 border-b"
          style={{ background: 'rgba(13,16,24,0.98)', backdropFilter: 'blur(16px)', borderColor: '#1A1D26' }}>
          {/* Search */}
          <div className="flex-1 max-w-sm relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#3A3E50]" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search communities…"
              className="w-full rounded-full pl-9 pr-4 py-1.5 text-xs placeholder-[#3A3E50] focus:outline-none transition-colors"
              style={{ background: 'rgba(26,29,38,0.9)', border: '1px solid #2A2E3B', color: '#F0F2F8' }} />
          </div>
          <button onClick={onClose}
            className="ml-auto p-1.5 rounded-full text-[#555870] hover:text-white hover:bg-white/8 transition-colors flex-shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Safety strip ── */}
        <div className="flex-shrink-0" style={{ background: 'rgba(62,207,207,0.03)', borderBottom: '1px solid rgba(62,207,207,0.08)' }}>
          <div className="max-w-4xl mx-auto px-4 py-1 flex items-center gap-2 text-[10px]" style={{ color: 'rgba(62,207,207,0.5)' }}>
            <ShieldAlert className="w-3 h-3 flex-shrink-0" />
            Peer support only · No medical advice · Crisis: <strong className="ml-0.5" style={{ color: 'rgba(62,207,207,0.75)' }}>988</strong> · text HOME to 741741
          </div>
        </div>

        {/* ── Body: 2 columns ─── */}
        <div className="flex-1 overflow-hidden flex max-w-4xl mx-auto w-full">

          {/* Left: sub nav */}
          <aside className="w-52 flex-shrink-0 border-r overflow-y-auto py-3 hidden md:block"
            style={{ borderColor: '#1A1D26', background: 'rgba(10,13,20,0.5)' }}>
            <p className="text-[10px] font-black uppercase tracking-widest px-3 py-1 mb-1" style={{ color: '#4A5070' }}>Communities</p>
            {subs.map(s => (
              <button key={s.id} onClick={() => setActiveSub(s.id)}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs transition-all"
                style={activeSub === s.id ? { background: `${s.color}12`, color: s.color, fontWeight: 700 } : { color: '#8A93B2' }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: activeSub === s.id ? s.color : '#2A2E3B' }} />
                <div className="flex-1 min-w-0 text-left">
                  <div className="truncate font-semibold text-xs">{s.displayName}</div>
                  <div className="text-[9px]" style={{ color: '#4A5070' }}>{fmtNum(s.members)} members</div>
                </div>
              </button>
            ))}

            <div className="px-3 mt-4 pt-3 border-t" style={{ borderColor: '#1A1D26' }}>
              <p className="text-[10px] font-black uppercase tracking-widest mb-2" style={{ color: '#4A5070' }}>Your Match</p>
              {/* Matched sub mini card */}
              <div className="rounded-md overflow-hidden" style={{ background: 'rgba(123,97,255,0.06)', border: '1px solid rgba(123,97,255,0.18)' }}>
                <div className="h-6" style={{ background: MATCHED_SUB.bannerGradient }} />
                <div className="px-2 pb-2 pt-1">
                  <div className="flex items-center gap-1.5 -mt-3 mb-1">
                    <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ background: 'rgba(123,97,255,0.2)', border: '2px solid rgba(10,13,20,0.95)' }}>
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#7B61FF' }} />
                    </div>
                    <span className="text-[10px] font-black mt-1" style={{ color: '#7B61FF' }}>r/{MATCHED_SUB.name}</span>
                  </div>
                  <p className="text-[9px] leading-relaxed" style={{ color: '#6B7280' }}>{MATCHED_SUB.description}</p>
                  <div className="flex items-center gap-1 mt-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#6BCB77]" style={{ boxShadow: '0 0 4px #6BCB77' }} />
                    <span className="text-[9px]" style={{ color: '#6BCB77' }}>{MATCHED_SUB.online} online</span>
                  </div>
                </div>
              </div>
              <button onClick={() => { onClose(); navigate('/forum'); }}
                className="w-full text-[10px] font-black mt-2 py-1.5 rounded-full text-white flex items-center justify-center gap-1 transition-all"
                style={{ background: '#7B61FF', boxShadow: '0 0 10px rgba(123,97,255,0.25)' }}>
                Open Full Forum <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </aside>

          {/* Center: feed */}
          <main className="flex-1 min-w-0 overflow-y-auto">
            {/* Sub banner */}
            <div className="flex-shrink-0">
              <div className="h-14 relative overflow-hidden" style={{ background: currentSub.id === 'all' ? 'linear-gradient(135deg, #1a1040 0%, #2d1b6e 40%, #0f0b2a 100%)' : MATCHED_SUB.bannerGradient }}>
                <div className="absolute inset-0" style={{ background: `radial-gradient(ellipse at 25% 60%, ${currentSub.color}30 0%, transparent 65%)` }} />
              </div>
              <div className="px-4 py-2 flex items-center gap-3 border-b" style={{ background: 'rgba(13,16,24,0.95)', borderColor: '#1A1D26' }}>
                <div className="w-10 h-10 rounded-full flex items-center justify-center -mt-5 flex-shrink-0"
                  style={{ background: `${currentSub.color}20`, border: `3px solid rgba(13,16,24,0.95)`, boxShadow: `0 0 16px ${currentSub.color}30` }}>
                  <span className="w-3 h-3 rounded-full" style={{ background: currentSub.color }} />
                </div>
                <div>
                  <h2 className="text-sm font-black" style={{ color: currentSub.color }}>{currentSub.displayName}</h2>
                  <p className="text-[10px] text-[#4A5070]">{fmtNum(currentSub.members)} members</p>
                </div>

              </div>
            </div>

            <div className="px-4 py-3 space-y-2.5">
              {/* Create post box */}
              <div className="flex items-center gap-2 rounded-md p-2"
                style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
                <AvatarBlob color="#7B61FF" size={32} letter="Y" />
                <button onClick={() => setShowCompose(true)}
                  className="flex-1 text-left rounded px-3 py-2 text-sm text-[#3A3E50] hover:text-[#6B7280] transition-colors"
                  style={{ background: 'rgba(10,13,20,0.8)', border: '1px solid #1E2130' }}>
                  Create Post
                </button>
                <button onClick={() => setShowCompose(true)} className="p-2 text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 rounded transition-colors">
                  <ImageIcon className="w-4 h-4" />
                </button>
              </div>

              {/* Sort bar */}
              <div className="flex items-center gap-0.5 rounded-md px-1.5 py-1"
                style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
                {SORT_OPTS.map(opt => {
                  const Icon = opt.icon;
                  return (
                    <button key={opt.id} onClick={() => setSort(opt.id)}
                      className={clsx('flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded transition-all',
                        sort === opt.id ? 'text-[#7B61FF]' : 'text-[#555870] hover:text-[#8A93B2] hover:bg-white/5')}
                      style={sort === opt.id ? { background: 'rgba(123,97,255,0.12)' } : {}}>
                      <Icon className="w-3.5 h-3.5" /> {opt.label}
                    </button>
                  );
                })}
              </div>

              {/* Posts */}
              <div className="space-y-2">
                {displayed.map((post, i) => (
                  <motion.div key={post.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <PostCard post={post} onExpand={() => { onClose(); navigate('/forum'); }} />
                  </motion.div>
                ))}
              </div>

              {/* CTA */}
              <motion.button
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
                onClick={() => { onClose(); navigate('/forum'); }}
                className="w-full flex items-center justify-between p-4 rounded-xl transition-all group mt-2"
                style={{ background: 'rgba(123,97,255,0.06)', border: '1px solid rgba(123,97,255,0.2)' }}
                whileHover={{ borderColor: 'rgba(123,97,255,0.4)', backgroundColor: 'rgba(123,97,255,0.1)' }}>
                <div className="text-left">
                  <p className="text-sm font-black" style={{ color: '#7B61FF' }}>Open Full Community Forum</p>
                  <p className="text-xs mt-0.5" style={{ color: '#6B7280' }}>6 sub-communities · Vote, comment, and post anonymously</p>
                </div>
                <ArrowRight className="w-5 h-5 flex-shrink-0 transition-transform group-hover:translate-x-1" style={{ color: '#7B61FF' }} />
              </motion.button>

              <div className="text-center py-4">
                <p className="text-[10px]" style={{ color: '#4A5070' }}>Showing matched posts • <button onClick={() => { onClose(); navigate('/forum'); }} className="underline hover:text-[#7B61FF] transition-colors">See all in full forum</button></p>
              </div>
            </div>
          </main>
        </div>

        {/* Mobile FAB */}
        <div className="fixed bottom-6 right-6 z-50 md:hidden">
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => setShowCompose(true)}
            className="w-12 h-12 rounded-full flex items-center justify-center text-white"
            style={{ background: '#7B61FF', boxShadow: '0 0 28px rgba(123,97,255,0.55)' }}>
            <Plus className="w-5 h-5" />
          </motion.button>
        </div>
      </div>

      {/* Compose overlay */}
      <AnimatePresence>
        {showCompose && <ComposeModal onClose={() => setShowCompose(false)} />}
      </AnimatePresence>
    </>
  );
};
