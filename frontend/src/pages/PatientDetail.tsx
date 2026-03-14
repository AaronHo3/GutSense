
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Zap, Clock, CalendarDays, TrendingUp } from 'lucide-react';
import { usePatientData } from '../hooks/usePatientData';
import { useAlerts } from '../hooks/useAlerts';
import { RiskScore } from '../components/RiskScore';
import { ScoreBreakdown } from '../components/ScoreBreakdown';
import { BiomarkerChart, MARKERS } from '../components/BiomarkerChart';
import { AlertBanner } from '../components/AlertBanner';
import { ClinicalNotes } from '../components/ClinicalNotes';
import { ReportPanel } from '../components/ReportPanel';
import { api } from '../api/endpoints';
import type { Patient, ClinicalNote } from '../types';

export function PatientDetail() {
  const { patientId } = useParams<{ patientId: string }>();
  const id = Number(patientId);
  const navigate = useNavigate();

  const { readings, latestRisk, loading } = usePatientData(id, 10000);
  const { alerts, acknowledge } = useAlerts(id, 10000);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [spiking, setSpiking] = useState(false);

  const loadNotes = () => api.getNotes(id).then(setNotes).catch(() => {});

  useEffect(() => {
    api.getPatient(id).then(setPatient).catch(() => {});
    loadNotes();
  }, [id]);

  const handleAddNote = async (text: string, isRec: boolean) => {
    await api.addNote(id, text, isRec);
    loadNotes();
  };

  const handleSpike = async () => {
    setSpiking(true);
    await api.simulateSpike(id);
    setSpiking(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen text-slate-400 text-sm">Loading...</div>;
  }

  const lastReadingTime = latestRisk
    ? new Date(latestRisk.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—';
  const daysMonitored = readings.length > 0
    ? Math.round((Date.now() - new Date(readings[0].timestamp).getTime()) / 86400000)
    : 0;

  const levelColors: Record<string, string> = {
    green: 'bg-emerald-500/15 text-emerald-400',
    yellow: 'bg-yellow-500/15 text-yellow-400',
    orange: 'bg-orange-500/15 text-orange-400',
    red: 'bg-red-500/15 text-red-400',
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/physician')}
          className="p-2 rounded-lg text-slate-400 hover:text-white transition flex-shrink-0"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-bold text-white">{patient?.name ?? 'Patient'}</h1>
            {latestRisk && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${levelColors[latestRisk.risk_level]}`}>
                {latestRisk.risk_level === 'green' ? 'Low' : latestRisk.risk_level === 'yellow' ? 'Elevated' : latestRisk.risk_level === 'orange' ? 'High' : 'Critical'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            {patient && `${patient.age}${patient.sex}`}
            {patient?.family_history && ' · Family history of CRC'}
            {patient?.has_nod2_variant && ' · NOD2 variant'}
          </p>
        </div>
        <button
          onClick={handleSpike}
          disabled={spiking}
          className="flex items-center gap-1.5 px-3 py-2 bg-orange-500 hover:bg-orange-600 text-white text-xs rounded-lg transition disabled:opacity-50 flex-shrink-0"
        >
          <Zap className="w-3.5 h-3.5" />
          {spiking ? 'Simulating...' : 'Simulate Spike'}
        </button>
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
            <div className="text-sm font-semibold text-white truncate">{latestRisk.trajectory}</div>
            <div className="text-xs text-slate-500 mt-0.5 flex items-center justify-center gap-1">
              <TrendingUp className="w-3 h-3" />7-Day Trend
            </div>
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

      {/* Risk gauge + AI report + score breakdown */}
      {latestRisk && (
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          <div className="flex-shrink-0 flex justify-center w-full sm:w-auto">
            <RiskScore
              score={latestRisk.adjusted_score}
              level={latestRisk.risk_level}
              trajectory={latestRisk.trajectory}
            />
          </div>
          <div className="flex-1 space-y-3">
            <ReportPanel risk={latestRisk} mode="physician" />
            <ScoreBreakdown risk={latestRisk} />
          </div>
        </div>
      )}

      {/* Biomarker trends */}
      <div>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 pb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          Biomarker Trends
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {MARKERS.map(marker => (
            <BiomarkerChart key={marker.key} readings={readings} marker={marker} />
          ))}
        </div>
      </div>

      {/* Clinical notes */}
      <ClinicalNotes notes={notes} onAdd={handleAddNote} allowAdd />
    </div>
  );
}
