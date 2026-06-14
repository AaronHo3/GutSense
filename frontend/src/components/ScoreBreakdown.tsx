
import type { RiskAssessment } from '../types';

interface Props {
  risk: RiskAssessment;
}

const MARKER_META: Record<string, { label: string; weight: number }> = {
  hemoglobin_fit: { label: 'Hemoglobin FIT', weight: 0.25 },
  calprotectin:   { label: 'Calprotectin', weight: 0.20 },
  mmp9:           { label: 'MMP-9', weight: 0.15 },
  mpo:            { label: 'MPO', weight: 0.15 },
  mmp8:           { label: 'MMP-8', weight: 0.10 },
  fibrinogen:     { label: 'Fibrinogen', weight: 0.08 },
  haptoglobin:    { label: 'Haptoglobin', weight: 0.05 },
  pgrp_s:         { label: 'PGRP-S', weight: 0.02 },
};

function barColor(score: number): string {
  if (score < 30) return '#2F6B4F';
  if (score < 60) return '#9A7A24';
  if (score < 80) return '#B35C33';
  return '#9E2B25';
}

export function ScoreBreakdown({ risk }: Props) {
  const breakdown = risk.score_breakdown;
  if (!breakdown) return null;

  const entries = Object.entries(MARKER_META).filter(([k]) => breakdown[k] !== undefined);

  return (
    <div className="card p-6">
      <div className="flex items-baseline justify-between mb-4">
        <span className="eyebrow">Score Breakdown</span>
        <span className="eyebrow">component · weight · contribution</span>
      </div>

      <div>
        {entries.map(([key, meta]) => {
          const raw = breakdown[key] ?? 0;
          const weighted = raw * meta.weight;
          const color = barColor(raw);
          return (
            <div key={key} className="py-2.5" style={{ borderTop: '1px solid var(--line)' }}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-ink" style={{ fontSize: '0.875rem' }}>{meta.label}</span>
                <div className="flex items-center gap-4 font-mono tnum" style={{ fontSize: '0.75rem' }}>
                  <span className="text-muted" style={{ width: 28, textAlign: 'right' }}>{raw.toFixed(0)}</span>
                  <span className="text-faint" style={{ width: 36, textAlign: 'right' }}>×{meta.weight.toFixed(2)}</span>
                  <span style={{ color, width: 36, textAlign: 'right', fontWeight: 500 }}>{weighted.toFixed(1)}</span>
                </div>
              </div>
              <div className="h-px w-full" style={{ background: 'var(--line)' }}>
                <div className="h-px" style={{ width: `${Math.min(100, raw)}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-between items-baseline mt-4 pt-3" style={{ borderTop: '1px solid var(--line2)' }}>
        <span className="eyebrow">Weighted total · pre-adjustment</span>
        <span className="font-mono tnum text-ink" style={{ fontSize: '0.9375rem', fontWeight: 500 }}>
          {risk.raw_score.toFixed(1)} <span className="text-faint">/ 100</span>
        </span>
      </div>
    </div>
  );
}
