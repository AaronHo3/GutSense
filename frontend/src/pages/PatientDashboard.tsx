
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Activity, Clock, CalendarDays, TrendingUp } from 'lucide-react';
import { usePatientData } from '../hooks/usePatientData';
import { useAlerts } from '../hooks/useAlerts';
import { RiskScore } from '../components/RiskScore';
import { BiomarkerChart, MARKERS } from '../components/BiomarkerChart';
import { AlertBanner } from '../components/AlertBanner';
import { LifestyleInputPanel } from '../components/LifestyleInputPanel';
import { ReportPanel } from '../components/ReportPanel';
import { ClinicalNotes } from '../components/ClinicalNotes';
import { api } from '../api/endpoints';
import type { Patient, ClinicalNote } from '../types';

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
