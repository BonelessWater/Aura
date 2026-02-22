import React, { useEffect, useState } from 'react';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, Area, AreaChart,
} from 'recharts';
import { motion } from 'motion/react';

// ─── CSV helpers ──────────────────────────────────────────────────────────────
function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',');
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => { obj[h.trim()] = (vals[i] ?? '').trim(); });
    return obj;
  });
}

async function loadCSV(path: string) {
  const res = await fetch(path);
  return parseCSV(await res.text());
}

function toDate(s: string) { return s.slice(0, 10); }

// ─── Aggregation ──────────────────────────────────────────────────────────────
function avgByDay(rows: Record<string, string>[]) {
  const sums: Record<string, { total: number; count: number }> = {};
  for (const r of rows) {
    const day = toDate(r.startDate);
    const val = parseFloat(r.value);
    if (!day || isNaN(val)) continue;
    if (!sums[day]) sums[day] = { total: 0, count: 0 };
    sums[day].total += val;
    sums[day].count += 1;
  }
  return Object.entries(sums)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, { total, count }]) => ({ day, value: Math.round(total / count) }));
}

function sumByDay(rows: Record<string, string>[]) {
  const sums: Record<string, number> = {};
  for (const r of rows) {
    const day = toDate(r.startDate);
    const val = parseFloat(r.value);
    if (!day || isNaN(val)) continue;
    sums[day] = (sums[day] ?? 0) + val;
  }
  return Object.entries(sums)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, value]) => ({ day, value: Math.round(value) }));
}

function sleepByDay(rows: Record<string, string>[]) {
  const byDay: Record<string, { sleep: number; deep: number; rem: number }> = {};
  for (const r of rows) {
    const v = r.value;
    const day = toDate(r.startDate);
    if (!day) continue;
    if (!byDay[day]) byDay[day] = { sleep: 0, deep: 0, rem: 0 };
    const start = new Date(r.startDate).getTime();
    const end = new Date(r.endDate).getTime();
    const mins = (end - start) / 60000;
    if (v.includes('AsleepCore')) { byDay[day].sleep += mins; }
    else if (v.includes('AsleepDeep')) { byDay[day].sleep += mins; byDay[day].deep += mins; }
    else if (v.includes('AsleepREM')) { byDay[day].sleep += mins; byDay[day].rem += mins; }
  }
  return Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, { sleep, deep, rem }]) => ({
      day,
      hours: parseFloat((sleep / 60).toFixed(1)),
      quality: sleep > 0 ? Math.round(((deep + rem) / sleep) * 100) : 0,
    }));
}

