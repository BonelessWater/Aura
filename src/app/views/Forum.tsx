import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowUp, ArrowDown, MessageSquare, Share2, Bookmark,
  ShieldAlert, Plus, X, Search, Bell,
  Flame, Clock, TrendingUp, Zap, Lock, Flag,
  AlertTriangle, CheckCircle2, Users, Award, ChevronLeft,
  Send, Hash, MoreHorizontal, Eye, EyeOff, ImageIcon,
  Link2, AlignLeft, ChevronDown,
} from 'lucide-react';
import { useNavigate } from 'react-router';
import { clsx } from 'clsx';

/* ─────────────────── Types ─────────────────── */
interface Sub {
  id: string;
  name: string;
  displayName: string;
  color: string;
  glow: string;
  bannerGradient: string;
  icon: string;
  members: number;
  online: number;
  description: string;
  rules: string[];
  tags: string[];
}

interface Post {
  id: number;
  subId: string;
  author: string;
  avatarColor: string;
  anonymous: boolean;
  flair: string;
  flairColor: string;
  title: string;
  body: string;
  votes: number;
  comments: Comment[];
  time: string;
  pinned?: boolean;
  cw?: string;
}

interface Comment {
  id: number;
  author: string;
  avatarColor: string;
  body: string;
  votes: number;
  time: string;
  replies?: Comment[];
}

/* ─────────────────── Sub-communities ─────────────────── */
const SUBS: Sub[] = [
  {
    id: 'autoimmune',
    name: 'AutoimmuneAllies',
    displayName: 'Autoimmune Allies',
    color: '#7B61FF',
    glow: 'rgba(123,97,255,0.2)',
    bannerGradient: 'linear-gradient(135deg, #1a1040 0%, #2d1b6e 40%, #0f0b2a 100%)',
    icon: '🛡️',
    members: 14_820,
    online: 412,
    description: 'A space for people navigating autoimmune diagnoses — sharing labs, SOAP notes, and the hell of getting a referral.',
    rules: [
      'No medical advice. Share experiences, not prescriptions.',
      'Be kind. We\'re all exhausted here.',
      'Flare triggers are real — use content warnings.',
      'No diet cure posts. Period.',
    ],
    tags: ['Lupus', 'RA', 'Sjögren\'s', 'MCTD', 'Diagnosis Journey'],
  },
  {
    id: 'referrals',
    name: 'ReferralRoulette',
    displayName: 'Referral Roulette',
    color: '#F4A261',
    glow: 'rgba(244,162,97,0.2)',
    bannerGradient: 'linear-gradient(135deg, #2a1800 0%, #5c3010 40%, #1a0e00 100%)',
    icon: '🎲',
    members: 9_340,
    online: 218,
    description: 'The nightmare of getting the right specialist. Scripts, templates, and solidarity.',
    rules: [
      'Share referral templates freely.',
      'No naming/shaming specific doctors.',
      'Insurance talk welcome — vent away.',
    ],
    tags: ['Template', 'Insurance', 'Denied', 'Win', 'NHS', 'Medicare'],
  },
  {
    id: 'labs',
    name: 'LabDecoded',
    displayName: 'Lab Decoded',
    color: '#3ECFCF',
    glow: 'rgba(62,207,207,0.2)',
    bannerGradient: 'linear-gradient(135deg, #001a1a 0%, #0b4040 40%, #001212 100%)',
    icon: '🔬',
    members: 21_100,
    online: 634,
    description: 'Post your results, understand the numbers. Not a substitute for your doctor — a supplement.',
    rules: [
      'No interpretation = diagnosis. Just pattern sharing.',
      'Cite sources when referencing ranges.',
      'Mark old results with dates.',
    ],
    tags: ['ANA', 'CRP', 'ESR', 'NLR', 'CBC', 'Thyroid'],
  },
  {
    id: 'flares',
    name: 'FlareDiary',
    displayName: 'Flare Diary',
    color: '#E07070',
    glow: 'rgba(224,112,112,0.2)',
    bannerGradient: 'linear-gradient(135deg, #2a0808 0%, #5c1a1a 40%, #1a0404 100%)',
    icon: '🔥',
    members: 7_560,
    online: 189,
    description: 'Track, vent, and validate. Flare cycles are real and so is your exhaustion.',
    rules: [
      'Use CW: [intense symptoms] tags if needed.',
      'No toxic positivity. "Have you tried yoga?" is banned.',
      'Validate first. Advice only if asked.',
    ],
    tags: ['Venting', 'Fatigue', 'Pain', 'Brain Fog', 'Joint Pain'],
  },
  {
    id: 'wins',
    name: 'SymptomWins',
    displayName: 'Symptom Wins',
    color: '#6BCB77',
    glow: 'rgba(107,203,119,0.2)',
    bannerGradient: 'linear-gradient(135deg, #041a06 0%, #0f4015 40%, #020e03 100%)',
    icon: '✨',
    members: 5_200,
    online: 144,
    description: 'Celebrate every win, no matter how small. Got a referral? Got believed? Post it.',
    rules: [
      'All wins count. "I made it outside today" is valid.',
      'Be supportive. Always.',
    ],
    tags: ['Diagnosed', 'Referred', 'Believed', 'Remission'],
  },
  {
    id: 'anxiety',
    name: 'AnxiousAndFighting',
    displayName: 'Anxious & Fighting',
    color: '#B784F7',
    glow: 'rgba(183,132,247,0.2)',
    bannerGradient: 'linear-gradient(135deg, #1a0a2a 0%, #3d1a6e 40%, #0f0618 100%)',
    icon: '💜',
    members: 12_400,
    online: 380,
    description: 'The mental load of chronic illness. Medical anxiety, decision fatigue, appointment dread — all valid here.',
    rules: [
      'This is not a crisis resource. For emergencies call 988.',
      'Gentle space only — no tough love.',
      'Celebrate rest as resistance.',
    ],
    tags: ['Medical Anxiety', 'Appointment Dread', 'Decision Fatigue', 'Vent'],
  },
];

