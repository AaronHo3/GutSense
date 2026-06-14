
import { useState } from 'react';
import type { RiskAssessment } from '../types';

interface Props {
  risk: RiskAssessment;
  mode?: 'patient' | 'physician';
}

export function ReportPanel({ risk, mode = 'patient' }: Props) {
  const [expanded, setExpanded] = useState(false);
  const explanation = mode === 'physician' ? risk.physician_summary : risk.patient_explanation;

  if (!explanation) {
    return (
      <div className="card p-6 h-full">
        <span className="eyebrow">AI Analysis</span>
        <div className="space-y-2.5 mt-4 animate-pulse">
          <div className="h-3.5 rounded w-full" style={{ background: 'var(--line)' }} />
          <div className="h-3.5 rounded w-5/6" style={{ background: 'var(--line)' }} />
          <div className="h-3.5 rounded w-4/6" style={{ background: 'var(--line)' }} />
        </div>
      </div>
    );
  }

  const MAX_CHARS = 260;
  const isTruncatable = explanation.length > MAX_CHARS;
  const displayText = isTruncatable && !expanded
    ? explanation.slice(0, MAX_CHARS).trimEnd() + '…'
    : explanation;

  return (
    <div className="card p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="eyebrow">AI Analysis</span>
          {risk.confounded_by && (
            <span className="font-mono uppercase" style={{ fontSize: '0.625rem', letterSpacing: '0.1em', color: '#9A7A24' }}>
              · Confounded
            </span>
          )}
        </div>
        <span className="font-mono text-faint" style={{ fontSize: '0.625rem', letterSpacing: '0.08em' }}>
          CLAUDE · SONNET 4.6
        </span>
      </div>

      <p
        className="font-serif text-ink"
        style={{ fontSize: '1.0625rem', lineHeight: 1.55, fontWeight: 380, letterSpacing: '-0.005em' }}
      >
        {displayText}
      </p>

      {isTruncatable && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="self-start mt-2 font-mono text-faint hover:text-ink transition-colors"
          style={{ fontSize: '0.6875rem', letterSpacing: '0.04em' }}
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}

      {risk.confounded_by && (
        <p className="text-faint mt-3" style={{ fontSize: '0.8125rem', fontStyle: 'italic' }}>
          {risk.confounded_by}
        </p>
      )}

      {risk.next_steps && risk.next_steps.length > 0 && (
        <div className="mt-auto pt-5">
          <hr className="hairline mb-3" />
          <span className="eyebrow">Recommended next steps</span>
          <ol className="mt-3 space-y-2">
            {risk.next_steps.map((step, i) => (
              <li key={i} className="flex gap-3 items-baseline">
                <span className="font-mono text-faint tnum" style={{ fontSize: '0.6875rem' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="text-muted" style={{ fontSize: '0.875rem', lineHeight: 1.45 }}>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
