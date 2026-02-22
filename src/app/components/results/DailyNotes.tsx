import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, Calendar, Smile, Meh, Frown, Trash2, ChevronDown, ChevronUp } from 'lucide-react';

interface NoteEntry {
  id: string;
  date: string;
  mood: 'good' | 'okay' | 'bad';
  text: string;
  symptoms: string[];
}

const SYMPTOM_CHIPS = [
  'Fatigue', 'Joint Pain', 'Rash', 'Brain Fog', 'Headache',
  'Swelling', 'Fever', 'Nausea', 'Insomnia', 'Muscle Ache',
];

const MOOD_OPTIONS: { value: NoteEntry['mood']; icon: typeof Smile; label: string; color: string }[] = [
  { value: 'good', icon: Smile,  label: 'Good Day',  color: '#3ECFCF' },
  { value: 'okay', icon: Meh,    label: 'Okay',      color: '#F4A261' },
  { value: 'bad',  icon: Frown,  label: 'Rough Day', color: '#E07070' },
];

const formatDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
};

export const DailyNotes = () => {
  const [notes, setNotes] = useState<NoteEntry[]>(() => {
    try {
      const saved = localStorage.getItem('aura-daily-notes');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });

  const [isAdding, setIsAdding] = useState(false);
  const [draftMood, setDraftMood] = useState<NoteEntry['mood']>('okay');
  const [draftText, setDraftText] = useState('');
  const [draftSymptoms, setDraftSymptoms] = useState<string[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const persist = (updated: NoteEntry[]) => {
    setNotes(updated);
    try { localStorage.setItem('aura-daily-notes', JSON.stringify(updated)); } catch {}
  };

  const handleAdd = () => {
    if (!draftText.trim()) return;
    const entry: NoteEntry = {
      id: Date.now().toString(),
      date: new Date().toISOString(),
      mood: draftMood,
      text: draftText.trim(),
      symptoms: draftSymptoms,
    };
    persist([entry, ...notes]);
    setDraftText('');
    setDraftMood('okay');
    setDraftSymptoms([]);
    setIsAdding(false);
  };

  const handleDelete = (id: string) => {
    persist(notes.filter(n => n.id !== id));
  };

  const toggleSymptom = (s: string) => {
    setDraftSymptoms(prev =>
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
    );
  };

  const moodIcon = (mood: NoteEntry['mood'], size = 'w-5 h-5') => {
    const opt = MOOD_OPTIONS.find(m => m.value === mood)!;
    const Icon = opt.icon;
    return <Icon className={size} style={{ color: opt.color }} />;
  };

  return (
    <div id="daily-notes" className="scroll-target">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-[#F0F2F8]">
          Daily Notes
        </h3>
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center gap-1.5 text-sm font-medium text-[#7B61FF] hover:text-[#9B85FF] transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Entry
        </button>
      </div>

      {/* Add new entry form */}
      <AnimatePresence>
        {isAdding && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-6"
          >
            <div className="bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 space-y-5">

              {/* Mood selector */}
              <div>
                <label className="text-xs uppercase tracking-wider text-[#8A93B2] mb-2 block">How are you feeling today?</label>
                <div className="flex gap-3">
                  {MOOD_OPTIONS.map(opt => {
                    const Icon = opt.icon;
                    const active = draftMood === opt.value;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => setDraftMood(opt.value)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                          active
                            ? 'border-[' + opt.color + ']/40 bg-[' + opt.color + ']/10'
                            : 'border-[#2A2E3B] bg-transparent hover:border-[#3A3E4B]'
                        }`}
                        style={active ? { borderColor: opt.color + '66', backgroundColor: opt.color + '15', color: opt.color } : { color: '#8A93B2' }}
                      >
                        <Icon className="w-5 h-5" />
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Symptom chips */}
              <div>
                <label className="text-xs uppercase tracking-wider text-[#8A93B2] mb-2 block">Symptoms noticed today</label>
                <div className="flex flex-wrap gap-2">
                  {SYMPTOM_CHIPS.map(s => {
                    const active = draftSymptoms.includes(s);
                    return (
                      <button
                        key={s}
                        onClick={() => toggleSymptom(s)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                          active
                            ? 'bg-[#7B61FF]/15 border-[#7B61FF]/40 text-[#7B61FF]'
                            : 'bg-transparent border-[#2A2E3B] text-[#8A93B2] hover:border-[#3A3E4B]'
                        }`}
                      >
                        {s}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Text area */}
              <div>
                <label className="text-xs uppercase tracking-wider text-[#8A93B2] mb-2 block">What happened today?</label>
                <textarea
                  value={draftText}
                  onChange={e => setDraftText(e.target.value)}
                  placeholder="Describe how you're feeling, what you noticed, any triggers..."
                  rows={4}
                  className="w-full bg-[#0A0D14] border border-[#2A2E3B] rounded-xl px-4 py-3 text-sm text-[#F0F2F8] placeholder-[#8A93B2]/50 resize-none focus:outline-none focus:border-[#7B61FF]/50 transition-colors"
                />
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setIsAdding(false)}
                  className="px-4 py-2 rounded-lg text-sm text-[#8A93B2] hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAdd}
                  disabled={!draftText.trim()}
                  className="px-5 py-2 rounded-lg text-sm font-medium bg-[#7B61FF] text-white hover:bg-[#6B51EF] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  Save Entry
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Entries list */}
      {notes.length === 0 && !isAdding ? (
        <div className="text-center py-12 text-[#8A93B2]">
          <Calendar className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No entries yet. Start tracking how you feel each day.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => {
            const isExpanded = expandedId === note.id;
            return (
              <motion.div
                key={note.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#13161F] border border-[#2A2E3B] rounded-xl overflow-hidden"
              >
                {/* Collapsed row */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : note.id)}
                  className="w-full flex items-center gap-4 p-4 text-left hover:bg-[#1A1D26]/50 transition-colors"
                >
                  {moodIcon(note.mood)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-[#F0F2F8]">{formatDate(note.date)}</span>
                      {note.symptoms.length > 0 && (
                        <span className="text-[10px] text-[#8A93B2] bg-[#1A1D26] px-2 py-0.5 rounded-full">
                          {note.symptoms.length} symptom{note.symptoms.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#8A93B2] truncate">{note.text}</p>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-[#8A93B2] shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-[#8A93B2] shrink-0" />
                  )}
                </button>

                {/* Expanded details */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 pt-0 border-t border-[#2A2E3B] space-y-3">
                        {/* Symptoms */}
                        {note.symptoms.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-3">
                            {note.symptoms.map(s => (
                              <span
                                key={s}
                                className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#7B61FF]/10 text-[#7B61FF] border border-[#7B61FF]/20"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Full text */}
                        <p className="text-sm text-[#C0C7DC] leading-relaxed whitespace-pre-wrap">
                          {note.text}
                        </p>

                        {/* Delete */}
                        <div className="flex justify-end">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(note.id); }}
                            className="flex items-center gap-1.5 text-xs text-[#E07070]/60 hover:text-[#E07070] transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Delete
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};
