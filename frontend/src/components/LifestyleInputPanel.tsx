
import { useState, useEffect } from 'react';
import { api } from '../api/endpoints';
import type { LifestyleMetadata } from '../types';

interface Props {
  patientId: number;
  onUpdate?: () => void;
}

export function LifestyleInputPanel({ patientId, onUpdate }: Props) {
  const [data, setData] = useState<Partial<LifestyleMetadata>>({
    recent_antibiotic_use: false,
    fiber_intake_g_day: 20,
    sleep_quality: 3,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [recalculating, setRecalculating] = useState(false);

  useEffect(() => {
    api.getLifestyle(patientId).then(l => {
      if (l) setData(l);
    }).catch(() => {});
  }, [patientId]);

  const handleSave = async () => {
    setSaving(true);
    await api.updateLifestyle(patientId, {
      recent_antibiotic_use: data.recent_antibiotic_use,
      fiber_intake_g_day: data.fiber_intake_g_day,
      sleep_quality: data.sleep_quality,
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onUpdate?.();
  };

  const handleRecalculate = async () => {
    setRecalculating(true);
    await api.recalculateScore(patientId);
    setRecalculating(false);
    onUpdate?.();
  };

  const sleepLabels = ['n/a', 'Poor', 'Fair', 'Okay', 'Good', 'Excellent'];
  const antibioticOn = data.recent_antibiotic_use ?? false;

  return (
    <div className="card p-6">
      <span className="eyebrow">Lifestyle Context</span>
      <p className="text-muted mt-3 mb-5" style={{ fontSize: '0.8125rem', lineHeight: 1.5 }}>
        Adjustments apply to the next incoming reading. Save, then use Recalculate to apply immediately.
      </p>

      <div className="space-y-5">
        {/* Antibiotics toggle */}
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <div className="text-ink" style={{ fontSize: '0.9375rem' }}>Recent antibiotic use</div>
            <div className="font-mono text-faint mt-0.5" style={{ fontSize: '0.6875rem' }}>Adjusts microbiome markers</div>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              className="sr-only"
              checked={antibioticOn}
              onChange={e => setData(d => ({ ...d, recent_antibiotic_use: e.target.checked }))}
            />
            <div className="w-9 h-5 rounded-full transition-colors" style={{ background: antibioticOn ? 'var(--ink)' : 'var(--line2)' }}>
              <div className="w-4 h-4 rounded-full transition-transform mt-0.5" style={{ background: 'var(--surface)', transform: antibioticOn ? 'translateX(18px)' : 'translateX(2px)' }} />
            </div>
          </div>
        </label>

        {/* Fiber intake */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-ink" style={{ fontSize: '0.9375rem' }}>Daily fiber intake</span>
            <span className="font-mono tnum text-ink" style={{ fontSize: '0.875rem', fontWeight: 500 }}>{data.fiber_intake_g_day ?? 20}g</span>
          </div>
          <input
            type="range"
            min={0} max={60} step={1}
            value={data.fiber_intake_g_day ?? 20}
            onChange={e => setData(d => ({ ...d, fiber_intake_g_day: Number(e.target.value) }))}
            className="w-full"
            style={{ accentColor: '#1B1A17' }}
          />
          <div className="flex justify-between font-mono text-faint mt-1" style={{ fontSize: '0.625rem' }}>
            <span>0g</span><span>25g target</span><span>60g</span>
          </div>
        </div>

        {/* Sleep quality */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-ink" style={{ fontSize: '0.9375rem' }}>Sleep quality</span>
            <span className="font-mono text-ink" style={{ fontSize: '0.875rem', fontWeight: 500 }}>{sleepLabels[data.sleep_quality ?? 3]}</span>
          </div>
          <input
            type="range"
            min={1} max={5} step={1}
            value={data.sleep_quality ?? 3}
            onChange={e => setData(d => ({ ...d, sleep_quality: Number(e.target.value) }))}
            className="w-full"
            style={{ accentColor: '#1B1A17' }}
          />
        </div>
      </div>

      <div className="mt-6 flex gap-2.5">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 px-4 py-2 font-mono uppercase transition disabled:opacity-40"
          style={{
            background: saved ? '#2F6B4F' : 'var(--ink)',
            color: 'var(--paper)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em',
          }}
        >
          {saving ? 'Saving…' : saved ? 'Saved' : 'Save'}
        </button>
        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          className="px-4 py-2 font-mono uppercase text-muted hover:text-ink transition disabled:opacity-40"
          style={{ border: '1px solid var(--line2)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
          title="Re-score the latest reading with current lifestyle data"
        >
          {recalculating ? 'Updating…' : 'Recalculate'}
        </button>
      </div>
    </div>
  );
}