/* ─────────────────── Mock Posts ─────────────────── */
const ALL_POSTS: Post[] = [
  {
    id: 1, subId: 'autoimmune', author: 'butterfly_w', avatarColor: '#7B61FF', anonymous: false,
    flair: 'Lupus', flairColor: '#7B61FF',
    title: "ANA came back positive — GP still dismissed me. Here's what I did.",
    body: "Got a 1:320 speckled ANA, malar rash, joint pain. GP said \"stress.\" I printed my Aura SOAP note, highlighted the NLR trend, and booked a second opinion. The new GP referred me to rheum in the same visit. The note was the difference.",
    votes: 312, time: '2h ago', pinned: true,
    comments: [
      { id: 1, author: 'CRP_tracker', avatarColor: '#3ECFCF', body: 'This is exactly why having documentation matters. SOAP notes cut through the dismissal.', votes: 89, time: '1h ago',
        replies: [{ id: 11, author: 'butterfly_w', avatarColor: '#7B61FF', body: 'Exactly — the visual trend chart was what made it click for them.', votes: 34, time: '55m ago' }] },
      { id: 2, author: 'joint_journal', avatarColor: '#F4A261', body: 'Saving this. Seeing my GP next week with a 1:160 result and already dreading it.', votes: 34, time: '45m ago' },
      { id: 3, author: 'anon_patient', avatarColor: '#B784F7', body: 'Thank you for sharing. Did you go private or NHS for the second opinion?', votes: 12, time: '20m ago' },
    ],
  },
  {
    id: 2, subId: 'referrals', author: 'waiting_room_99', avatarColor: '#F4A261', anonymous: false,
    flair: 'Template', flairColor: '#F4A261',
    title: '📋 Referral script that got me seen in 3 weeks instead of 6 months [template inside]',
    body: "Lead with objective lab values, attach SOAP note, mention symptom timeline, end with a specific ask (\"I am requesting an urgent rheumatology referral given the sustained inflammatory markers\"). Specificity = urgency signal.",
    votes: 567, time: '1d ago',
    comments: [
      { id: 1, author: 'systemic_struggle', avatarColor: '#6BCB77', body: 'Used a version of this last month. Rheum seen in 2 weeks. The specific ask language is crucial.', votes: 144, time: '20h ago' },
    ],
  },
  {
    id: 3, subId: 'labs', author: 'lab_lurker', avatarColor: '#3ECFCF', anonymous: false,
    flair: 'Interpretation Help', flairColor: '#3ECFCF',
    title: 'ESR 78, CRP 42, normal CBC. Rheum says "nothing to worry about" — does this track?',
    body: "Been elevated for 6 months straight. My Aura analysis flagged persistent inflammatory load with no infectious cause. Just want to know if others have seen this pattern before a diagnosis.",
    votes: 189, time: '4h ago', cw: 'Dismissal experience',
    comments: [
      { id: 1, author: 'inflamed_and_informed', avatarColor: '#E07070', body: 'Sustained ESR/CRP elevation without infection is a significant pattern. Not saying what it is — but your instincts to push are valid.', votes: 76, time: '3h ago' },
    ],
  },
  {
    id: 4, subId: 'flares', author: 'invisibleflamex', avatarColor: '#E07070', anonymous: true,
    flair: 'Venting', flairColor: '#E07070',
    title: "[CW: Fatigue Spiral] Week 3 of a flare I can't explain and no one believes",
    body: "I've tracked everything. Logged every symptom, uploaded my wearable data, printed the Aura report. My partner says \"you don't look sick.\" My GP says \"anxiety.\" I'm so tired of being my own advocate when I'm also the patient.",
    votes: 441, time: '6h ago', cw: 'Medical dismissal, emotional exhaustion',
    comments: [
      { id: 1, author: 'chronic_and_still_here', avatarColor: '#B784F7', body: 'You are seen. Documenting everything while feeling this way is an act of strength. Please keep going.', votes: 213, time: '5h ago' },
      { id: 2, author: 'justa_patient', avatarColor: '#7B61FF', body: '"You don\'t look sick" — has anyone ever said anything more infuriating? Sending solidarity.', votes: 189, time: '4h ago' },
    ],
  },
  {
    id: 5, subId: 'wins', author: 'small_steps_big_battles', avatarColor: '#6BCB77', anonymous: false,
    flair: 'Win 🎉', flairColor: '#6BCB77',
    title: "Got diagnosed after 4 years. I cried in the rheumatologist's office.",
    body: "Mixed connective tissue disease. Four years of \"it's probably anxiety.\" One Aura report with a clear inflammatory timeline. One prepared appointment. One doctor who actually looked. I am not making this up. I never was.",
    votes: 1_203, time: '2d ago',
    comments: [
      { id: 1, author: 'butterfly_w', avatarColor: '#7B61FF', body: 'This made me tear up. Congratulations on being believed. You deserve every bit of this.', votes: 340, time: '1d ago' },
      { id: 2, author: 'waiting_room_99', avatarColor: '#F4A261', body: 'Pinning this to my bathroom mirror. Thank you.', votes: 210, time: '22h ago' },
    ],
  },
  {
    id: 6, subId: 'anxiety', author: 'appointment_dread', avatarColor: '#B784F7', anonymous: true,
    flair: 'Venting', flairColor: '#B784F7',
    title: 'Anyone else rehearse the appointment 50 times and still blank when the doctor walks in?',
    body: "I have a full Aura report, a printed list of questions, my symptom timeline — and the moment they enter the room I forget everything and say \"I'm fine.\" Every. Single. Time.",
    votes: 734, time: '8h ago',
    comments: [
      { id: 1, author: 'advocating_for_myself', avatarColor: '#3ECFCF', body: 'I literally hand the doctor my printout and say "I\'ve written it all here so I don\'t forget anything." Takes the pressure off having to perform being sick.', votes: 412, time: '7h ago',
        replies: [{ id: 11, author: 'appointment_dread', avatarColor: '#B784F7', body: "This is genius. Removing the performance aspect. I'm doing this.", votes: 89, time: '6h ago' }] },
      { id: 2, author: 'small_steps_big_battles', avatarColor: '#6BCB77', body: 'Opening line that works: "I need to show you something before we start." Then slide the SOAP note across. Resets the whole dynamic.', votes: 289, time: '6h ago' },
    ],
  },
];

/* ─────────────────── Helpers ─────────────────── */
function fmtNum(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function AvatarBlob({ color, size = 32, letter }: { color: string; size?: number; letter?: string }) {
  return (
    <div
      className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, background: `linear-gradient(135deg, ${color}40, ${color}70)`, boxShadow: `0 0 8px ${color}40` }}
    >
      {letter ? (
        <span style={{ fontSize: size * 0.42, color: 'white', fontWeight: 700, lineHeight: 1 }}>{letter.toUpperCase()}</span>
      ) : (
        <svg width={size} height={size} viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="8" fill={color} opacity="0.7" />
          <circle cx="28" cy="12" r="4" fill={color} opacity="0.4" />
          <circle cx="10" cy="28" r="6" fill={color} opacity="0.3" />
        </svg>
      )}
    </div>
  );
}

/* ─────────────────── Vote Rail ─────────────────── */
function VoteRail({ votes: initVotes }: { votes: number }) {
  const [votes, setVotes] = useState(initVotes);
  const [voted, setVoted] = useState<'up' | 'down' | null>(null);

  function vote(dir: 'up' | 'down') {
    if (voted === dir) { setVotes(initVotes); setVoted(null); }
    else { setVotes(initVotes + (dir === 'up' ? 1 : -1)); setVoted(dir); }
  }

  return (
    <div className="flex flex-col items-center gap-0.5 py-0.5">
      <motion.button whileTap={{ scale: 0.8 }} onClick={e => { e.stopPropagation(); vote('up'); }}
        className={clsx('p-1 rounded transition-colors', voted === 'up' ? 'text-[#FF6B35]' : 'text-[#555870] hover:text-[#FF6B35] hover:bg-[#FF6B35]/10')}>
        <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
      </motion.button>
      <span className="text-[11px] font-bold tabular-nums leading-none"
        style={{ color: voted === 'up' ? '#FF6B35' : voted === 'down' ? '#7B61FF' : '#8A93B2' }}>
        {fmtNum(votes)}
      </span>
      <motion.button whileTap={{ scale: 0.8 }} onClick={e => { e.stopPropagation(); vote('down'); }}
        className={clsx('p-1 rounded transition-colors', voted === 'down' ? 'text-[#7B61FF]' : 'text-[#555870] hover:text-[#7B61FF] hover:bg-[#7B61FF]/10')}>
        <ArrowDown className="w-4 h-4" strokeWidth={2.5} />
      </motion.button>
    </div>
  );
}

