import { useState, useEffect } from 'react';
import {
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import { BarChart2, ExternalLink, RefreshCw, Download, Database, Activity, Users, AlertTriangle } from 'lucide-react';
import client from '../api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Analytics {
  kpis: {
    total_patients: number;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    avg_score: number;
    max_score: number;
    min_score: number;
  };
  risk_distribution: { level: string; count: number; avg_score: number; pct: number }[];
  cohort: { id: string; name: string; gender: string; risk_score: number; risk_level: string; recommendation: string }[];
  biomarker_trends: Record<string, number | string>[];
  risk_trend: { week: string; avg_score: number; readings: number }[];
  trajectory_dist: { trajectory: string; count: number }[];
  score_breakdown: Record<string, number | string>[];
  iris_portal_url: string;
  data_source: string;
}

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------
const RISK_COLORS: Record<string, string> = {
  HIGH: '#ef4444', high: '#ef4444',
  MEDIUM: '#f59e0b', medium: '#f59e0b',
  LOW: '#10b981', low: '#10b981',
};

const BIOMARKER_COLORS: Record<string, string> = {
  hemoglobin:     '#f87171',
  calprotectin:   '#fb923c',
  butyrate:       '#34d399',
  fungal:         '#a78bfa',
  proteobacteria: '#60a5fa',
  methylation:    '#f472b6',
};

