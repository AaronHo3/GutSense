
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Activity, Clock, CalendarDays, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const TRAJECTORY_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  'Rapidly Increasing': { icon: <TrendingUp className="w-3 h-3" />, color: '#f87171', label: 'Rising fast' },
  'Slowly Increasing':  { icon: <TrendingUp className="w-3 h-3" />, color: '#fbbf24', label: 'Trending up' },
  'Stable':             { icon: <Minus className="w-3 h-3" />,       color: '#94a3b8', label: 'No change' },
  'Improving':          { icon: <TrendingDown className="w-3 h-3" />, color: '#34d399', label: 'Improving' },
};
import { BiomarkerChart, MARKERS } from '../components/BiomarkerChart';
import { usePatientData } from '../hooks/usePatientData';
import { useAlerts } from '../hooks/useAlerts';
import { RiskScore } from '../components/RiskScore';
import { AlertBanner } from '../components/AlertBanner';
import { LifestyleInputPanel } from '../components/LifestyleInputPanel';
import { ReportPanel } from '../components/ReportPanel';
import { ClinicalNotes } from '../components/ClinicalNotes';
import { api } from '../api/endpoints';
import type { Patient, ClinicalNote } from '../types';

const SIGNAL_GROUPS = [
  {
    label: 'Hidden Blood',
    keys: ['hemoglobin_fit', 'haptoglobin'],
    description: 'Detects microscopic blood in your stool — often the earliest warning sign, invisible to the naked eye.',
    chartKeys: ['hemoglobin_fit_ng_ml', 'haptoglobin_ug_g'],
    chartDescription: 'These charts show how blood-related markers have changed over time. Spikes may indicate small amounts of bleeding in the gut.',
  },
  {
    label: 'Gut Inflammation',
    keys: ['calprotectin', 'mpo'],
    description: 'Measures irritation and immune activity in your intestinal lining.',
    chartKeys: ['calprotectin_ug_g', 'mpo_ng_ml'],
    chartDescription: 'These charts track immune cell activity in your gut lining over time. Sustained elevation can mean your gut is under ongoing stress.',
  },
  {
    label: 'Tissue Health',
    keys: ['mmp9', 'mmp8'],
    description: 'Tracks proteins linked to tissue breakdown — elevated levels can signal changes in gut cell activity.',
    chartKeys: ['mmp9_ng_ml', 'mmp8_ng_ml'],
    chartDescription: 'These proteins help the body repair tissue. When persistently high, they can indicate that the gut lining is being broken down faster than normal.',
  },
  {
    label: 'Inflammatory Response',
    keys: ['fibrinogen', 'pgrp_s'],
    description: "Reflects your body's overall inflammatory response in the gut.",
    chartKeys: ['fibrinogen_ng_ml', 'pgrp_s_ng_ml'],
    chartDescription: 'These markers reflect how actively your immune system is responding. Elevated readings over time may point to ongoing gut irritation.',
  },
];

const STATUS_LABEL = ['Normal', 'Slightly Elevated', 'Elevated', 'High'] as const;
const STATUS_COLOR = ['#34d399', '#fbbf24', '#fb923c', '#f87171'] as const;

function signalStatus(score: number) {
  const i = score <= 30 ? 0 : score <= 60 ? 1 : score <= 80 ? 2 : 3;
  return { label: STATUS_LABEL[i], color: STATUS_COLOR[i] };
}

