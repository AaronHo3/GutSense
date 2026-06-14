
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
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

const TRAJECTORY_GLYPH: Record<string, string> = {
  'Rapidly Increasing': '↑↑',
  'Slowly Increasing': '↑',
  'Stable': '→',
  'Improving': '↓',
};

const SIGNAL_GROUPS = [
  {
    label: 'Hidden Blood',
    keys: ['hemoglobin_fit', 'haptoglobin'],
    description: 'Detects microscopic blood in your stool, often the earliest warning sign and invisible to the naked eye.',
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
    description: 'Tracks proteins linked to tissue breakdown. Elevated levels can signal changes in gut cell activity.',
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
const STATUS_COLOR = ['#2F6B4F', '#9A7A24', '#B35C33', '#9E2B25'] as const;

function signalStatus(score: number) {
  const i = score <= 30 ? 0 : score <= 60 ? 1 : score <= 80 ? 2 : 3;
  return { label: STATUS_LABEL[i], color: STATUS_COLOR[i] };
}

function StatCell({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="px-5 py-4 first:pl-0">
      <div className="font-mono tnum" style={{ fontSize: '1.5rem', lineHeight: 1, color: color ?? 'var(--ink)', fontWeight: 500 }}>
        {value}
      </div>
      <div className="eyebrow mt-2">{label}</div>
    </div>
  );
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
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="eyebrow">Loading patient data…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="font-mono" style={{ color: '#9E2B25', fontSize: '0.875rem' }}>{error}</div>
      </div>
    );
  }

  const lastReadingTime = latestRisk
    ? new Date(latestRisk.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'n/a';
  const daysMonitored = readings.length > 0
    ? Math.round((Date.now() - new Date(readings[0].timestamp).getTime()) / 86400000)
    : 0;
  const physRecs = notes.filter(n => n.is_physician_recommendation);
  const levelColor = latestRisk
    ? signalStatus(latestRisk.adjusted_score).color
    : 'var(--ink)';

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10 sm:py-14">

      {/* Masthead */}
      <header className="rise">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="eyebrow">Patient Dashboard</span>
            <h1 className="font-serif text-ink mt-3" style={{ fontSize: 'clamp(2.25rem, 5vw, 3.5rem)', lineHeight: 1, fontWeight: 420, letterSpacing: '-0.02em' }}>
              {patient?.name ?? 'Patient'}
            </h1>
            <p className="font-mono text-muted mt-3" style={{ fontSize: '0.8125rem', letterSpacing: '0.02em' }}>
              {patient && `${patient.age} · ${patient.sex === 'M' ? 'Male' : 'Female'}`}
              {patient?.family_history ? '  ·  Family history of CRC' : ''}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 pt-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: '#2F6B4F' }} />
            <span className="font-mono uppercase text-muted" style={{ fontSize: '0.625rem', letterSpacing: '0.14em' }}>Live</span>
          </div>
        </div>
      </header>

      {/* Stat band */}
      {latestRisk && (
        <div className="mt-8 flex flex-wrap divide-x rise" style={{ borderTop: '1px solid var(--ink)', borderBottom: '1px solid var(--line)', borderColor: 'var(--line)' }}>
          <StatCell label="Risk Score" value={String(Math.round(latestRisk.adjusted_score))} color={levelColor} />
          <StatCell label="Trajectory" value={`${TRAJECTORY_GLYPH[latestRisk.trajectory] ?? '→'} ${latestRisk.trajectory}`} />
          <StatCell label="Last Reading" value={lastReadingTime} />
          <StatCell label="Days Monitored" value={String(daysMonitored)} />
        </div>
      )}

      {/* Alerts */}
      <div className="mt-6">
        <AlertBanner alerts={alerts} onAcknowledge={acknowledge} />
      </div>

      {/* Gauge + AI analysis */}
      {latestRisk && (
        <section className="mt-8 grid grid-cols-1 lg:grid-cols-[minmax(0,300px)_1fr] gap-6 items-stretch rise" style={{ animationDelay: '0.08s' }}>
          <div className="card flex items-center justify-center py-10">
            <RiskScore
              score={latestRisk.adjusted_score}
              level={latestRisk.risk_level}
              trajectory={latestRisk.trajectory}
            />
          </div>
          <ReportPanel risk={latestRisk} mode="patient" />
        </section>
      )}

      {/* Physician recommendations */}
      {physRecs.length > 0 && (
        <div className="mt-6">
          <ClinicalNotes notes={physRecs} allowAdd={false} />
        </div>
      )}

      {/* Health Signals */}
      {latestRisk?.score_breakdown && (
        <section className="mt-14">
          <div className="flex items-baseline justify-between pb-3" style={{ borderBottom: '1px solid var(--ink)' }}>
            <h2 className="font-serif text-ink" style={{ fontSize: '1.5rem', fontWeight: 420 }}>Your Health Signals</h2>
            <span className="eyebrow hidden sm:block">What your latest test detected</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-6">
            {SIGNAL_GROUPS.map(group => {
              const maxScore = Math.max(...group.keys.map(k => (latestRisk.score_breakdown as Record<string, number>)[k] ?? 0));
              const { label, color } = signalStatus(maxScore);
              const chartMarkers = MARKERS.filter(m => group.chartKeys.includes(m.key as string));
              return (
                <div key={group.label} className="card overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-serif text-ink" style={{ fontSize: '1.125rem', fontWeight: 440 }}>{group.label}</div>
                      <span className="font-mono uppercase" style={{ fontSize: '0.625rem', letterSpacing: '0.1em', color }}>{label}</span>
                    </div>
                    <p className="text-muted" style={{ fontSize: '0.875rem', lineHeight: 1.5 }}>{group.description}</p>
                    <div className="mt-4 h-px w-full" style={{ background: 'var(--line)' }}>
                      <div className="h-px transition-all duration-700" style={{ width: `${maxScore}%`, background: color }} />
                    </div>
                  </div>
                  <details className="group/detail">
                    <summary className="flex items-center justify-between px-5 py-2.5 cursor-pointer eyebrow hover:text-ink transition-colors" style={{ borderTop: '1px solid var(--line)' }}>
                      <span>View 90-day trends</span>
                      <span className="group-open/detail:rotate-180 transition-transform">▾</span>
                    </summary>
                    <div className="px-5 pb-5 pt-1 space-y-4">
                      <p className="text-faint" style={{ fontSize: '0.8125rem', lineHeight: 1.5 }}>{group.chartDescription}</p>
                      {chartMarkers.map(marker => (
                        <BiomarkerChart key={marker.key} readings={readings} marker={marker} />
                      ))}
                    </div>
                  </details>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Lifestyle context (collapsible) */}
      <details className="group mt-10">
        <summary className="eyebrow cursor-pointer flex items-center gap-2 pb-3 hover:text-ink transition-colors" style={{ borderBottom: '1px solid var(--line)' }}>
          <span>Lifestyle Context</span>
          <span className="group-open:rotate-90 transition-transform inline-block">›</span>
        </summary>
        <div className="mt-5">
          <LifestyleInputPanel patientId={patientId} />
        </div>
      </details>
    </div>
  );
}
