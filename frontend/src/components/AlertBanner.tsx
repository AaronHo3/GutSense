
import { X } from 'lucide-react';
import type { Alert } from '../types';

interface Props {
  alerts: Alert[];
  onAcknowledge: (id: number) => void;
}

const SEVERITY: Record<string, { color: string; tint: string; label: string }> = {
  info:     { color: '#56524A', tint: 'rgba(86,82,74,0.05)',  label: 'Notice' },
  warning:  { color: '#9A7A24', tint: 'rgba(154,122,36,0.07)', label: 'Warning' },
  critical: { color: '#9E2B25', tint: 'rgba(158,43,37,0.07)',  label: 'Critical Alert' },
};

export function AlertBanner({ alerts, onAcknowledge }: Props) {
  if (alerts.length === 0) return null;

  const seen = new Set<string>();
  const deduped = alerts.filter(a => {
    if (seen.has(a.severity)) return false;
    seen.add(a.severity);
    return true;
  });

  return (
    <div className="flex flex-col gap-2">
      {deduped.map(alert => {
        const cfg = SEVERITY[alert.severity] ?? SEVERITY.info;
        return (
          <div
            key={alert.id}
            className="flex items-start gap-4 pl-4 pr-3 py-3"
            style={{ background: cfg.tint, borderLeft: `2px solid ${cfg.color}` }}
          >
            <div className="flex-1 min-w-0">
              <div className="font-mono uppercase" style={{ color: cfg.color, fontSize: '0.6875rem', letterSpacing: '0.12em', fontWeight: 500 }}>
                {cfg.label}
              </div>
              <div className="text-muted mt-1" style={{ fontSize: '0.875rem', lineHeight: 1.4 }}>{alert.message}</div>
            </div>
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="text-faint hover:text-ink transition-colors flex-shrink-0 mt-0.5"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
