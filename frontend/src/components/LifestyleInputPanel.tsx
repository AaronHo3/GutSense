
import { useState, useEffect } from 'react';
import { Apple, Moon, Pill, Save, RefreshCw } from 'lucide-react';
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

  const sleepLabels = ['—', 'Poor', 'Fair', 'Okay', 'Good', 'Excellent'];

  return (
    <div className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1 pb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        Lifestyle Context
      </h3>
      <p className="text-xs text-slate-500 mb-4 mt-2">
        Adjustments apply to the next incoming reading. Save then use <span className="font-medium text-slate-400">Recalculate</span> to apply immediately.
      </p>

      <div className="space-y-4">
        {/* Antibiotics toggle */}
        <label className="flex items-center justify-between cursor-pointer group">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-orange-500/15 flex items-center justify-center flex-shrink-0">
              <Pill className="w-3.5 h-3.5 text-orange-400" />
            </div>
            <div>
              <div className="text-sm text-slate-200 font-medium">Recent antibiotic use</div>
              <div className="text-xs text-slate-500">Adjusts microbiome markers</div>
            </div>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              className="sr-only"
              checked={data.recent_antibiotic_use ?? false}
              onChange={e => setData(d => ({ ...d, recent_antibiotic_use: e.target.checked }))}
            />
            <div
              className={`w-9 h-5 rounded-full transition-colors ${data.recent_antibiotic_use ? 'bg-orange-500' : 'bg-white/15'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white shadow-sm transition-transform mt-0.5 ${data.recent_antibiotic_use ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'}`} />
            </div>
          </div>
        </label>

        {/* Fiber intake */}
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
              <Apple className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="flex-1 flex items-center justify-between">
              <span className="text-sm text-slate-200 font-medium">Daily fiber intake</span>
              <span className="text-sm font-bold text-emerald-400">{data.fiber_intake_g_day ?? 20}g</span>
            </div>
          </div>
          <input
            type="range"
            min={0} max={60} step={1}
            value={data.fiber_intake_g_day ?? 20}
            onChange={e => setData(d => ({ ...d, fiber_intake_g_day: Number(e.target.value) }))}
            className="w-full accent-emerald-400 ml-9"
            style={{ width: 'calc(100% - 2.25rem)' }}
          />
          <div className="flex justify-between text-xs text-slate-600 mt-0.5 ml-9">
            <span>0g</span><span>25g target</span><span>60g</span>
          </div>
        </div>

        {/* Sleep quality */}
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <div className="flex-1 flex items-center justify-between">
              <span className="text-sm text-slate-200 font-medium">Sleep quality</span>
              <span className="text-sm font-bold text-indigo-400">{sleepLabels[data.sleep_quality ?? 3]}</span>
            </div>
          </div>
          <input
            type="range"
            min={1} max={5} step={1}
            value={data.sleep_quality ?? 3}
            onChange={e => setData(d => ({ ...d, sleep_quality: Number(e.target.value) }))}
            className="w-full accent-indigo-400 ml-9"
            style={{ width: 'calc(100% - 2.25rem)' }}
          />
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-xl transition shadow-sm font-medium ${
            saved
              ? 'bg-emerald-500 text-white'
              : 'text-white hover:bg-white/20'
          } disabled:opacity-50`}
          style={saved ? {} : { background: 'rgba(255,255,255,0.1)' }}
        >
          <Save className="w-3.5 h-3.5" />
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save'}
        </button>
        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          className="flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-xl transition shadow-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          title="Re-score the latest reading with current lifestyle data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${recalculating ? 'animate-spin' : ''}`} />
          {recalculating ? 'Updating...' : 'Recalculate'}
        </button>
      </div>
    </div>
  );
}
