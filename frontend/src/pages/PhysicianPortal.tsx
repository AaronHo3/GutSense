
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, RefreshCw, Zap, Users, AlertTriangle } from 'lucide-react';
import { api } from '../api/endpoints';
import type { PatientSummary } from '../types';

const LEVEL_STYLES = {
  green:  { border: 'border-l-emerald-400', badge: 'bg-emerald-500/15 text-emerald-400',  label: 'Low',      dot: 'bg-emerald-400' },
  yellow: { border: 'border-l-yellow-400',  badge: 'bg-yellow-500/15 text-yellow-400',   label: 'Elevated',  dot: 'bg-yellow-400' },
  orange: { border: 'border-l-orange-400',  badge: 'bg-orange-500/15 text-orange-400',   label: 'High',      dot: 'bg-orange-400' },
  red:    { border: 'border-l-red-500',     badge: 'bg-red-500/15 text-red-400',         label: 'Critical',  dot: 'bg-red-500' },
};

function getInitials(name: string) {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
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

  // Summary stats
  const totalCritical = roster.filter(r => r.latest_risk?.risk_level === 'red').length;
  const totalElevated = roster.filter(r => ['yellow', 'orange'].includes(r.latest_risk?.risk_level ?? '')).length;
  const totalAlerts = roster.reduce((sum, r) => sum + r.unacknowledged_alerts, 0);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-base font-bold text-white">Physician Dashboard</h1>
          <p className="text-xs text-slate-400">Patients sorted by risk · auto-refreshes every 10s</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition px-3 py-1.5 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </div>

      {/* Stats row */}
      {!loading && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold text-white tabular-nums">{roster.length}</div>
            <div className="text-xs text-slate-500 flex items-center justify-center gap-1 mt-0.5">
              <Users className="w-3 h-3" />Patients
            </div>
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold text-red-400 tabular-nums">{totalCritical}</div>
            <div className="text-xs text-slate-500 mt-0.5">Critical</div>
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold text-yellow-400 tabular-nums">{totalElevated}</div>
            <div className="text-xs text-slate-500 mt-0.5">Elevated</div>
          </div>
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-2xl font-bold text-orange-400 tabular-nums">{totalAlerts}</div>
            <div className="text-xs text-slate-500 flex items-center justify-center gap-1 mt-0.5">
              <AlertTriangle className="w-3 h-3" />Alerts
            </div>
          </div>
        </div>
      )}

      {/* Patient list */}
      {loading ? (
        <div className="text-center text-slate-400 text-sm py-12">Loading patient roster...</div>
      ) : (
        <div className="space-y-2.5">
          {roster.map(({ patient, latest_risk, unacknowledged_alerts, latest_reading }) => {
            const level = (latest_risk?.risk_level ?? 'green') as keyof typeof LEVEL_STYLES;
            const styles = LEVEL_STYLES[level];

            return (
              <div
                key={patient.id}
                onClick={() => navigate(`/physician/patient/${patient.id}`)}
                className={`rounded-2xl border-l-4 ${styles.border} p-4 cursor-pointer transition-all`}
                style={{ background: 'rgba(255,255,255,0.05)', borderTopColor: 'rgba(255,255,255,0.08)', borderRightColor: 'rgba(255,255,255,0.08)', borderBottomColor: 'rgba(255,255,255,0.08)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              >
                <div className="flex items-center gap-3">
                  {/* Avatar */}
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0 ${styles.dot}`}>
                    {getInitials(patient.name)}
                  </div>

                  {/* Patient info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-white text-sm truncate">{patient.name}</h3>
                      {unacknowledged_alerts > 0 && (
                        <span className="flex items-center gap-0.5 text-xs text-red-400 font-medium flex-shrink-0">
                          <AlertCircle className="w-3 h-3" />
                          {unacknowledged_alerts}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">
                      {patient.age}{patient.sex}
                      {patient.family_history && ' · Family Hx ⚠'}
                      {patient.has_nod2_variant && ' · NOD2+'}
                    </p>
                    {latest_risk && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        {latest_risk.trajectory} · {new Date(latest_risk.timestamp).toLocaleString()}
                      </p>
                    )}
                  </div>

                  {/* Score */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white tabular-nums">
                        {latest_risk ? Math.round(latest_risk.adjusted_score) : '—'}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles.badge}`}>
                        {styles.label}
                      </span>
                    </div>
                    <button
                      onClick={e => handleSpike(e, patient.id)}
                      disabled={spiking === patient.id}
                      title="Simulate a high-risk reading (demo)"
                      className="p-2 rounded-lg hover:text-orange-400 text-slate-500 transition disabled:opacity-50"
                      style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}
                    >
                      {spiking === patient.id
                        ? <RefreshCw className="w-4 h-4 animate-spin" />
                        : <Zap className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Mini biomarker summary */}
                {latest_reading && (
                  <div className="mt-2.5 pt-2 flex gap-3 text-xs text-slate-500 flex-wrap" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <span>Hgb: <span className="text-slate-300 font-medium">{latest_reading.hemoglobin_ng_ml.toFixed(0)}</span> ng/mL</span>
                    <span>But: <span className="text-slate-300 font-medium">{latest_reading.butyrate_mmol_kg.toFixed(1)}</span> mmol/kg</span>
                    <span>Cal: <span className="text-slate-300 font-medium">{latest_reading.calprotectin_ug_g.toFixed(0)}</span> µg/g</span>
                    <span>Meth: <span className="text-slate-300 font-medium">{latest_reading.methylation_score.toFixed(3)}</span></span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