/* ─────────────────── Post Card ─────────────────── */
function PostCard({ post, sub, onClick }: { post: Post; sub: Sub; onClick: () => void }) {
  const [saved, setSaved] = useState(false);
  const [cwOpen, setCwOpen] = useState(!post.cw);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className={clsx(
        'flex rounded-md border overflow-hidden cursor-pointer group transition-all duration-150',
        post.pinned ? 'border-[#7B61FF]/35' : 'border-[#1C1F2E] hover:border-[#7B61FF]/25',
      )}
      style={{
        background: 'rgba(15,18,24,0.85)',
        backdropFilter: 'blur(4px)',
        boxShadow: post.pinned ? `0 0 0 1px rgba(123,97,255,0.08) inset, 0 2px 12px rgba(0,0,0,0.3)` : '0 1px 6px rgba(0,0,0,0.25)',
      }}
    >
      {/* Vote strip — Reddit's signature left column */}
      <div
        className="w-10 flex-shrink-0 flex flex-col items-center pt-2 rounded-l-md"
        style={{ background: 'rgba(255,255,255,0.015)' }}
        onClick={e => e.stopPropagation()}
      >
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
          <button onClick={e => { e.stopPropagation(); }} className="font-semibold hover:underline" style={{ color: sub.color }}>
            {sub.icon} r/{sub.name}
          </button>
          <span className="text-[#2E3248]">•</span>
          <span>Posted by</span>
          <span className="text-[#6B7280] hover:underline cursor-pointer flex items-center gap-1">
            <AvatarBlob color={post.avatarColor} size={14} letter={post.author[0]} />
            {post.anonymous ? 'u/Anonymous' : `u/${post.author}`}
          </span>
          <span className="text-[#2E3248]">•</span>
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
            className="flex items-center gap-1.5 text-[11px] text-[#F4A261] px-2.5 py-1.5 rounded mb-1.5 transition-colors"
            style={{ background: 'rgba(244,162,97,0.06)', border: '1px solid rgba(244,162,97,0.18)' }}>
            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
            CW: {post.cw} — tap to reveal
          </button>
        ) : (
          <p className="text-xs text-[#6B7280] leading-relaxed line-clamp-2 mb-2">{post.body}</p>
        )}

        {/* Action row */}
        <div className="flex items-center gap-0 -ml-1.5 mt-0.5" onClick={e => e.stopPropagation()}>
          <button onClick={onClick}
            className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
            <MessageSquare className="w-3.5 h-3.5" />
            {post.comments.length} Comments
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

/* ─────────────────── Comment Block (threaded) ─────────────────── */
function CommentBlock({ comment, depth = 0, subColor }: { comment: Comment; depth?: number; subColor: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [votes, setVotes] = useState(comment.votes);
  const [voted, setVoted] = useState<'up' | 'down' | null>(null);
  const [replying, setReplying] = useState(false);
  const [replyText, setReplyText] = useState('');

  function vote(dir: 'up' | 'down') {
    if (voted === dir) { setVotes(comment.votes); setVoted(null); }
    else { setVotes(comment.votes + (dir === 'up' ? 1 : -1)); setVoted(dir); }
  }

  const DEPTH_COLORS = ['#7B61FF', '#3ECFCF', '#F4A261', '#6BCB77', '#E07070'];
  const threadColor = DEPTH_COLORS[depth % DEPTH_COLORS.length];

  return (
    <div className={clsx('flex gap-2', depth > 0 && 'ml-5 pl-3 border-l')}>
      <style>{`.thread-border-${depth} { border-color: ${threadColor}28; }`}</style>

      <div className="flex flex-col items-center gap-0 pt-0.5">
        <button onClick={() => setCollapsed(!collapsed)} className="flex-shrink-0">
          <AvatarBlob color={comment.avatarColor} size={depth === 0 ? 26 : 20} letter={comment.author[0]} />
        </button>
        {!collapsed && (comment.replies?.length ?? 0) > 0 && (
          <div className="w-0.5 flex-1 mt-1 rounded-full" style={{ background: `${comment.avatarColor}30`, minHeight: 12 }} />
        )}
      </div>

      <div className="flex-1 min-w-0 pb-1">
        <div className="flex items-center gap-1.5 mb-1 flex-wrap">
          <span className="text-xs font-bold" style={{ color: subColor }}>{comment.author}</span>
          <span className="text-[10px] text-[#3A3E50]">·</span>
          <span className="text-[10px] text-[#3A3E50]">{comment.time}</span>
          <span className="text-[10px] text-[#3A3E50]">·</span>
          <span className="text-[10px] font-bold" style={{ color: voted === 'up' ? '#FF6B35' : voted === 'down' ? '#7B61FF' : '#4A5070' }}>
            {fmtNum(votes)} pts
          </span>
        </div>

        {!collapsed ? (
          <>
            <p className="text-sm text-[#B8BDD0] leading-relaxed mb-2">{comment.body}</p>

            <div className="flex items-center gap-0.5 -ml-1">
              <button onClick={() => vote('up')} className={clsx('p-1 rounded transition-colors', voted === 'up' ? 'text-[#FF6B35]' : 'text-[#4A5070] hover:text-[#FF6B35]')}>
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => vote('down')} className={clsx('p-1 rounded transition-colors', voted === 'down' ? 'text-[#7B61FF]' : 'text-[#4A5070] hover:text-[#7B61FF]')}>
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setReplying(!replying)}
                className="flex items-center gap-1 text-[11px] font-semibold text-[#4A5070] hover:text-[#8A93B2] px-2 py-0.5 rounded hover:bg-white/5 transition-colors ml-1">
                <MessageSquare className="w-3 h-3" /> Reply
              </button>
              <button className="flex items-center gap-1 text-[11px] font-semibold text-[#4A5070] hover:text-[#8A93B2] px-2 py-0.5 rounded hover:bg-white/5 transition-colors">
                <Share2 className="w-3 h-3" /> Share
              </button>
            </div>

            {replying && (
              <div className="mt-2 rounded overflow-hidden" style={{ border: '1px solid #1E2130' }}>
                <div className="flex items-center gap-1 px-2 py-1 border-b" style={{ background: 'rgba(10,13,20,0.6)', borderColor: '#1E2130' }}>
                  {[AlignLeft, Link2, ImageIcon].map((Icon, i) => (
                    <button key={i} className="p-1 rounded text-[#4A5070] hover:text-[#8A93B2] hover:bg-white/5 transition-colors">
                      <Icon className="w-3.5 h-3.5" />
                    </button>
                  ))}
                </div>
                <textarea autoFocus value={replyText} onChange={e => setReplyText(e.target.value)}
                  placeholder="What are your thoughts?"
                  rows={3}
                  className="w-full bg-[#0A0D14] px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] resize-none focus:outline-none" />
                <div className="flex items-center justify-end gap-2 px-3 py-2 border-t" style={{ background: 'rgba(10,13,20,0.6)', borderColor: '#1E2130' }}>
                  <button onClick={() => setReplying(false)} className="text-xs text-[#4A5070] hover:text-[#8A93B2] px-3 py-1.5 rounded transition-colors">Cancel</button>
                  <button disabled={!replyText.trim()} onClick={() => setReplying(false)}
                    className="text-xs bg-[#7B61FF] hover:bg-[#6B51EF] disabled:opacity-30 text-white px-3 py-1.5 rounded font-semibold transition-colors">Reply</button>
                </div>
              </div>
            )}

            {comment.replies?.map(r => (
              <div key={r.id} className="mt-2">
                <CommentBlock comment={r} depth={depth + 1} subColor={subColor} />
              </div>
            ))}
          </>
        ) : (
          <button onClick={() => setCollapsed(false)}
            className="text-[11px] text-[#4A5070] hover:text-[#8A93B2] transition-colors">
            [{comment.replies?.length ? `+${comment.replies.length + 1}` : '+1'} hidden]
          </button>
        )}
      </div>
    </div>
  );
}

