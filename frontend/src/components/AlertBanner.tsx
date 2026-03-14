
import { AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import type { Alert } from '../types';

interface Props {
  alerts: Alert[];
  onAcknowledge: (id: number) => void;
}

const SEVERITY_CONFIG = {
  info:     { icon: Info,          bg: 'bg-blue-500/10',   border: 'border-blue-500/20 border-l-blue-500',  text: 'text-blue-300',  label: 'Info' },
  warning:  { icon: AlertTriangle, bg: 'bg-yellow-500/10', border: 'border-yellow-500/20 border-l-yellow-500', text: 'text-yellow-300', label: 'Warning' },
  critical: { icon: AlertCircle,   bg: 'bg-red-500/10',    border: 'border-red-500/20 border-l-red-500',   text: 'text-red-300',   label: 'Critical Alert' },
};

export function AlertBanner({ alerts, onAcknowledge }: Props) {
  if (alerts.length === 0) return null;

  // Deduplicate: show only the most recent alert per severity
  const seen = new Set<string>();
  const deduped = alerts.filter(a => {
    if (seen.has(a.severity)) return false;
    seen.add(a.severity);
    return true;
  });

  return (
    <div className="flex flex-col gap-2">
      {deduped.map(alert => {
        const cfg = SEVERITY_CONFIG[alert.severity];
        const Icon = cfg.icon;
        const isCritical = alert.severity === 'critical';
        return (
          <div
            key={alert.id}
            className={`flex items-start gap-3 p-3 rounded-xl border border-l-4 ${cfg.bg} ${cfg.border}`}
          >
            <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${cfg.text} ${isCritical ? 'animate-pulse' : ''}`} />
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-semibold ${cfg.text}`}>{cfg.label}</div>
              <div className={`text-xs ${cfg.text} opacity-75 mt-0.5`}>{alert.message}</div>
            </div>
            <button
              onClick={() => onAcknowledge(alert.id)}
              className={`${cfg.text} opacity-50 hover:opacity-100 transition-opacity flex-shrink-0`}
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
