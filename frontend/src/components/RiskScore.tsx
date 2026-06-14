
interface Props {
  score: number;
  level: 'green' | 'yellow' | 'orange' | 'red';
  trajectory: string;
  size?: number;
}

const LEVEL_META = {
  green:  { color: '#2F6B4F', label: 'Low Risk' },
  yellow: { color: '#9A7A24', label: 'Elevated' },
  orange: { color: '#B35C33', label: 'High Risk' },
  red:    { color: '#9E2B25', label: 'Critical' },
};

const TRAJECTORY_GLYPH: Record<string, string> = {
  'Rapidly Increasing': '↑↑',
  'Slowly Increasing': '↑',
  'Stable': '→',
  'Improving': '↓',
};

export function RiskScore({ score, level, trajectory, size = 208 }: Props) {
  const { color, label } = LEVEL_META[level];
  const stroke = 3;
  const radius = size / 2 - 18;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const fraction = Math.max(0, Math.min(1, score / 100));
  const dashOffset = circumference * (1 - fraction);

  // End-cap marker position (track starts at top, sweeps clockwise)
  const endAngle = -Math.PI / 2 + fraction * 2 * Math.PI;
  const markerX = center + radius * Math.cos(endAngle);
  const markerY = center + radius * Math.sin(endAngle);

  // Major ticks at 0 / 25 / 50 / 75
  const ticks = [0, 0.25, 0.5, 0.75].map(t => {
    const a = -Math.PI / 2 + t * 2 * Math.PI;
    const inner = radius + 6;
    const outer = radius + 10;
    return {
      x1: center + inner * Math.cos(a), y1: center + inner * Math.sin(a),
      x2: center + outer * Math.cos(a), y2: center + outer * Math.sin(a),
    };
  });

  return (
    <div className="flex flex-col items-center">
      <span className="eyebrow mb-4">Risk Index</span>

      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {/* Hairline track */}
          <circle
            cx={center} cy={center} r={radius}
            fill="none" stroke="#D2CCBD" strokeWidth={stroke}
          />
          {/* Signal arc */}
          <circle
            cx={center} cy={center} r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.22,1,0.36,1)' }}
          />
        </svg>

        {/* Ticks (drawn upright, not rotated) */}
        <svg width={size} height={size} style={{ position: 'absolute', top: 0, left: 0 }}>
          {ticks.map((t, i) => (
            <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke="#D2CCBD" strokeWidth={1} />
          ))}
          <circle cx={markerX} cy={markerY} r={4.5} fill={color} />
        </svg>

        {/* Numeral */}
        <div
          style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <span
            className="font-serif tnum"
            style={{ fontSize: '4.25rem', lineHeight: 0.9, fontWeight: 460, color, letterSpacing: '-0.02em' }}
          >
            {Math.round(score)}
          </span>
          <span className="font-mono text-faint" style={{ fontSize: '0.7rem', marginTop: 2 }}>
            / 100
          </span>
        </div>
      </div>

      {/* Level + trajectory */}
      <div className="mt-5 flex flex-col items-center gap-1.5">
        <span
          className="font-mono uppercase"
          style={{ color, fontSize: '0.8125rem', letterSpacing: '0.12em', fontWeight: 500 }}
        >
          {label}
        </span>
        <span className="font-mono text-muted" style={{ fontSize: '0.6875rem', letterSpacing: '0.04em' }}>
          {TRAJECTORY_GLYPH[trajectory] ?? '→'} {trajectory}
        </span>
      </div>
    </div>
  );
}