/* ─────────────────── Post Detail ─────────────────── */
function PostDetail({ post, sub, onClose }: { post: Post; sub: Sub; onClose: () => void }) {
  const [replyText, setReplyText] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [comments, setComments] = useState(post.comments);
  const [sortComments, setSortComments] = useState<'best' | 'new' | 'top'>('best');

  function submitReply() {
    if (!replyText.trim()) return;
    setComments(prev => [{
      id: Date.now(), author: anonymous ? 'Anonymous' : 'You', avatarColor: '#7B61FF',
      body: replyText.trim(), votes: 1, time: 'just now',
    }, ...prev]);
    setReplyText('');
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[80] overflow-y-auto"
      style={{ background: 'rgba(8,11,18,0.97)', backdropFilter: 'blur(8px)' }}>
      <div className="max-w-3xl mx-auto min-h-screen pb-24 px-4">

        {/* Nav */}
        <div className="sticky top-0 z-10 flex items-center gap-2 py-2.5 mb-4 border-b border-[#1C1F2E]"
          style={{ background: 'rgba(13,16,24,0.95)', backdropFilter: 'blur(12px)' }}>
          <button onClick={onClose} className="flex items-center gap-1 text-xs font-semibold text-[#6B7280] hover:text-[#8A93B2] px-2 py-1.5 rounded hover:bg-white/5 transition-colors">
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
          <span className="text-[#2E3248]">/</span>
          <span className="text-xs font-semibold" style={{ color: sub.color }}>{sub.icon} r/{sub.name}</span>
          <span className="text-[#2E3248]">/</span>
          <span className="text-xs text-[#6B7280] truncate max-w-[200px]">{post.title.slice(0, 40)}…</span>
        </div>

        {/* Full post */}
        <div className="flex rounded-md overflow-hidden mb-4" style={{ background: 'rgba(15,18,24,0.9)', border: '1px solid #1C1F2E' }}>
          <div className="w-10 flex-shrink-0 flex flex-col items-center pt-3" style={{ background: 'rgba(255,255,255,0.015)' }}>
            <VoteRail votes={post.votes} />
          </div>
          <div className="flex-1 min-w-0 p-4">
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[#6B7280] mb-2">
              <AvatarBlob color={post.avatarColor} size={16} letter={post.author[0]} />
              <span>{post.anonymous ? 'u/Anonymous' : `u/${post.author}`}</span>
              <span className="text-[#2E3248]">•</span>
              <span>{post.time}</span>
              {post.flair && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                  style={{ background: `${post.flairColor}15`, color: post.flairColor, border: `1px solid ${post.flairColor}28` }}>
                  {post.flair}
                </span>
              )}
            </div>
            <h2 className="text-base font-bold text-[#F0F2F8] mb-3 leading-snug">{post.title}</h2>
            {post.cw && (
              <div className="flex items-center gap-2 text-[11px] text-[#F4A261] px-3 py-1.5 rounded mb-3"
                style={{ background: 'rgba(244,162,97,0.06)', border: '1px solid rgba(244,162,97,0.18)' }}>
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" /> CW: {post.cw}
              </div>
            )}
            <p className="text-sm text-[#A0A8C0] leading-relaxed mb-4">{post.body}</p>

            <div className="flex items-center gap-0 border-t border-[#1C1F2E] pt-2 -ml-1">
              <button className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
                <MessageSquare className="w-3.5 h-3.5" /> {post.comments.length} Comments
              </button>
              <button className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
                <Share2 className="w-3.5 h-3.5" /> Share
              </button>
              <button className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
                <Bookmark className="w-3.5 h-3.5" /> Save
              </button>
              <button className="flex items-center gap-1.5 text-[11px] font-semibold text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 px-2 py-1 rounded transition-colors">
                <Flag className="w-3.5 h-3.5" /> Report
              </button>
            </div>
          </div>
        </div>

        {/* Comment composer */}
        <div className="rounded-md overflow-hidden mb-5" style={{ background: 'rgba(15,18,24,0.9)', border: '1px solid #1C1F2E' }}>
          <div className="px-4 pt-3 pb-1">
            <p className="text-xs text-[#6B7280]">
              Comment as <span className="font-bold" style={{ color: sub.color }}>{anonymous ? 'Anonymous' : 'you'}</span>
            </p>
          </div>
          {/* Reddit-style toolbar + textarea */}
          <div className="mx-4 rounded overflow-hidden mb-3 focus-within:ring-1 ring-[#7B61FF]/40 transition-all" style={{ border: '1px solid #1E2130' }}>
            <div className="flex items-center gap-1 px-2 py-1.5 border-b border-[#1E2130]" style={{ background: 'rgba(10,13,20,0.5)' }}>
              {[AlignLeft, Link2, ImageIcon].map((Icon, i) => (
                <button key={i} className="p-1.5 rounded text-[#4A5070] hover:text-[#8A93B2] hover:bg-white/5 transition-colors">
                  <Icon className="w-3.5 h-3.5" />
                </button>
              ))}
            </div>
            <textarea value={replyText} onChange={e => setReplyText(e.target.value)}
              placeholder="What are your thoughts?"
              rows={4}
              className="w-full bg-transparent px-3 py-2.5 text-sm text-[#F0F2F8] placeholder-[#3A3E50] resize-none focus:outline-none" />
          </div>
          <div className="flex items-center justify-between px-4 pb-3">
            <button onClick={() => setAnonymous(!anonymous)}
              className={clsx('flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-full border transition-all',
                anonymous ? 'text-[#7B61FF] border-[#7B61FF]/40' : 'text-[#4A5070] border-[#2A2E3B] hover:border-[#3A3E50]')}
              style={anonymous ? { background: 'rgba(123,97,255,0.1)' } : {}}>
              {anonymous ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              {anonymous ? 'Anonymous' : 'Post as you'}
            </button>
            <button disabled={!replyText.trim()} onClick={submitReply}
              className="text-xs font-bold bg-[#7B61FF] hover:bg-[#6B51EF] disabled:opacity-30 disabled:cursor-not-allowed text-white px-4 py-1.5 rounded-full transition-colors shadow-[0_0_12px_rgba(123,97,255,0.3)]">
              Comment
            </button>
          </div>
        </div>

        {/* Comment sort */}
        <div className="flex items-center gap-2 px-1 mb-3">
          <span className="text-xs font-bold text-[#6B7280]">Sort by:</span>
          {(['best', 'new', 'top'] as const).map(s => (
            <button key={s} onClick={() => setSortComments(s)}
              className={clsx('text-xs px-2 py-0.5 rounded transition-colors capitalize',
                sortComments === s ? 'bg-[#7B61FF]/15 text-[#7B61FF] font-bold' : 'text-[#4A5070] hover:text-[#8A93B2]')}>
              {s}
            </button>
          ))}
        </div>

        {/* Comments */}
        <div className="space-y-3">
          {comments.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
              className="rounded-md p-3" style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
              <CommentBlock comment={c} subColor={sub.color} />
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ─────────────────── New Post Modal ─────────────────── */
const FLAIRS = ['Question', 'Venting', 'Success Story', 'Template', 'Research', 'Diagnosis Journey', 'Win 🎉'];

function NewPostModal({ subs, defaultSub, onClose, onSubmit }: {
  subs: Sub[];
  defaultSub: string;
  onClose: () => void;
  onSubmit: (post: Omit<Post, 'id' | 'votes' | 'comments' | 'time'>) => void;
}) {
  const [tab, setTab] = useState<'post' | 'image' | 'link'>('post');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [selectedSub, setSelectedSub] = useState(defaultSub);
  const [flair, setFlair] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [cw, setCw] = useState('');
  const [showSubPicker, setShowSubPicker] = useState(false);
  const sub = subs.find(s => s.id === selectedSub)!;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[90] flex items-start justify-center pt-[5vh] px-4 pb-10 overflow-y-auto"
      style={{ background: 'rgba(8,11,18,0.92)', backdropFilter: 'blur(8px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>

      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 20, opacity: 0 }}
        transition={{ type: 'spring', damping: 30 }} className="w-full max-w-2xl">

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-black text-[#F0F2F8]">Create a Post</h2>
          <button onClick={onClose} className="p-1.5 rounded-full hover:bg-white/8 text-[#6B7280] hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sub picker */}
        <div className="relative mb-4">
          <button onClick={() => setShowSubPicker(!showSubPicker)}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm transition-colors"
            style={{ background: 'rgba(15,18,24,0.9)', border: showSubPicker ? `1px solid ${sub.color}60` : '1px solid #1C1F2E' }}>
            <span className="text-base">{sub.icon}</span>
            <span className="font-bold" style={{ color: sub.color }}>r/{sub.name}</span>
            <ChevronDown className={clsx('w-4 h-4 text-[#6B7280] transition-transform', showSubPicker && 'rotate-180')} />
          </button>

          <AnimatePresence>
            {showSubPicker && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="absolute top-full left-0 mt-1 w-72 rounded-lg shadow-2xl z-10 overflow-hidden"
                style={{ background: '#13161F', border: '1px solid #2A2E3B' }}>
                {subs.map(s => (
                  <button key={s.id} onClick={() => { setSelectedSub(s.id); setShowSubPicker(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors text-sm hover:bg-white/5"
                    style={selectedSub === s.id ? { background: `${s.color}12` } : {}}>
                    <span className="text-lg">{s.icon}</span>
                    <div>
                      <div className="font-semibold" style={selectedSub === s.id ? { color: s.color } : { color: '#F0F2F8' }}>r/{s.name}</div>
                      <div className="text-[10px] text-[#4A5070]">{fmtNum(s.members)} members</div>
                    </div>
                    {selectedSub === s.id && <CheckCircle2 className="w-4 h-4 ml-auto" style={{ color: s.color }} />}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Tab bar */}
        <div className="flex rounded-t-md overflow-hidden" style={{ border: '1px solid #1C1F2E', borderBottom: 'none', background: 'rgba(15,18,24,0.9)' }}>
          {[{ id: 'post', label: 'Post', icon: AlignLeft }, { id: 'image', label: 'Image', icon: ImageIcon }, { id: 'link', label: 'Link', icon: Link2 }].map(t => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id as any)}
                className={clsx('flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-bold border-b-2 transition-all',
                  tab === t.id ? 'border-[#7B61FF] text-[#F0F2F8]' : 'border-transparent text-[#555870] hover:text-[#8A93B2]')}
                style={tab === t.id ? { background: 'rgba(123,97,255,0.06)' } : {}}>
                <Icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            );
          })}
        </div>

        {/* Form */}
        <div className="p-4 space-y-3 rounded-b-md" style={{ background: 'rgba(15,18,24,0.9)', border: '1px solid #1C1F2E' }}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" maxLength={300}
            className="w-full bg-[#0A0D14] border border-[#1E2130] rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none focus:border-[#7B61FF]/50 transition-colors" />

          {tab === 'post' && (
            <textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Text (optional)" rows={6}
              className="w-full bg-[#0A0D14] border border-[#1E2130] rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] resize-none focus:outline-none focus:border-[#7B61FF]/50 transition-colors" />
          )}
          {tab === 'link' && (
            <input placeholder="URL" className="w-full bg-[#0A0D14] border border-[#1E2130] rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none focus:border-[#7B61FF]/50 transition-colors" />
          )}
          {tab === 'image' && (
            <div className="border-2 border-dashed border-[#1E2130] rounded-lg p-8 text-center text-[#4A5070] hover:border-[#7B61FF]/30 transition-colors cursor-pointer">
              <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">Drop image or click to upload</p>
            </div>
          )}

          {/* Flair */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#4A5070] mb-1.5">Flair</p>
            <div className="flex flex-wrap gap-1.5">
              {FLAIRS.map(f => (
                <button key={f} onClick={() => setFlair(flair === f ? '' : f)}
                  className="text-[10px] px-2.5 py-1 rounded-full border transition-all"
                  style={flair === f ? { background: sub.color, color: 'white', borderColor: sub.color } : { borderColor: '#2A2E3B', color: '#6B7280' }}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          <input value={cw} onChange={e => setCw(e.target.value)}
            placeholder="Content warning (optional) — e.g. Medical dismissal, fatigue spiral"
            className="w-full bg-[#0A0D14] border border-[#1E2130] rounded px-3 py-2 text-sm text-[#F0F2F8] placeholder-[#3A3E50] focus:outline-none focus:border-[#F4A261]/40 transition-colors" />

          <div className="flex items-center justify-between pt-1 border-t border-[#1E2130]">
            <button onClick={() => setAnonymous(!anonymous)}
              className={clsx('flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-all',
                anonymous ? 'text-[#7B61FF] border-[#7B61FF]/40' : 'text-[#4A5070] border-[#2A2E3B] hover:border-[#3A3E50]')}
              style={anonymous ? { background: 'rgba(123,97,255,0.1)' } : {}}>
              {anonymous ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {anonymous ? 'Anonymous' : 'Post as you'}
            </button>
            <div className="flex gap-2">
              <button onClick={onClose} className="text-xs border border-[#2A2E3B] text-[#8A93B2] px-4 py-1.5 rounded-full hover:border-[#3A3E50] transition-colors">
                Cancel
              </button>
              <button disabled={!title.trim()}
                onClick={() => {
                  onSubmit({ subId: selectedSub, author: anonymous ? 'Anonymous' : 'You', avatarColor: '#7B61FF', anonymous, flair, flairColor: sub.color, title: title.trim(), body: body.trim(), cw: cw.trim() || undefined });
                  onClose();
                }}
                className="text-xs font-bold bg-[#7B61FF] hover:bg-[#6B51EF] disabled:opacity-30 disabled:cursor-not-allowed text-white px-4 py-1.5 rounded-full transition-colors shadow-[0_0_14px_rgba(123,97,255,0.3)]">
                Post
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ─────────────────── Sub Banner (Reddit subreddit header) ─────────────────── */
function SubBanner({ sub, joined, onJoin }: { sub: Sub; joined: boolean; onJoin: () => void }) {
  return (
    <div className="rounded-md overflow-hidden mb-4" style={{ border: '1px solid #1C1F2E', boxShadow: `0 0 40px ${sub.glow}` }}>
      {/* Banner image area */}
      <div className="h-20 relative overflow-hidden" style={{ background: sub.bannerGradient }}>
        <div className="absolute inset-0" style={{ background: `radial-gradient(ellipse at 25% 60%, ${sub.color}35 0%, transparent 65%)` }} />
        <div className="absolute inset-0 opacity-[0.07]"
          style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.05) 3px, rgba(255,255,255,0.05) 4px)' }} />
      </div>

      {/* Community info */}
      <div className="px-4 pb-3 pt-2" style={{ background: 'rgba(15,18,24,0.95)' }}>
        <div className="flex items-end gap-3 -mt-7 mb-3">
          <div className="w-16 h-16 rounded-full flex-shrink-0"
            style={{ background: `radial-gradient(circle, ${sub.color}25, ${sub.color}05)`, border: `4px solid rgba(15,18,24,0.95)`, boxShadow: `0 0 20px ${sub.glow}` }} />
          <div className="pb-1 flex-1 min-w-0">
            <h1 className="text-base font-black text-[#F0F2F8]">{sub.displayName}</h1>
            <p className="text-xs text-[#555870]">r/{sub.name}</p>
          </div>
          <button onClick={onJoin}
            className="flex-shrink-0 text-xs font-black px-5 py-2 rounded-full border transition-all mb-1"
            style={!joined
              ? { background: sub.color, borderColor: sub.color, color: 'white', boxShadow: `0 0 14px ${sub.glow}` }
              : { background: 'transparent', borderColor: '#2A2E3B', color: '#8A93B2' }}>
            {joined ? 'Joined ✓' : 'Join'}
          </button>
        </div>
        <p className="text-xs text-[#8A93B2] leading-relaxed mb-2">{sub.description}</p>
        <div className="flex items-center gap-4 text-[11px] text-[#6B7280]">
          <span><strong className="text-[#C8CAD6] text-xs">{fmtNum(sub.members)}</strong> Members</span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#6BCB77]" style={{ boxShadow: '0 0 6px #6BCB77' }} />
            <strong className="text-[#6BCB77] text-xs">{fmtNum(sub.online)}</strong> Online
          </span>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── Create Post box ─────────────────── */
function CreatePostBox({ onClick }: { onClick: () => void }) {
  return (
    <div className="flex items-center gap-2 rounded-md p-2 mb-3 transition-colors"
      style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
      <AvatarBlob color="#7B61FF" size={34} letter="Y" />
      <button onClick={onClick}
        className="flex-1 text-left rounded px-3 py-2 text-sm text-[#3A3E50] hover:text-[#6B7280] focus:outline-none transition-colors"
        style={{ background: 'rgba(10,13,20,0.8)', border: '1px solid #1E2130' }}>
        Create Post
      </button>
      <button onClick={onClick} className="p-2 rounded text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 transition-colors">
        <ImageIcon className="w-5 h-5" />
      </button>
      <button onClick={onClick} className="p-2 rounded text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 transition-colors">
        <Link2 className="w-5 h-5" />
      </button>
    </div>
  );
}

/* ─────────────────── Sort bar ─────────────────── */
type SortMode = 'hot' | 'new' | 'top' | 'rising';
const SORT_OPTS: { id: SortMode; label: string; icon: React.ElementType }[] = [
  { id: 'hot', label: 'Hot', icon: Flame },
  { id: 'new', label: 'New', icon: Clock },
  { id: 'top', label: 'Top', icon: TrendingUp },
  { id: 'rising', label: 'Rising', icon: Zap },
];

function SortBar({ sort, setSort }: { sort: SortMode; setSort: (s: SortMode) => void }) {
  return (
    <div className="flex items-center gap-1 rounded-md px-2 py-1.5 mb-3"
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
  );
}

/* ─────────────────── Right sidebar widgets ─────────────────── */
function CommunityAbout({ sub, joined, onJoin, onCreatePost }: { sub: Sub; joined: boolean; onJoin: () => void; onCreatePost: () => void }) {
  return (
    <div className="rounded-md overflow-hidden" style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
      <div className="h-8" style={{ background: sub.bannerGradient }} />
      <div className="p-3">
        <h3 className="font-black text-sm text-[#F0F2F8] mb-2">About Community</h3>
        <p className="text-xs text-[#8A93B2] leading-relaxed mb-3">{sub.description}</p>
        <div className="flex gap-5 text-xs border-y border-[#1C1F2E] py-3 mb-3">
          <div>
            <p className="font-black text-[#F0F2F8] text-sm">{fmtNum(sub.members)}</p>
            <p className="text-[#6B7280]">Members</p>
          </div>
          <div>
            <p className="font-black text-[#6BCB77] text-sm flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#6BCB77]" style={{ boxShadow: '0 0 5px #6BCB77' }} />{fmtNum(sub.online)}
            </p>
            <p className="text-[#6B7280]">Online</p>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <button onClick={onJoin}
            className="w-full text-xs font-black py-2 rounded-full transition-all"
            style={!joined ? { background: sub.color, color: 'white', boxShadow: `0 0 12px ${sub.glow}` } : { background: 'transparent', border: '1px solid #2A2E3B', color: '#8A93B2' }}>
            {joined ? 'Joined ✓' : `Join r/${sub.name}`}
          </button>
          <button onClick={onCreatePost}
            className="w-full text-xs font-black py-2 rounded-full border transition-colors"
            style={{ borderColor: `${sub.color}50`, color: sub.color }}>
            + Create Post
          </button>
        </div>
        {sub.tags.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#1C1F2E]">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#4A5070] mb-2">Post Flairs</p>
            <div className="flex flex-wrap gap-1.5">
              {sub.tags.map(t => (
                <span key={t} className="text-[10px] px-2 py-0.5 rounded-full"
                  style={{ background: `${sub.color}12`, color: sub.color, border: `1px solid ${sub.color}22` }}>{t}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RulesWidget({ sub }: { sub: Sub }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="rounded-md overflow-hidden" style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#1C1F2E]">
        <Lock className="w-3.5 h-3.5 text-[#555870]" />
        <h3 className="text-xs font-black text-[#F0F2F8]">r/{sub.name} Rules</h3>
      </div>
      {sub.rules.map((rule, i) => (
        <button key={i} onClick={() => setOpen(open === i ? null : i)}
          className="w-full text-left px-3 py-2.5 border-b border-[#1C1F2E] last:border-0 hover:bg-white/3 transition-colors">
          <div className="flex items-start gap-2">
            <span className="text-[10px] font-black text-[#555870] mt-0.5 w-4 flex-shrink-0">{i + 1}.</span>
            <span className="text-xs text-[#8A93B2] flex-1 leading-relaxed">{rule}</span>
            <ChevronDown className={clsx('w-3.5 h-3.5 text-[#4A5070] flex-shrink-0 transition-transform mt-0.5', open === i && 'rotate-180')} />
          </div>
        </button>
      ))}
    </div>
  );
}

function SafetyWidget() {
  return (
    <div className="rounded-md p-3" style={{ background: 'rgba(224,112,112,0.05)', border: '1px solid rgba(224,112,112,0.2)' }}>
      <h4 className="text-[11px] font-bold text-[#E07070] mb-1.5 flex items-center gap-1.5">
        <AlertTriangle className="w-3.5 h-3.5" /> If you're in crisis
      </h4>
      <p className="text-[11px] text-[#8A93B2] leading-relaxed">
        <strong className="text-[#E07070]">988</strong> Suicide & Crisis Lifeline (US)<br />
        <strong className="text-[#E07070]">116 123</strong> Samaritans (UK)<br />
        Text <strong className="text-[#E07070]">HOME</strong> to <strong className="text-[#E07070]">741741</strong>
      </p>
    </div>
  );
}

function HomeAboutWidget({ onCreatePost }: { onCreatePost: () => void }) {
  return (
    <div className="rounded-md overflow-hidden" style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid rgba(123,97,255,0.2)', boxShadow: '0 0 20px rgba(123,97,255,0.06)' }}>
      <div className="h-10" style={{ background: 'linear-gradient(135deg, #1a1040 0%, #2d1b6e 100%)' }} />
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2 -mt-5">
          <div className="w-10 h-10 rounded-full flex-shrink-0"
            style={{ background: 'rgba(123,97,255,0.2)', border: '3px solid rgba(15,18,24,0.95)', boxShadow: '0 0 12px rgba(123,97,255,0.3)' }} />
        </div>
        <p className="text-xs text-[#8A93B2] leading-relaxed mb-3">
          Your diagnosis journey, shared. 6 sub-communities for every part of living with chronic illness.
        </p>
        <button onClick={onCreatePost} className="w-full text-xs font-black py-2 rounded-full text-white mb-2 transition-all"
          style={{ background: '#7B61FF', boxShadow: '0 0 12px rgba(123,97,255,0.3)' }}>
          + Create Post
        </button>
        <ul className="mt-2 space-y-1.5 text-[11px] text-[#8A93B2]">
          {['We believe your symptoms', 'No medical advice — ever', 'Validate first, advise after', 'Rest is not failure'].map(p => (
            <li key={p} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#6BCB77', boxShadow: '0 0 4px #6BCB77' }} /> {p}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function TopCommunitiesWidget({ subs, activeSub, onSelect }: { subs: Sub[]; activeSub: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="rounded-md overflow-hidden" style={{ background: 'rgba(15,18,24,0.85)', border: '1px solid #1C1F2E' }}>
      <div className="px-3 py-2.5 border-b border-[#1C1F2E]">
        <h3 className="text-xs font-black text-[#F0F2F8]">Top Communities</h3>
      </div>
      {[...subs].sort((a, b) => b.members - a.members).map((s, i) => (
        <button key={s.id} onClick={() => onSelect(s.id)}
          className="w-full flex items-center gap-2.5 px-3 py-2 border-b border-[#1C1F2E] last:border-0 transition-colors text-left hover:bg-white/3"
          style={activeSub === s.id ? { background: `${s.color}0C` } : {}}>
          <span className="text-[10px] text-[#4A5070] font-mono w-4 flex-shrink-0">{i + 1}</span>
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color, boxShadow: `0 0 5px ${s.color}` }} />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold truncate" style={activeSub === s.id ? { color: s.color } : { color: '#C8CAD6' }}>r/{s.name}</div>
            <div className="text-[10px] text-[#4A5070]">{fmtNum(s.members)}</div>
          </div>
        </button>
      ))}
    </div>
  );
}

/* ─────────────────── Main Forum ─────────────────── */
export const Forum = () => {
  const navigate = useNavigate();
  const [activeSub, setActiveSub] = useState<string | null>(null);
  const [posts, setPosts] = useState<Post[]>(ALL_POSTS);
  const [openPost, setOpenPost] = useState<Post | null>(null);
  const [showCompose, setShowCompose] = useState(false);
  const [sort, setSort] = useState<SortMode>('hot');
  const [search, setSearch] = useState('');
  const [joinedSubs, setJoinedSubs] = useState<Set<string>>(new Set());

  const currentSub = activeSub ? SUBS.find(s => s.id === activeSub) ?? null : null;

  const displayed = posts
    .filter(p => activeSub ? p.subId === activeSub : true)
    .filter(p => search ? (p.title + p.body + p.author).toLowerCase().includes(search.toLowerCase()) : true)
    .sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return sort === 'new' ? b.id - a.id : b.votes - a.votes;
    });

  function toggleJoin(id: string) {
    setJoinedSubs(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  function addPost(partial: Omit<Post, 'id' | 'votes' | 'comments' | 'time'>) {
    setPosts(prev => [{ ...partial, id: Date.now(), votes: 1, comments: [], time: 'just now' }, ...prev]);
    setActiveSub(partial.subId);
  }

  return (
    <div className="min-h-screen font-sans" style={{ background: 'rgba(8,11,18,0.88)', backdropFilter: 'blur(1px)' }}>

      {/* ── Top Nav ── */}
      <div className="sticky top-0 z-40" style={{ background: 'rgba(13,16,24,0.96)', backdropFilter: 'blur(16px)', borderBottom: '1px solid #1A1D26' }}>
        <div className="max-w-5xl mx-auto flex items-center gap-2 px-4 h-12">
          <button onClick={() => navigate(-1)} className="p-1.5 rounded-full text-[#555870] hover:text-[#8A93B2] hover:bg-white/5 transition-colors flex-shrink-0">
            <ChevronLeft className="w-5 h-5" />
          </button>

          {/* Active sub breadcrumb */}
          {currentSub && (
            <button onClick={() => setActiveSub(null)}
              className="flex items-center gap-1.5 text-xs font-bold ml-1 transition-colors"
              style={{ color: currentSub.color }}>
              <span className="text-[#2E3248] font-normal">/</span>
              r/{currentSub.name}
            </button>
          )}

          {/* Search */}
          <div className="flex-1 max-w-sm mx-auto relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#3A3E50]" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search communities…"
              className="w-full rounded-full pl-9 pr-4 py-1.5 text-xs placeholder-[#3A3E50] focus:outline-none transition-colors"
              style={{ background: 'rgba(26,29,38,0.9)', border: '1px solid #2A2E3B', color: '#F0F2F8' }} />
          </div>

          <div className="flex items-center gap-1.5 ml-auto">
            <button className="p-2 rounded-full text-[#4A5070] hover:text-[#8A93B2] hover:bg-white/5 transition-colors">
              <Bell className="w-4 h-4" />
            </button>
            <motion.button whileTap={{ scale: 0.95 }} onClick={() => setShowCompose(true)}
              className="flex items-center gap-1.5 text-[11px] font-black text-white px-3 py-1.5 rounded-full transition-colors"
              style={{ background: '#7B61FF', boxShadow: '0 0 14px rgba(123,97,255,0.35)' }}>
              <Plus className="w-3.5 h-3.5" /> Create Post
            </motion.button>
          </div>
        </div>
      </div>

      {/* Safety strip */}
      <div style={{ background: 'rgba(62,207,207,0.03)', borderBottom: '1px solid rgba(62,207,207,0.08)' }}>
        <div className="max-w-5xl mx-auto px-4 py-1.5 flex items-center gap-2 text-[10px]" style={{ color: 'rgba(62,207,207,0.55)' }}>
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
          Peer support only — no medical advice · Crisis support:
          <strong className="ml-0.5" style={{ color: 'rgba(62,207,207,0.8)' }}>988</strong> ·
          <strong style={{ color: 'rgba(62,207,207,0.8)' }}>116 123</strong> · text HOME to 741741
        </div>
      </div>

      {/* Main 3-column layout */}
      <div className="max-w-5xl mx-auto px-4 py-5 flex gap-5">

        {/* Left nav */}
        <aside className="w-56 flex-shrink-0 hidden lg:block">
          <div className="sticky top-16">
            <p className="text-[10px] font-black uppercase tracking-widest px-2 py-1.5 mb-1" style={{ color: '#4A5070' }}>Communities</p>

            <button onClick={() => setActiveSub(null)}
              className="w-full flex items-center gap-2.5 px-2 py-2 rounded text-sm transition-colors mb-0.5"
              style={!activeSub ? { background: 'rgba(123,97,255,0.12)', color: '#7B61FF', fontWeight: 700 } : { color: '#8A93B2' }}>
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: '#7B61FF', boxShadow: '0 0 6px rgba(123,97,255,0.6)' }} /> Home
            </button>

            <div className="my-2 border-t" style={{ borderColor: '#1C1F2E' }} />

            {SUBS.map(s => (
              <button key={s.id} onClick={() => setActiveSub(activeSub === s.id ? null : s.id)}
                className="w-full flex items-center gap-2.5 px-2 py-2 rounded transition-all text-sm mb-0.5"
                style={activeSub === s.id ? { background: `${s.color}15`, color: s.color, fontWeight: 700 } : { color: '#8A93B2' }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color, boxShadow: `0 0 6px ${s.color}` }} />
                <div className="flex-1 min-w-0 text-left">
                  <div className="text-xs font-semibold truncate">{s.displayName}</div>
                  <div className="text-[9px]" style={{ color: '#4A5070' }}>{fmtNum(s.members)}</div>
                </div>
                {joinedSubs.has(s.id) && <span className="text-[9px] font-black" style={{ color: '#6BCB77' }}>●</span>}
              </button>
            ))}
          </div>
        </aside>

        {/* Center feed */}
        <main className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            {currentSub && (
              <motion.div key={currentSub.id} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <SubBanner sub={currentSub} joined={joinedSubs.has(currentSub.id)} onJoin={() => toggleJoin(currentSub.id)} />
              </motion.div>
            )}
          </AnimatePresence>

          <CreatePostBox onClick={() => setShowCompose(true)} />
          <SortBar sort={sort} setSort={setSort} />

          <div className="space-y-2">
            {displayed.length === 0 ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-center py-16 rounded-md"
                style={{ background: 'rgba(15,18,24,0.7)', border: '1px solid #1C1F2E', color: '#4A5070' }}>
                <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-20" />
                <p className="text-sm">No posts yet.</p>
                <button onClick={() => setShowCompose(true)} className="mt-2 text-xs font-semibold hover:underline" style={{ color: '#7B61FF' }}>
                  Be the first to post
                </button>
              </motion.div>
            ) : (
              displayed.map(post => {
                const sub = SUBS.find(s => s.id === post.subId)!;
                return <PostCard key={post.id} post={post} sub={sub} onClick={() => setOpenPost(post)} />;
              })
            )}
          </div>
        </main>

        {/* Right sidebar */}
        <aside className="w-72 flex-shrink-0 hidden xl:block">
          <div className="sticky top-16 space-y-3">
            {currentSub ? (
              <>
                <CommunityAbout sub={currentSub} joined={joinedSubs.has(currentSub.id)} onJoin={() => toggleJoin(currentSub.id)} onCreatePost={() => setShowCompose(true)} />
                <RulesWidget sub={currentSub} />
              </>
            ) : (
              <>
                <HomeAboutWidget onCreatePost={() => setShowCompose(true)} />
                <TopCommunitiesWidget subs={SUBS} activeSub={activeSub} onSelect={setActiveSub} />
              </>
            )}
            <SafetyWidget />
          </div>
        </aside>
      </div>

      {/* Post detail */}
      <AnimatePresence>
        {openPost && (
          <PostDetail post={openPost} sub={SUBS.find(s => s.id === openPost.subId)!} onClose={() => setOpenPost(null)} />
        )}
      </AnimatePresence>

      {/* Compose */}
      <AnimatePresence>
        {showCompose && (
          <NewPostModal subs={SUBS} defaultSub={activeSub ?? 'autoimmune'} onClose={() => setShowCompose(false)} onSubmit={addPost} />
        )}
      </AnimatePresence>

      {/* Mobile FAB */}
      <div className="fixed bottom-6 right-6 z-50 xl:hidden">
        <motion.button whileTap={{ scale: 0.9 }} onClick={() => setShowCompose(true)}
          className="w-12 h-12 rounded-full flex items-center justify-center text-white"
          style={{ background: '#7B61FF', boxShadow: '0 0 28px rgba(123,97,255,0.55)' }}>
          <Plus className="w-5 h-5" />
        </motion.button>
      </div>
    </div>
  );
};