function fmtDay(d: string) {
  const dt = new Date(d + 'T12:00:00');
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtTime(d: string) {
  const dt = new Date(d);
  return dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────
const ChartTooltip = ({
  active, payload, label, unit, formatLabel,
}: {
  active?: boolean; payload?: { value: number }[]; label?: string; unit: string;
  formatLabel?: (l: string) => string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#1A1D26] border border-[#2A2E3B] rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-[#8A93B2] mb-0.5">{label ? (formatLabel ? formatLabel(label) : fmtDay(label)) : ''}</div>
      <div className="text-white font-mono font-semibold">{payload[0].value} {unit}</div>
    </div>
  );
};

// ─── Mini chart card ──────────────────────────────────────────────────────────
function MetricCard({ title, color, children, badge }: {
  title: string; color: string; children: React.ReactNode; badge?: string;
}) {
  return (
    <div className="bg-[#0A0D14] border border-[#2A2E3B] rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color }}>{title}</span>
        {badge && (
          <span className="text-[10px] font-mono text-[#8A93B2] bg-[#1A1D26] px-2 py-0.5 rounded">{badge}</span>
        )}
      </div>
      {children}
    </div>
  );
}

// ─── Streaming heart rate chart (polls public/data/live_hr.json) ─────────────
const POLL_MS   = 2000;  // match capture script interval
const WINDOW_S  = 60;    // rolling 60-second view

function StreamingHR() {
  const [points, setPoints] = useState<{ ts: number; bpm: number }[]>([]);
  const [live, setLive]     = useState(false);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const res  = await fetch(`/data/live_hr.json?_=${Date.now()}`);
        const data: { ts: number; bpm: number }[] = await res.json();
        if (!Array.isArray(data) || !data.length) return;

        const cutoff = Date.now() - WINDOW_S * 1000;
        const window_ = data.filter(p => p.ts >= cutoff);
        setPoints(window_);

        // Consider "live" if the newest point is <10 s old
        setLive(data[data.length - 1].ts > Date.now() - 10_000);
      } catch {
        // file not ready yet
      }
    };

    fetch_();
    const id = setInterval(fetch_, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const current = points[points.length - 1]?.bpm;
  const vals    = points.map(p => p.bpm);
  const minY    = vals.length ? Math.min(...vals) - 4 : 40;
  const maxY    = vals.length ? Math.max(...vals) + 4 : 120;

  // Build chart-friendly array with a relative time label
  const chartData = points.map(p => ({
    bpm: p.bpm,
    label: new Date(p.ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  }));

  return (
    <div className="bg-[#0A0D14] border border-[#E07070]/20 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium uppercase tracking-wider text-[#E07070]">
            Live Heart Rate
          </span>
          {/* live / offline dot */}
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: live ? '#52D0A0' : '#8A93B2',
              boxShadow: live ? '0 0 4px #52D0A0' : 'none',
            }}
          />
        </div>
        <span className="font-mono text-xs text-[#E07070]/70">
          {current ? `${current} bpm` : live === false && !points.length ? 'run npm run heartrate' : '—'}
        </span>
      </div>

      {chartData.length === 0 ? (
        <div className="flex items-center justify-center h-24 text-[#8A93B2] text-[10px]">
          Waiting for data — run <code className="mx-1 text-[#3ECFCF]">npm run heartrate</code> to start capture
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="hrGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#E07070" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#E07070" stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="label" tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis domain={[minY, maxY]} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} width={28} />
            <Tooltip content={<ChartTooltip unit="bpm" formatLabel={l => l} />} />
            <Area
              type="monotone"
              dataKey="bpm"
              stroke="#E07070"
              strokeWidth={1.5}
              fill="url(#hrGrad)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export const AppleWatchPanel = () => {
  const [hr, setHr] = useState<{ day: string; value: number }[]>([]);
  const [sleep, setSleep] = useState<{ day: string; hours: number; quality: number }[]>([]);
  const [cal, setCal] = useState<{ day: string; value: number }[]>([]);
  const [resp, setResp] = useState<{ day: string; value: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      loadCSV('/data/applewatch/heart_rate.csv'),
      loadCSV('/data/applewatch/sleep.csv'),
      loadCSV('/data/applewatch/calories_active.csv'),
      loadCSV('/data/applewatch/respiratory_rate.csv'),
    ]).then(([hrRows, sleepRows, calRows, respRows]) => {
      setHr(avgByDay(hrRows));
      setSleep(sleepByDay(sleepRows));
      setCal(sumByDay(calRows));
      setResp(avgByDay(respRows));
      setLoading(false);
    });
  }, []);

  const latestHr = hr[hr.length - 1]?.value;
  const latestResp = resp[resp.length - 1]?.value;
  const lastSleep = sleep[sleep.length - 1];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-[#8A93B2] text-xs">
        Loading health data…
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-5"
    >
      {/* Stat strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Heart Rate', value: latestHr ? `${latestHr} bpm` : '—', color: '#E07070' },
          { label: 'Sleep Last Night', value: lastSleep ? `${lastSleep.hours}h` : '—', color: '#7B61FF' },
          { label: 'Sleep Quality', value: lastSleep ? `${lastSleep.quality}%` : '—', color: '#3ECFCF' },
          { label: 'Resp. Rate', value: latestResp ? `${latestResp} /min` : '—', color: '#52D0A0' },
        ].map(s => (
          <div key={s.label} className="bg-[#0A0D14] border border-[#2A2E3B] rounded-xl px-4 py-3 text-center">
            <div className="text-[9px] uppercase tracking-wider text-[#8A93B2] mb-1">{s.label}</div>
            <div className="font-mono text-sm font-semibold" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Streaming heart rate */}
      <StreamingHR />

      {/* Avg HR per day */}
      <MetricCard title="Avg Heart Rate / Day" color="#E07070" badge="bpm">
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={hr}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="day" tickFormatter={fmtDay} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} domain={['auto', 'auto']} width={28} />
            <Tooltip content={<ChartTooltip unit="bpm" />} />
            <Line type="monotone" dataKey="value" stroke="#E07070" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </MetricCard>

      {/* Sleep hours per night */}
      <MetricCard title="Sleep / Night" color="#7B61FF" badge="hours">
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={sleep}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="day" tickFormatter={fmtDay} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} width={24} />
            <Tooltip content={<ChartTooltip unit="hrs" />} />
            <Bar dataKey="hours" fill="#7B61FF" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </MetricCard>

      {/* Sleep quality % */}
      <MetricCard title="Sleep Quality (Deep + REM %)" color="#3ECFCF" badge="%">
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={sleep}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="day" tickFormatter={fmtDay} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} domain={[0, 100]} width={28} />
            <Tooltip content={<ChartTooltip unit="%" />} />
            <Line type="monotone" dataKey="quality" stroke="#3ECFCF" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </MetricCard>

      {/* Active calories per day */}
      <MetricCard title="Active Calories / Day" color="#F4A261" badge="Cal">
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={cal}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="day" tickFormatter={fmtDay} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} width={36} />
            <Tooltip content={<ChartTooltip unit="Cal" />} />
            <Bar dataKey="value" fill="#F4A261" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </MetricCard>

      {/* Respiratory rate per day */}
      <MetricCard title="Respiratory Rate / Day" color="#52D0A0" badge="/min">
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={resp}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A1D26" />
            <XAxis dataKey="day" tickFormatter={fmtDay} tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#8A93B2', fontSize: 9 }} tickLine={false} axisLine={false} domain={['auto', 'auto']} width={28} />
            <Tooltip content={<ChartTooltip unit="/min" />} />
            <Line type="monotone" dataKey="value" stroke="#52D0A0" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </MetricCard>
    </motion.div>
  );
};