export function PatientDashboard() {
  const { patientId: paramId } = useParams<{ patientId: string }>();
  const patientId = Number(paramId ?? 1);

  const { readings, latestRisk, loading, error } = usePatientData(patientId, 10000);
  const { alerts, acknowledge } = useAlerts(patientId, 10000);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);

  useEffect(() => {
    api.getPatient(patientId).then(setPatient).catch(() => {});
    api.getNotes(patientId).then(setNotes).catch(() => {});
    const t = setInterval(() => api.getNotes(patientId).then(setNotes).catch(() => {}), 10000);
    return () => clearInterval(t);
  }, [patientId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading patient data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-500 text-sm">{error}</div>
      </div>
    );
  }

  const lastReadingTime = latestRisk
    ? new Date(latestRisk.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—';
  const daysMonitored = readings.length > 0
    ? Math.round((Date.now() - new Date(readings[0].timestamp).getTime()) / 86400000)
    : 0;
  const physRecs = notes.filter(n => n.is_physician_recommendation);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-500/20 border border-blue-400/30 flex items-center justify-center shadow-sm">
            <span className="text-blue-300 font-bold text-sm">
              {patient?.name?.charAt(0) ?? '?'}
            </span>
          </div>
          <div>
            <h1 className="text-base font-bold text-white">{patient?.name ?? 'Patient'}</h1>
            <p className="text-xs text-slate-400">
              {patient && `${patient.age}${patient.sex}`}{patient?.family_history ? ' · Family Hx ⚠' : ''} · Gut Health Dashboard
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full font-medium">
          <Activity className="w-3 h-3" />
          Live
        </div>
      </div>

      {/* Stats strip */}
      {latestRisk && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold tabular-nums" style={{ color: latestRisk.risk_level === 'green' ? '#34d399' : latestRisk.risk_level === 'yellow' ? '#fbbf24' : latestRisk.risk_level === 'orange' ? '#fb923c' : '#f87171' }}>
              {Math.round(latestRisk.adjusted_score)}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">Risk Score</div>
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            {(() => { const t = TRAJECTORY_META[latestRisk.trajectory] ?? TRAJECTORY_META['Stable']; return (
              <>
                <div className="text-sm font-semibold flex items-center justify-center gap-1 truncate" style={{ color: t.color }}>
                  {t.icon}{latestRisk.trajectory}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">{t.label}</div>
              </>
            ); })()}
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-xs font-semibold text-white truncate">{lastReadingTime}</div>
            <div className="text-xs text-slate-500 mt-0.5 flex items-center justify-center gap-1">
              <Clock className="w-3 h-3" />Last Reading
            </div>
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold text-white tabular-nums">{daysMonitored}</div>
            <div className="text-xs text-slate-500 mt-0.5 flex items-center justify-center gap-1">
              <CalendarDays className="w-3 h-3" />Days Monitored
            </div>
          </div>
        </div>
      )}

      {/* Alerts */}
      <AlertBanner alerts={alerts} onAcknowledge={acknowledge} />

      {/* Risk score + AI analysis */}
      {latestRisk && (
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          <div className="flex-shrink-0 flex justify-center w-full sm:w-auto">
            <RiskScore
              score={latestRisk.adjusted_score}
              level={latestRisk.risk_level}
              trajectory={latestRisk.trajectory}
            />
          </div>
          <div className="flex-1 self-stretch">
            <ReportPanel risk={latestRisk} mode="patient" />
          </div>
        </div>
      )}

      {/* Physician recommendations */}
      {physRecs.length > 0 && (
        <ClinicalNotes notes={physRecs} allowAdd={false} />
      )}

      {/* Health Signals */}
      {latestRisk?.score_breakdown && (
        <div>
          <div className="mb-3 pb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Your Health Signals</h2>
            <p className="text-xs text-slate-500 mt-0.5">Plain-language summary of what your latest test detected.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SIGNAL_GROUPS.map(group => {
              const maxScore = Math.max(...group.keys.map(k => (latestRisk.score_breakdown as Record<string, number>)[k] ?? 0));
              const { label, color } = signalStatus(maxScore);
              const chartMarkers = MARKERS.filter(m => group.chartKeys.includes(m.key));
              return (
                <div key={group.label} className="rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="font-semibold text-sm text-white">{group.label}</div>
                      <div className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ color, background: color + '22' }}>{label}</div>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">{group.description}</p>
                    <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${maxScore}%`, background: color }} />
                    </div>
                  </div>
                  <details className="group/detail">
                    <summary className="flex items-center justify-between px-4 py-2 cursor-pointer text-xs text-slate-500 hover:text-slate-300 transition-colors select-none" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <span>View 90-day trends</span>
                      <span className="group-open/detail:rotate-180 transition-transform">▾</span>
                    </summary>
                    <div className="px-4 pb-4 pt-2 space-y-3">
                      <p className="text-xs text-slate-500 leading-relaxed">{group.chartDescription}</p>
                      {chartMarkers.map(marker => (
                        <BiomarkerChart key={marker.key} readings={readings} marker={marker} />
                      ))}
                    </div>
                  </details>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Lifestyle context — collapsible */}
      <details className="group">
        <summary className="text-xs font-semibold text-slate-400 uppercase tracking-wide cursor-pointer list-none flex items-center gap-2 pb-2 hover:text-slate-200 transition-colors" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <span>Lifestyle Context</span>
          <span className="text-slate-500 group-open:rotate-90 transition-transform inline-block">›</span>
        </summary>
        <div className="mt-3">
          <LifestyleInputPanel patientId={patientId} />
        </div>
      </details>
    </div>
  );
}
