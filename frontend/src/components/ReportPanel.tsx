
import { useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import type { RiskAssessment } from '../types';

interface Props {
  risk: RiskAssessment;
  mode?: 'patient' | 'physician';
}

const LEVEL_BORDER: Record<string, string> = {
  green:  'border-l-emerald-400',
  yellow: 'border-l-yellow-400',
  orange: 'border-l-orange-400',
  red:    'border-l-red-500',
};

const STEP_COLORS: Record<string, string> = {
  green:  'bg-emerald-500/15 text-emerald-400',
  yellow: 'bg-yellow-500/15 text-yellow-400',
  orange: 'bg-orange-500/15 text-orange-400',
  red:    'bg-red-500/15 text-red-400',
};

export function ReportPanel({ risk, mode = 'patient' }: Props) {
  const [expanded, setExpanded] = useState(false);
  const explanation = mode === 'physician' ? risk.physician_summary : risk.patient_explanation;
  const borderClass = LEVEL_BORDER[risk.risk_level] ?? 'border-l-slate-300';
  const stepColor = STEP_COLORS[risk.risk_level] ?? 'bg-slate-100 text-slate-700';

  // Loading skeleton
  if (!explanation) {
    return (
      <div className={`rounded-2xl border-l-4 ${borderClass} p-4`} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-semibold text-slate-300">AI Analysis</span>
        </div>
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-white/10 rounded w-full" />
          <div className="h-3 bg-white/10 rounded w-5/6" />
          <div className="h-3 bg-white/10 rounded w-4/6" />
        </div>
      </div>
    );
  }

  // Truncate long text unless expanded
  const MAX_CHARS = 220;
  const isTruncatable = explanation.length > MAX_CHARS;
  const displayText = isTruncatable && !expanded
    ? explanation.slice(0, MAX_CHARS).trimEnd() + '…'
    : explanation;

  return (
    <div className={`rounded-2xl border-l-4 ${borderClass} p-4`} style={{ background: 'rgba(255,255,255,0.05)', borderTopColor: 'rgba(255,255,255,0.08)', borderRightColor: 'rgba(255,255,255,0.08)', borderBottomColor: 'rgba(255,255,255,0.08)' }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-semibold text-white">AI Analysis</span>
          {risk.confounded_by && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium">
              ⚠ Confounded
            </span>
          )}
        </div>
        <span className="text-xs text-slate-600 select-none">Claude</span>
      </div>

      <p className="text-sm text-slate-300 leading-relaxed">{displayText}</p>

      {isTruncatable && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 mt-1 transition-colors"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}

      {risk.confounded_by && (
        <p className="text-xs italic text-slate-500 mt-2">{risk.confounded_by}</p>
      )}

      {risk.next_steps && risk.next_steps.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {risk.next_steps.map((step, i) => (
            <span key={i} className={`text-xs px-2 py-0.5 rounded-full font-medium ${stepColor}`}>
              {i + 1}. {step}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
