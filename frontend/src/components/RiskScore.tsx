
import { TrendingUp, TrendingDown, Minus, Flame } from 'lucide-react';

interface Props {
  score: number;
  level: 'green' | 'yellow' | 'orange' | 'red';
  trajectory: string;
  size?: number;
}

const LEVEL_COLORS = {
  green:  { stroke: '#34d399', text: '#34d399', glow: 'rgba(52,211,153,0.25)',  label: 'Low Risk' },
  yellow: { stroke: '#fbbf24', text: '#fbbf24', glow: 'rgba(251,191,36,0.25)',  label: 'Elevated' },
  orange: { stroke: '#fb923c', text: '#fb923c', glow: 'rgba(251,146,60,0.25)',  label: 'High Risk' },
  red:    { stroke: '#f87171', text: '#f87171', glow: 'rgba(248,113,113,0.35)', label: 'Critical' },
};

function TrajectoryIcon({ trajectory }: { trajectory: string }) {
  const cls = 'w-3.5 h-3.5';
  if (trajectory === 'Rapidly Increasing') return <Flame className={`${cls} text-red-500`} />;
  if (trajectory === 'Slowly Increasing')  return <TrendingUp className={`${cls} text-orange-400`} />;
  if (trajectory === 'Improving')          return <TrendingDown className={`${cls} text-green-500`} />;
  return <Minus className={`${cls} text-slate-400`} />;
}

export function RiskScore({ score, level, trajectory, size = 180 }: Props) {
  const colors = LEVEL_COLORS[level];
  const radius = size / 2 - 14;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - score / 100);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Gauge card */}
      <div
        className="rounded-2xl p-5 flex flex-col items-center"
        style={{ background: 'rgba(255,255,255,0.05)', border: `1px solid ${colors.stroke}30`, backdropFilter: 'blur(12px)' }}
      >
        {/* Glow layer */}
        <div
          className="absolute rounded-full blur-2xl pointer-events-none"
          style={{
            width: size * 0.7,
            height: size * 0.7,
            background: colors.glow,
          }}
        />
        <div style={{ position: 'relative' }}>
          <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            {/* Track ring */}
            <circle
              cx={center} cy={center} r={radius}
              fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={11}
            />
            {/* Score arc */}
            <circle
              cx={center} cy={center} r={radius}
              fill="none"
              stroke={colors.stroke}
              strokeWidth={11}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(.4,0,.2,1)', filter: `drop-shadow(0 0 6px ${colors.glow})` }}
            />
          </svg>
          {/* Score text centered */}
          <div
            style={{
              position: 'absolute',
              top: 0, left: 0, width: size, height: size,
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
            }}
          >
            <div className="text-5xl font-bold tabular-nums" style={{ color: colors.text, lineHeight: 1 }}>
              {Math.round(score)}
            </div>
            <div className="text-xs font-medium mt-1" style={{ color: colors.text, opacity: 0.6 }}>
              / 100
            </div>
          </div>
        </div>
      </div>

      {/* Label + trajectory below */}
      <div className="text-center space-y-1">
        <div
          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
          style={{ background: colors.glow, color: colors.text }}
        >
          {colors.label}
        </div>
        <div className="flex items-center justify-center gap-1 text-xs text-slate-400">
          <TrajectoryIcon trajectory={trajectory} />
          <span>{trajectory}</span>
        </div>
      </div>
    </div>
  );
}
