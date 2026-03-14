
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts';
import type { BiomarkerReading } from '../types';

interface MarkerConfig {
  key: keyof BiomarkerReading;
  label: string;
  unit: string;
  normalMax: number;
  alarmAt: number;
  color: string;
  inverted?: boolean;
  decimals?: number;
}

export const MARKERS: MarkerConfig[] = [
  {
    key: 'hemoglobin_ng_ml',
    label: 'Occult Blood (Hemoglobin)',
    unit: 'ng/mL',
    normalMax: 20,
    alarmAt: 100,
    color: '#ef4444',
  },
  {
    key: 'butyrate_mmol_kg',
    label: 'Butyrate (Protective SCFA)',
    unit: 'mmol/kg',
    normalMax: 15,
    alarmAt: 5,
    color: '#22c55e',
    inverted: true,
  },
  {
    key: 'calprotectin_ug_g',
    label: 'Calprotectin (Inflammation)',
    unit: 'µg/g',
    normalMax: 50,
    alarmAt: 200,
    color: '#f97316',
  },
  {
    key: 'basidio_ascomy_ratio',
    label: 'Fungal Dysbiosis Index',
    unit: 'ratio',
    normalMax: 1.5,
    alarmAt: 3.0,
    color: '#a855f7',
    decimals: 2,
  },
  {
    key: 'proteobacteria_index',
    label: 'Proteobacteria Index',
    unit: '0–1',
    normalMax: 0.2,
    alarmAt: 0.5,
    color: '#f59e0b',
    decimals: 3,
  },
  {
    key: 'methylation_score',
    label: 'DNA Methylation (SEPT9/SDC2)',
    unit: '0–1',
    normalMax: 0.25,
    alarmAt: 0.5,
    color: '#3b82f6',
    decimals: 3,
  },
];

interface Props {
  readings: BiomarkerReading[];
  marker: MarkerConfig;
}

interface DataPoint {
  date: string;
  value: number;
}

// Custom dot: only render for alarm-level readings
function AlarmDot(props: { cx?: number; cy?: number; payload?: DataPoint; marker: MarkerConfig }) {
  const { cx, cy, payload, marker } = props;
  if (!payload || cx === undefined || cy === undefined) return null;
  const isAlarm = marker.inverted
    ? payload.value < marker.alarmAt
    : payload.value > marker.alarmAt;
  if (!isAlarm) return null;
  return (
    <circle
      cx={cx} cy={cy} r={4}
      fill="#ef4444" stroke="white" strokeWidth={1.5}
    />
  );
}

export function BiomarkerChart({ readings, marker }: Props) {
  const data: DataPoint[] = readings.map(r => ({
    date: new Date(r.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: Number((r[marker.key] as number).toFixed(marker.decimals ?? 1)),
  }));

  const latestVal = data.length > 0 ? data[data.length - 1].value : null;
  const isAlarm = latestVal !== null && (
    marker.inverted ? latestVal < marker.alarmAt : latestVal > marker.alarmAt
  );
  const isConcerning = !isAlarm && latestVal !== null && (
    marker.inverted ? latestVal < marker.normalMax : latestVal > marker.normalMax
  );

  const statusColor = isAlarm ? 'text-red-400' : isConcerning ? 'text-yellow-400' : 'text-emerald-400';
  const statusLabel = isAlarm ? 'Alarm' : isConcerning ? 'Elevated' : 'Normal';
  const statusBg = isAlarm ? 'bg-red-500/15' : isConcerning ? 'bg-yellow-500/15' : 'bg-emerald-500/15';

  const gradientId = `grad-${String(marker.key)}`;

  return (
    <div
      className="rounded-2xl overflow-hidden border-l-4"
      style={{ background: 'rgba(255,255,255,0.05)', border: `1px solid rgba(255,255,255,0.08)`, borderLeftColor: marker.color }}
    >
      <div className="px-4 pt-4 pb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ background: marker.color }}
          />
          <div>
            <h3 className="text-xs font-semibold text-slate-200 leading-tight">{marker.label}</h3>
            <p className="text-xs text-slate-500">{marker.unit}</p>
          </div>
        </div>
        {latestVal !== null && (
          <div className="text-right">
            <div className="text-lg font-bold tabular-nums" style={{ color: marker.color }}>
              {latestVal.toFixed(marker.decimals ?? 1)}
            </div>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${statusBg} ${statusColor}`}>
              {statusLabel}
            </span>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={150}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={marker.color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={marker.color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: '#64748b' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 9, fill: '#64748b' }} tickLine={false} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }}
            formatter={(v) => [`${Number(v).toFixed(marker.decimals ?? 1)} ${marker.unit}`, marker.label]}
          />
          <ReferenceLine
            y={marker.normalMax}
            stroke="#34d399"
            strokeDasharray="4 2"
            strokeOpacity={0.5}
            label={{ value: 'Normal', position: 'insideTopRight', fontSize: 8, fill: '#34d399' }}
          />
          <ReferenceLine
            y={marker.alarmAt}
            stroke="#f87171"
            strokeDasharray="4 2"
            strokeOpacity={0.5}
            label={{ value: 'Alarm', position: 'insideTopRight', fontSize: 8, fill: '#f87171' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={marker.color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={(props) => <AlarmDot {...props} marker={marker} />}
            activeDot={{ r: 4, fill: marker.color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
