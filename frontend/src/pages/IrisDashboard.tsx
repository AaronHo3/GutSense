import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Wifi,
  WifiOff,
  FlaskConical,
  Stethoscope,
  Download,
  Sparkles,
  Users,
} from 'lucide-react';
import { api } from '../api/endpoints';
import type { IrisPatientSummary, IrisPatientDetail, IrisStatus } from '../types';

// ---------------------------------------------------------------------------
// Risk colour helpers
// ---------------------------------------------------------------------------
function riskColor(level: string) {
  switch (level) {
    case 'high':   return { badge: 'bg-red-500/15 text-red-400 border border-red-500/20', dot: '#f87171', bar: '#ef4444' };
    case 'medium': return { badge: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20', dot: '#fbbf24', bar: '#f59e0b' };
    default:       return { badge: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20', dot: '#34d399', bar: '#10b981' };
  }
}

function RiskBar({ score }: { score: number }) {
  const color = score >= 60 ? '#ef4444' : score >= 30 ? '#f59e0b' : '#10b981';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
        <div
          className="h-1.5 rounded-full transition-all"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-xs font-mono text-slate-400 w-8 text-right">{score}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Observation row
// ---------------------------------------------------------------------------
function ObsRow({ obs }: { obs: IrisPatientDetail['observations'][number] }) {
  const isAbnormal = obs.interpretation && ['H','HH','L','LL','A','AA','POS','R'].includes(obs.interpretation);
  return (
    <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
      <div className="flex-1 min-w-0">
        <span className="text-xs text-slate-300 truncate block">{obs.display}</span>
        {obs.date && <span className="text-xs text-slate-600">{obs.date}</span>}
      </div>
      <div className="flex items-center gap-2 ml-4">
        {obs.value && (
          <span className="text-xs text-slate-300">
            {obs.value} {obs.unit || ''}
          </span>
        )}
        {obs.is_high_weight && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 font-medium">★</span>
        )}
        {obs.interpretation && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded font-mono ${
              isAbnormal
                ? 'bg-red-500/15 text-red-400'
                : 'bg-emerald-500/15 text-emerald-400'
            }`}
          >
            {obs.interpretation}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Patient detail drawer
// ---------------------------------------------------------------------------
function PatientDrawer({
  fhirId,
  onClose,
}: {
  fhirId: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<IrisPatientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'summary' | 'observations' | 'reports'>('summary');

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getIrisPatient(fhirId)
      .then(setDetail)
      .catch((e: unknown) => setError(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to load patient detail'
      ))
      .finally(() => setLoading(false));
  }, [fhirId]);

  const colors = detail ? riskColor(detail.risk_level) : riskColor('low');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl flex flex-col"
        style={{
          background: 'linear-gradient(135deg, #0d1b3e 0%, #0a1628 100%)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
          {loading ? (
            <div className="h-5 w-48 rounded bg-white/10 animate-pulse" />
          ) : detail ? (
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-white font-semibold text-lg">{detail.name}</h2>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors.badge}`}>
                    {detail.risk_level.toUpperCase()} RISK
                  </span>
                </div>
                <p className="text-slate-500 text-sm mt-0.5">
                  {[detail.gender, detail.age ? `Age ${detail.age}` : null]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-white">{detail.risk_score}</p>
                <p className="text-xs text-slate-500">risk score</p>
              </div>
            </div>
          ) : null}

          {/* Tabs */}
          {!loading && detail && (
            <div className="flex gap-1 mt-4 p-1 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)' }}>
              {(['summary', 'observations', 'reports'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                    tab === t ? 'bg-white/15 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {t}
                  {t === 'observations' && detail.observations.length > 0 && (
                    <span className="ml-1 text-slate-600">({detail.observations.length})</span>
                  )}
                  {t === 'reports' && detail.reports.length > 0 && (
                    <span className="ml-1 text-slate-600">({detail.reports.length})</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Body */}
        <div className="p-5 flex-1">
          {loading && (
            <div className="space-y-3">
              {[120, 80, 96].map(w => (
                <div key={w} className="h-4 rounded animate-pulse" style={{ width: `${w}%`, background: 'rgba(255,255,255,0.08)' }} />
              ))}
            </div>
          )}
          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}
          {detail && !loading && (
            <>
              {tab === 'summary' && (
                <div className="space-y-4">

                  {/* RAG summary (IRIS Vector Search) */}
                  {detail.rag_summary ? (
                    <div
                      className="p-3 rounded-lg"
                      style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}
                    >
                      <div className="flex items-center gap-1.5 mb-2">
                        <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                        <p className="text-xs text-violet-400 font-medium">
                          IRIS Vector Search
                        </p>
                      </div>
                      <p className="text-sm text-slate-300 leading-relaxed">{detail.rag_summary}</p>
                    </div>
                  ) : (
                    <p className="text-slate-300 text-sm leading-relaxed">{detail.summary}</p>
                  )}

                  {/* Key findings */}
                  {detail.key_findings.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Key Findings</p>
                      <ul className="space-y-1.5">
                        {detail.key_findings.map((f, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm">
                            <span className="mt-0.5 text-yellow-400 flex-shrink-0">•</span>
                            <span className="text-slate-300">{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommendation */}
                  {detail.recommendation && (
                    <div
                      className="p-3 rounded-lg"
                      style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)' }}
                    >
                      <p className="text-xs text-blue-400 font-medium mb-1">Recommendation</p>
                      <p className="text-sm text-slate-300">{detail.recommendation}</p>
                    </div>
                  )}

                  {/* Similar cases from IRIS Vector Search */}
                  {detail.similar_cases && detail.similar_cases.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1.5 mb-2">
                        <Users className="w-3.5 h-3.5 text-slate-500" />
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Similar Cases — IRIS Vector Search</p>
                      </div>
                      <div className="space-y-2">
                        {detail.similar_cases.map((c, i) => {
                          const col = riskColor(c.risk_level);
                          return (
                            <div
                              key={i}
                              className="flex items-center justify-between p-2.5 rounded-lg"
                              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
                            >
                              <div className="flex-1 min-w-0">
                                <p className="text-sm text-white font-medium truncate">{c.patient_name}</p>
                                <p className="text-xs text-slate-500 truncate mt-0.5">{c.summary.slice(0, 80)}</p>
                              </div>
                              <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                                <span className={`text-xs px-1.5 py-0.5 rounded ${col.badge}`}>{c.risk_level}</span>
                                <span className="text-xs text-slate-400 font-mono">{c.risk_score}</span>
                                <span className="text-xs text-slate-500">{(c.similarity * 100).toFixed(0)}%</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Stats + FHIR download */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="p-2.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)' }}>
                      <p className="text-xs text-slate-500 mb-1">Observations</p>
                      <p className="text-white font-semibold">{detail.observations_count}</p>
                    </div>
                    <div className="p-2.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)' }}>
                      <p className="text-xs text-slate-500 mb-1">Reports</p>
                      <p className="text-white font-semibold">{detail.diagnostic_reports_count}</p>
                    </div>
                    {detail.fhir_bundle_id && (
                      <a
                        href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/iris/patients/${detail.fhir_id}/fhir`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2.5 rounded-lg flex flex-col items-center justify-center gap-1 transition-colors"
                        style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}
                      >
                        <Download className="w-3.5 h-3.5 text-emerald-400" />
                        <p className="text-xs text-emerald-400 font-medium">FHIR R4</p>
                      </a>
                    )}
                  </div>
                </div>
              )}

              {tab === 'observations' && (
                <div>
                  {detail.observations.length === 0 ? (
                    <p className="text-slate-500 text-sm">No observations found.</p>
                  ) : (
                    <div>
                      {detail.observations.map((obs, i) => (
                        <ObsRow key={i} obs={obs} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {tab === 'reports' && (
                <div className="space-y-3">
                  {detail.reports.length === 0 ? (
                    <p className="text-slate-500 text-sm">No diagnostic reports found.</p>
                  ) : (
                    detail.reports.map((r, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-lg"
                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-white font-medium">{r.code || 'Diagnostic Report'}</span>
                          <span className="text-xs text-slate-500">{r.date || '—'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              r.status === 'final'
                                ? 'bg-emerald-500/15 text-emerald-400'
                                : 'bg-yellow-500/15 text-yellow-400'
                            }`}
                          >
                            {r.status || 'unknown'}
                          </span>
                        </div>
                        {r.conclusion && (
                          <p className="text-xs text-slate-400 mt-2 leading-relaxed">{r.conclusion}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <div className="p-4 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <button
            onClick={onClose}
            className="w-full py-2 rounded-lg text-sm text-slate-400 hover:text-white transition-colors"
            style={{ background: 'rgba(255,255,255,0.06)' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Patient card
// ---------------------------------------------------------------------------
function PatientCard({
  patient,
  rank,
  onClick,
}: {
  patient: IrisPatientSummary;
  rank: number;
  onClick: () => void;
}) {
  const colors = riskColor(patient.risk_level);
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="p-4 rounded-xl cursor-pointer transition-all"
      style={{
        background: hovered ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
      }}
    >
      <div className="flex items-start gap-3">
        {/* Rank */}
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
          style={{ background: 'rgba(255,255,255,0.06)', color: colors.dot }}
        >
          {rank}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-white font-medium text-sm truncate">{patient.name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${colors.badge}`}>
              {patient.risk_level.toUpperCase()}
            </span>
          </div>

          <div className="text-xs text-slate-500 mb-2">
            {[patient.gender, patient.age ? `Age ${patient.age}` : null]
              .filter(Boolean)
              .join(' · ')}
          </div>

          <RiskBar score={patient.risk_score} />

          {patient.key_findings.length > 0 && (
            <p className="text-xs text-slate-500 mt-2 truncate">
              {patient.key_findings[0]}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1 text-slate-600 flex-shrink-0">
          <FlaskConical className="w-3.5 h-3.5" />
          <span className="text-xs">{patient.observations_count}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main dashboard
// ---------------------------------------------------------------------------
export function IrisDashboard() {
  const [status, setStatus] = useState<IrisStatus | null>(null);
  const [patients, setPatients] = useState<IrisPatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const load = useCallback(async (forceRefresh = false) => {
    if (forceRefresh) {
      setRefreshing(true);
      await api.refreshIrisCache().catch(() => {});
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const [st, res] = await Promise.all([
        api.getIrisStatus(),
        api.getIrisPatients(),
      ]);
      setStatus(st);
      setPatients(res.patients || []);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to load IRIS data. Is the IRIS Docker container running?';
      setError(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = patients.filter(
    p => filter === 'all' || p.risk_level === filter
  );

  const counts = {
    high:   patients.filter(p => p.risk_level === 'high').length,
    medium: patients.filter(p => p.risk_level === 'medium').length,
    low:    patients.filter(p => p.risk_level === 'low').length,
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-8 h-8 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Stethoscope className="w-4 h-4 text-violet-400" />
            </div>
            <h1 className="text-white font-bold text-xl">IRIS Vector Search</h1>
          </div>
          <p className="text-slate-500 text-sm">
            Patient biomarkers stored in IRIS · vector similarity · AI-ranked by risk
          </p>
        </div>

        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white transition-colors"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Connection status */}
      {status && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg mb-5 text-sm"
          style={{
            background: status.connected
              ? 'rgba(16,185,129,0.08)'
              : 'rgba(239,68,68,0.08)',
            border: `1px solid ${status.connected ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}
        >
          {status.connected ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-400" />
          )}
          <span className={status.connected ? 'text-emerald-400' : 'text-red-400'}>
            {status.message}
          </span>
          {status.connected && status.langchain_rag && (
            <span className="ml-auto flex items-center gap-1 text-xs text-violet-400">
              <Sparkles className="w-3 h-3" />
              IRIS Vector Search
            </span>
          )}
        </div>
      )}

      {/* Stats strip */}
      {!loading && patients.length > 0 && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Total',  value: patients.length,  icon: Activity,      color: 'text-white' },
            { label: 'High',   value: counts.high,       icon: AlertTriangle, color: 'text-red-400' },
            { label: 'Medium', value: counts.medium,     icon: Clock,         color: 'text-yellow-400' },
            { label: 'Low',    value: counts.low,        icon: CheckCircle,   color: 'text-emerald-400' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="p-3 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <Icon className={`w-4 h-4 ${color} mb-1`} />
              <p className={`text-xl font-bold ${color}`}>{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      {!loading && patients.length > 0 && (
        <div className="flex gap-1 p-1 rounded-lg mb-4" style={{ background: 'rgba(255,255,255,0.05)' }}>
          {(['all', 'high', 'medium', 'low'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                filter === f ? 'bg-white/15 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {f === 'all' ? `All (${patients.length})` : `${f} (${counts[f]})`}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div
              key={i}
              className="h-24 rounded-xl animate-pulse"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          ))}
        </div>
      )}

      {error && !loading && (
        <div
          className="p-5 rounded-xl text-center"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}
        >
          <WifiOff className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-red-400 font-medium mb-1">Could not connect to IRIS</p>
          <p className="text-slate-500 text-sm">{error}</p>
          <button
            onClick={() => load()}
            className="mt-4 px-4 py-2 rounded-lg text-sm text-white"
            style={{ background: 'rgba(239,68,68,0.2)' }}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div
          className="p-8 rounded-xl text-center"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <FlaskConical className="w-8 h-8 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">
            {patients.length === 0
              ? 'No patients found in the IRIS FHIR server.'
              : `No ${filter}-risk patients.`}
          </p>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((p, i) => (
            <PatientCard
              key={p.fhir_id}
              patient={p}
              rank={i + 1}
              onClick={() => setSelectedId(p.fhir_id)}
            />
          ))}
        </div>
      )}

      {/* Detail drawer */}
      {selectedId && (
        <PatientDrawer fhirId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
