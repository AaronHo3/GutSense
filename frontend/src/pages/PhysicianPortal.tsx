
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Zap } from 'lucide-react';
import { api } from '../api/endpoints';
import type { PatientSummary } from '../types';

const LEVEL_META = {
  green:  { color: '#2F6B4F', label: 'Low' },
  yellow: { color: '#9A7A24', label: 'Elevated' },
  orange: { color: '#B35C33', label: 'High' },
  red:    { color: '#9E2B25', label: 'Critical' },
};

function StatCell({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="px-5 py-4 first:pl-0">
      <div className="font-mono tnum" style={{ fontSize: '1.5rem', lineHeight: 1, color: color ?? 'var(--ink)', fontWeight: 500 }}>
        {value}
      </div>
      <div className="eyebrow mt-2">{label}</div>
    </div>
  );
}

export function PhysicianPortal() {
  const [roster, setRoster] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [spiking, setSpiking] = useState<number | null>(null);
  const navigate = useNavigate();

  const load = () => {
    api.getPhysicianRoster().then(r => {
      setRoster(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const handleSpike = async (e: React.MouseEvent, patientId: number) => {
    e.stopPropagation();
    setSpiking(patientId);
    await api.simulateSpike(patientId);
    setTimeout(() => { load(); setSpiking(null); }, 1500);
  };

  const totalCritical = roster.filter(r => r.latest_risk?.risk_level === 'red').length;
  const totalElevated = roster.filter(r => ['yellow', 'orange'].includes(r.latest_risk?.risk_level ?? '')).length;
  const totalAlerts = roster.reduce((sum, r) => sum + r.unacknowledged_alerts, 0);

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10 sm:py-14">

      {/* Masthead */}
      <header className="rise flex items-end justify-between gap-4">
        <div>
          <span className="eyebrow">Physician Dashboard</span>
          <h1 className="font-serif text-ink mt-3" style={{ fontSize: 'clamp(2.25rem, 5vw, 3.5rem)', lineHeight: 1, fontWeight: 420, letterSpacing: '-0.02em' }}>
            Patient Roster
          </h1>
          <p className="font-mono text-muted mt-3" style={{ fontSize: '0.8125rem' }}>
            Ranked by risk · refreshes every 10s
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 font-mono uppercase text-muted hover:text-ink transition px-3 py-2"
          style={{ fontSize: '0.6875rem', letterSpacing: '0.08em', border: '1px solid var(--line2)', borderRadius: 4 }}
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </header>

      {/* Stat band */}
      {!loading && (
        <div className="mt-8 flex flex-wrap divide-x rise" style={{ borderTop: '1px solid var(--ink)', borderBottom: '1px solid var(--line)', borderColor: 'var(--line)' }}>
          <StatCell label="Patients" value={roster.length} />
          <StatCell label="Critical" value={totalCritical} color="#9E2B25" />
          <StatCell label="Elevated" value={totalElevated} color="#9A7A24" />
          <StatCell label="Open Alerts" value={totalAlerts} />
        </div>
      )}

      {/* Roster ledger */}
      {loading ? (
        <div className="text-center eyebrow py-16">Loading patient roster…</div>
      ) : (
        <div className="mt-8">
          {roster.map(({ patient, latest_risk, unacknowledged_alerts, latest_reading }, idx) => {
            const level = (latest_risk?.risk_level ?? 'green') as keyof typeof LEVEL_META;
            const meta = LEVEL_META[level];
            return (
              <div
                key={patient.id}
                onClick={() => navigate(`/physician/patient/${patient.id}`)}
                className="group grid grid-cols-[auto_1fr_auto] sm:grid-cols-[auto_1fr_auto_auto] gap-4 sm:gap-6 items-center py-4 cursor-pointer transition-colors"
                style={{ borderTop: '1px solid var(--line)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(27,26,23,0.025)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {/* Rank */}
                <span className="font-mono tnum text-faint pl-1" style={{ fontSize: '0.75rem', width: 22 }}>
                  {String(idx + 1).padStart(2, '0')}
                </span>

                {/* Name + meta */}
                <div className="min-w-0">
                  <div className="flex items-center gap-2.5">
                    <h3 className="font-serif text-ink truncate" style={{ fontSize: '1.1875rem', fontWeight: 440 }}>{patient.name}</h3>
                    {unacknowledged_alerts > 0 && (
                      <span className="font-mono flex-shrink-0" style={{ fontSize: '0.625rem', color: '#9E2B25' }}>
                        ● {unacknowledged_alerts}
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-faint mt-1 truncate" style={{ fontSize: '0.6875rem', letterSpacing: '0.02em' }}>
                    {patient.age} · {patient.sex}
                    {patient.family_history && ' · Family Hx'}
                    {patient.has_nod2_variant && ' · NOD2+'}
                    {latest_reading && `  ·  Hgb ${latest_reading.hemoglobin_fit_ng_ml.toFixed(0)} · MPO ${latest_reading.mpo_ng_ml.toFixed(0)} · Cal ${latest_reading.calprotectin_ug_g.toFixed(0)}`}
                  </p>
                </div>

                {/* Score */}
                <div className="flex items-baseline gap-2 justify-end">
                  <span className="font-serif tnum" style={{ fontSize: '1.875rem', lineHeight: 1, color: meta.color, fontWeight: 460 }}>
                    {latest_risk ? Math.round(latest_risk.adjusted_score) : 'n/a'}
                  </span>
                  <span className="font-mono uppercase hidden sm:inline" style={{ fontSize: '0.625rem', letterSpacing: '0.1em', color: meta.color, width: 56 }}>
                    {meta.label}
                  </span>
                </div>

                {/* Spike action */}
                <button
                  onClick={e => handleSpike(e, patient.id)}
                  disabled={spiking === patient.id}
                  title="Simulate a high-risk reading (demo)"
                  className="hidden sm:flex items-center justify-center p-2 text-faint hover:text-ink transition disabled:opacity-40"
                  style={{ border: '1px solid var(--line)', borderRadius: 4 }}
                >
                  {spiking === patient.id
                    ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    : <Zap className="w-3.5 h-3.5" />}
                </button>
              </div>
            );
          })}
          <div style={{ borderTop: '1px solid var(--line)' }} />
        </div>
      )}
    </div>
  );
}
