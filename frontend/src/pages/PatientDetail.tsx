
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Zap, FileText } from 'lucide-react';
import { usePatientData } from '../hooks/usePatientData';
import { useAlerts } from '../hooks/useAlerts';
import { RiskScore } from '../components/RiskScore';
import { BiomarkerChart, MARKERS } from '../components/BiomarkerChart';
import { AlertBanner } from '../components/AlertBanner';
import { ClinicalNotes } from '../components/ClinicalNotes';
import { ReportPanel } from '../components/ReportPanel';
import { ScoreBreakdown } from '../components/ScoreBreakdown';
import { ReferralModal } from '../components/ReferralModal';
import { api } from '../api/endpoints';
import type { Patient, ClinicalNote } from '../types';

const TRAJECTORY_GLYPH: Record<string, string> = {
  'Rapidly Increasing': '↑↑',
  'Slowly Increasing': '↑',
  'Stable': '→',
  'Improving': '↓',
};

const LEVEL_META: Record<string, { color: string; label: string }> = {
  green:  { color: '#2F6B4F', label: 'Low' },
  yellow: { color: '#9A7A24', label: 'Elevated' },
  orange: { color: '#B35C33', label: 'High' },
  red:    { color: '#9E2B25', label: 'Critical' },
};

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

export function PatientDetail() {
  const { patientId } = useParams<{ patientId: string }>();
  const id = Number(patientId);
  const navigate = useNavigate();

  const { readings, latestRisk, loading } = usePatientData(id, 10000);
  const { alerts, acknowledge } = useAlerts(id, 10000);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [spiking, setSpiking] = useState(false);
  const [showReferral, setShowReferral] = useState(false);

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
    return <div className="flex items-center justify-center min-h-[60vh] eyebrow">Loading…</div>;
  }

  const lastReadingTime = latestRisk
    ? new Date(latestRisk.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'n/a';
  const daysMonitored = readings.length > 0
    ? Math.round((Date.now() - new Date(readings[0].timestamp).getTime()) / 86400000)
    : 0;
  const meta = latestRisk ? LEVEL_META[latestRisk.risk_level] : LEVEL_META.green;

  return (
    <div className="max-w-5xl mx-auto px-5 sm:px-8 py-10 sm:py-14">

      {/* Back link */}
      <button
        onClick={() => navigate('/physician')}
        className="flex items-center gap-2 eyebrow hover:text-ink transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Roster
      </button>

      {/* Masthead */}
      <header className="rise flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="eyebrow">Patient File</span>
            {latestRisk && (
              <span className="font-mono uppercase" style={{ fontSize: '0.625rem', letterSpacing: '0.12em', color: meta.color }}>
                · {meta.label} Risk
              </span>
            )}
          </div>
          <h1 className="font-serif text-ink mt-3" style={{ fontSize: 'clamp(2.25rem, 5vw, 3.5rem)', lineHeight: 1, fontWeight: 420, letterSpacing: '-0.02em' }}>
            {patient?.name ?? 'Patient'}
          </h1>
          <p className="font-mono text-muted mt-3" style={{ fontSize: '0.8125rem' }}>
            {patient && `${patient.age} · ${patient.sex === 'M' ? 'Male' : 'Female'}`}
            {patient?.family_history && '  ·  Family history of CRC'}
            {patient?.has_nod2_variant && '  ·  NOD2 variant'}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => setShowReferral(true)}
            className="flex items-center gap-2 px-4 py-2 text-paper font-mono uppercase transition"
            style={{ background: 'var(--ink)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
          >
            <FileText className="w-3.5 h-3.5" />
            Referral
          </button>
          <button
            onClick={handleSpike}
            disabled={spiking}
            className="flex items-center gap-2 px-4 py-2 text-muted hover:text-ink font-mono uppercase transition disabled:opacity-40"
            style={{ border: '1px solid var(--line2)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
          >
            <Zap className="w-3.5 h-3.5" />
            {spiking ? 'Simulating…' : 'Spike'}
          </button>
        </div>
      </header>

      {/* Stat band */}
      {latestRisk && (
        <div className="mt-8 flex flex-wrap divide-x rise" style={{ borderTop: '1px solid var(--ink)', borderBottom: '1px solid var(--line)', borderColor: 'var(--line)' }}>
          <StatCell label="Risk Score" value={String(Math.round(latestRisk.adjusted_score))} color={meta.color} />
          <StatCell label="Trajectory" value={`${TRAJECTORY_GLYPH[latestRisk.trajectory] ?? '→'} ${latestRisk.trajectory}`} />
          <StatCell label="Last Reading" value={lastReadingTime} />
          <StatCell label="Days Monitored" value={String(daysMonitored)} />
        </div>
      )}

      {/* Alerts */}
      <div className="mt-6">
        <AlertBanner alerts={alerts} onAcknowledge={acknowledge} />
      </div>

      {/* Gauge + AI + breakdown */}
      {latestRisk && (
        <section className="mt-8 grid grid-cols-1 lg:grid-cols-[minmax(0,300px)_1fr] gap-6 items-stretch rise" style={{ animationDelay: '0.08s' }}>
          <div className="card flex items-center justify-center py-10">
            <RiskScore
              score={latestRisk.adjusted_score}
              level={latestRisk.risk_level}
              trajectory={latestRisk.trajectory}
            />
          </div>
          <ReportPanel risk={latestRisk} mode="physician" />
        </section>
      )}

      {latestRisk && (
        <div className="mt-6">
          <ScoreBreakdown risk={latestRisk} />
        </div>
      )}

      {/* Biomarker trends */}
      <section className="mt-14">
        <div className="flex items-baseline justify-between pb-3" style={{ borderBottom: '1px solid var(--ink)' }}>
          <h2 className="font-serif text-ink" style={{ fontSize: '1.5rem', fontWeight: 420 }}>Biomarker Trends</h2>
          <span className="eyebrow hidden sm:block">8 markers · 90-day window</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-6">
          {MARKERS.map(marker => (
            <BiomarkerChart key={marker.key} readings={readings} marker={marker} />
          ))}
        </div>
      </section>

      {/* Clinical notes */}
      <div className="mt-6">
        <ClinicalNotes notes={notes} onAdd={handleAddNote} allowAdd />
      </div>

      {showReferral && patient && (
        <ReferralModal
          patientId={id}
          patientName={patient.name}
          onClose={() => setShowReferral(false)}
          onSent={loadNotes}
        />
      )}
    </div>
  );
}
