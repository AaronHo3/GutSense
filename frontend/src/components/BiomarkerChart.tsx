
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
    key: 'hemoglobin_fit_ng_ml',
    label: 'Hemoglobin FIT (Occult Blood)',
    unit: 'ng/mL',
    normalMax: 10,
    alarmAt: 100,
    color: '#ef4444',
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
    key: 'mmp9_ng_ml',
    label: 'MMP-9 (Matrix Metalloproteinase-9)',
    unit: 'ng/mL',
    normalMax: 30,
    alarmAt: 150,
    color: '#8b5cf6',
  },
  {
    key: 'mpo_ng_ml',
    label: 'MPO (Myeloperoxidase)',
    unit: 'ng/mL',
    normalMax: 100,
    alarmAt: 500,
    color: '#ec4899',
  },
  {
    key: 'mmp8_ng_ml',
    label: 'MMP-8 (Neutrophil Collagenase)',
    unit: 'ng/mL',
    normalMax: 30,
    alarmAt: 150,
    color: '#06b6d4',
  },
  {
    key: 'fibrinogen_ng_ml',
    label: 'Fibrinogen (Fecal)',
    unit: 'ng/mL',
    normalMax: 100,
    alarmAt: 400,
    color: '#f59e0b',
  },
  {
    key: 'haptoglobin_ug_g',
    label: 'Haptoglobin (Fecal)',
    unit: 'µg/g',
    normalMax: 50,
    alarmAt: 200,
    color: '#10b981',
  },
  {
    key: 'pgrp_s_ng_ml',
    label: 'PGRP-S (Innate Immunity)',
    unit: 'ng/mL',
    normalMax: 20,
    alarmAt: 100,
    color: '#3b82f6',
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
          <YAxis tick={{ fontSize: 9, fill: '#64748b' }} tickLine={false} domain={[0, 'auto']} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }}
            formatter={(v) => [`${Number(v).toFixed(marker.decimals ?? 1)} ${marker.unit}`, marker.label]}
          />
          <ReferenceLine
            y={marker.normalMax}
            stroke="#34d399"
            strokeDasharray="4 2"
            strokeOpacity={0.6}
            label={{ value: `Normal ≤${marker.normalMax}`, position: 'insideTopRight', fontSize: 8, fill: '#34d399' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={marker.color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, fill: marker.color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