function riskBadge(level: string) {
  const l = level.toLowerCase();
  if (l === 'high')   return 'bg-red-500/15 text-red-400 border border-red-500/20';
  if (l === 'medium') return 'bg-amber-500/15 text-amber-400 border border-amber-500/20';
  return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20';
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------
function KpiCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color: string;
}) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500 uppercase tracking-wider">{label}</span>
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center`} style={{ background: `${color}20` }}>
          <Icon className="w-3.5 h-3.5" style={{ color }} />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 text-xs" style={{ background: 'rgba(10,15,30,0.95)', border: '1px solid rgba(255,255,255,0.12)' }}>
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <span className="text-white font-medium">{typeof p.value === 'number' ? p.value.toFixed(p.value < 1 ? 3 : 1) : p.value}</span></p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AnalyticsDashboard() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeBiomarker, setActiveBiomarker] = useState<string>('hemoglobin');
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const r = await client.get<Analytics>('/api/iris/analytics');
      setData(r.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const exportCsv = () => {
    if (!data) return;
    const rows = [
      ['Name', 'Gender', 'Risk Score', 'Risk Level', 'Recommendation'],
      ...data.cohort.map(p => [p.name, p.gender, p.risk_score, p.risk_level, `"${p.recommendation}"`]),
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'iris-analytics.csv'; a.click();
  };

  const refresh = async () => {
    setRefreshing(true);
    await client.post('/api/iris/refresh');
    await load();
    setRefreshing(false);
  };

  // ── Loading / error ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-slate-500">Querying IRIS SQL…</p>
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-red-400">{error || 'No data'}</p>
          <button onClick={load} className="mt-3 text-xs text-slate-400 hover:text-white">Retry</button>
        </div>
      </div>
    );
  }

  const { kpis, risk_distribution, cohort, biomarker_trends, risk_trend } = data;

  // Normalise IRIS uppercase level keys for charts
  const riskDist = risk_distribution.map(r => ({ ...r, level: r.level.toLowerCase() }));

  // Score breakdown for radar — pivot to [{subject, ...patients}]

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart2 className="w-5 h-5 text-violet-400" />
            <h1 className="text-lg font-bold text-white">InterSystems Analytics</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/20 font-medium">
              IRIS SQL
            </span>
          </div>
          <p className="text-xs text-slate-500">{data.data_source}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors"
            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <a
            href={data.iris_portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-violet-300 hover:text-white transition-colors"
            style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.25)' }}
          >
            <ExternalLink className="w-3.5 h-3.5" /> IRIS Portal
          </a>
          <button
            onClick={refresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors disabled:opacity-50"
            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* ── KPIs ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Total Patients" value={kpis.total_patients} icon={Users} color="#60a5fa"
          sub="In IRIS vector store" />
        <KpiCard label="High Risk" value={kpis.high_risk}
          sub={`${((kpis.high_risk / kpis.total_patients) * 100).toFixed(0)}% of cohort`}
          icon={AlertTriangle} color="#ef4444" />
        <KpiCard label="Avg Risk Score" value={kpis.avg_score}
          sub={`Range ${kpis.min_score} – ${kpis.max_score}`}
          icon={Activity} color="#f59e0b" />
        <KpiCard label="IRIS Source" value="SQL Native" sub="sqlalchemy-iris · port 1972"
          icon={Database} color="#a78bfa" />
      </div>

      {/* ── Risk distribution + Risk trend ────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Donut */}
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p className="text-xs text-slate-400 font-medium mb-4 uppercase tracking-wider">Risk Distribution</p>
          <div className="flex items-center gap-4">
            <PieChart width={140} height={140}>
              <Pie data={riskDist} cx={65} cy={65} innerRadius={40} outerRadius={65}
                dataKey="count" paddingAngle={3}>
                {riskDist.map((entry) => (
                  <Cell key={entry.level} fill={RISK_COLORS[entry.level] || '#6b7280'} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
            <div className="flex-1 space-y-2">
              {riskDist.map(r => (
                <div key={r.level} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: RISK_COLORS[r.level] || '#6b7280' }} />
                    <span className="text-xs text-slate-300">{r.level.charAt(0).toUpperCase() + r.level.slice(1)}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-white">{r.count}</span>
                    <span className="text-xs text-slate-500 ml-1">({r.pct}%)</span>
                  </div>
                </div>
              ))}
              <div className="border-t pt-2 mt-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Avg score</span>
                  <span className="text-white font-medium">{kpis.avg_score}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Weekly risk trend */}
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <p className="text-xs text-slate-400 font-medium mb-4 uppercase tracking-wider">Weekly Avg Risk Score (90 days)</p>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={risk_trend} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="week" tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey="avg_score" name="Avg Score"
                stroke="#f59e0b" strokeWidth={2} dot={{ r: 3, fill: '#f59e0b' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Biomarker trend ───────────────────────────────────────────────── */}
      <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">30-Day Biomarker Population Average</p>
          <div className="flex gap-1 flex-wrap">
            {Object.keys(BIOMARKER_COLORS).map(b => (
              <button key={b} onClick={() => setActiveBiomarker(b)}
                className="text-xs px-2 py-0.5 rounded-md transition-all"
                style={{
                  background: activeBiomarker === b ? `${BIOMARKER_COLORS[b]}25` : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${activeBiomarker === b ? BIOMARKER_COLORS[b] : 'rgba(255,255,255,0.08)'}`,
                  color: activeBiomarker === b ? BIOMARKER_COLORS[b] : '#94a3b8',
                }}
              >{b}</button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={biomarker_trends} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false}
              tickFormatter={(v: string) => v.slice(5)} />
            <YAxis tick={{ fill: '#64748b', fontSize: 9 }} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Line type="monotone" dataKey={activeBiomarker} name={activeBiomarker}
              stroke={BIOMARKER_COLORS[activeBiomarker]} strokeWidth={2}
              dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── Cohort table ──────────────────────────────────────────────────── */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Patient Cohort — IRIS Native Store</p>
          <span className="text-xs text-slate-600">{cohort.length} patients</span>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
              {['Name', 'Gender', 'Risk Score', 'Risk Level', 'Recommendation'].map(h => (
                <th key={h} className="px-4 py-2 text-left text-slate-500 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cohort.map((p, i) => (
              <tr key={p.id} style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.04)' : undefined }}>
                <td className="px-4 py-2.5 text-white font-medium">{p.name}</td>
                <td className="px-4 py-2.5 text-slate-400">{p.gender === 'M' ? 'Male' : 'Female'}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full rounded-full"
                        style={{ width: `${p.risk_score}%`, background: RISK_COLORS[p.risk_level] || '#6b7280' }} />
                    </div>
                    <span className="text-white font-mono">{p.risk_score}</span>
                  </div>
                </td>
                <td className="px-4 py-2.5">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${riskBadge(p.risk_level)}`}>
                    {p.risk_level}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-slate-400 max-w-xs truncate">{p.recommendation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-xs text-slate-600 pb-2">
        <span>Powered by InterSystems IRIS SQL Analytics · sqlalchemy-iris · VECTOR(DOUBLE, 1536)</span>
        <a href={data.iris_portal_url} target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-slate-400 transition-colors">
          Open IRIS Management Portal <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
