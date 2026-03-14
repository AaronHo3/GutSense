
import type { RiskAssessment } from '../types';

interface Props {
  risk: RiskAssessment;
}

const MARKER_META: Record<string, { label: string; weight: number; color: string; unit: string }> = {
  hemoglobin:     { label: 'Occult Blood (Hgb)',       weight: 0.25, color: '#ef4444', unit: 'ng/mL' },
  methylation:    { label: 'DNA Methylation (SEPT9)',   weight: 0.25, color: '#3b82f6', unit: '0–1' },
  calprotectin:   { label: 'Calprotectin (Inflam.)',    weight: 0.20, color: '#f97316', unit: 'µg/g' },
  butyrate:       { label: 'Butyrate (Protective)',     weight: 0.15, color: '#22c55e', unit: 'mmol/kg' },
  basidio_ascomy: { label: 'Fungal Dysbiosis',          weight: 0.10, color: '#a855f7', unit: 'ratio' },
  proteobacteria: { label: 'Proteobacteria Index',      weight: 0.05, color: '#f59e0b', unit: '0–1' },
};

function barColor(componentScore: number): string {
  if (componentScore < 30) return '#22c55e';
  if (componentScore < 60) return '#eab308';
  if (componentScore < 80) return '#f97316';
  return '#ef4444';
}

export function ScoreBreakdown({ risk }: Props) {
  const breakdown = risk.score_breakdown;
  if (!breakdown) return null;

  const entries = Object.entries(MARKER_META).filter(([k]) => breakdown[k] !== undefined);

  return (
    <div className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
        Score Breakdown
      </h3>
      <div className="space-y-2.5">
        {entries.map(([key, meta]) => {
          const raw = breakdown[key] ?? 0;
          const weighted = raw * meta.weight;
          const color = barColor(raw);
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-0.5">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: meta.color }}
                  />
                  <span className="text-xs text-slate-300">{meta.label}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400 tabular-nums">
                  <span className="font-mono">{raw.toFixed(0)}</span>
                  <span className="text-slate-600">×{meta.weight}</span>
                  <span className="font-semibold" style={{ color }}>
                    {weighted.toFixed(1)}
                  </span>
                </div>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(100, raw)}%`, background: color }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-2 flex justify-between text-xs" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <span className="text-slate-500">Weighted total (pre-adjustments)</span>
        <span className="font-bold text-white tabular-nums">
          {risk.raw_score.toFixed(1)} / 100
        </span>
      </div>
    </div>
  );
}
