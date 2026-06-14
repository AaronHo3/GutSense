
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
  { key: 'hemoglobin_fit_ng_ml', label: 'Hemoglobin FIT', unit: 'ng/mL', normalMax: 10, alarmAt: 100, color: '#1B1A17' },
  { key: 'calprotectin_ug_g', label: 'Calprotectin', unit: 'µg/g', normalMax: 50, alarmAt: 200, color: '#1B1A17' },
  { key: 'mmp9_ng_ml', label: 'MMP-9', unit: 'ng/mL', normalMax: 30, alarmAt: 150, color: '#1B1A17' },
  { key: 'mpo_ng_ml', label: 'MPO', unit: 'ng/mL', normalMax: 100, alarmAt: 500, color: '#1B1A17' },
  { key: 'mmp8_ng_ml', label: 'MMP-8', unit: 'ng/mL', normalMax: 30, alarmAt: 150, color: '#1B1A17' },
  { key: 'fibrinogen_ng_ml', label: 'Fibrinogen', unit: 'ng/mL', normalMax: 100, alarmAt: 400, color: '#1B1A17' },
  { key: 'haptoglobin_ug_g', label: 'Haptoglobin', unit: 'µg/g', normalMax: 50, alarmAt: 200, color: '#1B1A17' },
  { key: 'pgrp_s_ng_ml', label: 'PGRP-S', unit: 'ng/mL', normalMax: 20, alarmAt: 100, color: '#1B1A17' },
];

interface Props {
  readings: BiomarkerReading[];
  marker: MarkerConfig;
}

interface DataPoint {
  date: string;
  value: number;
}

const INK = '#1B1A17';
const LINE = '#E4DFD3';
const FAINT = '#8C8779';

const STATUS = {
  alarm:      { color: '#9E2B25', label: 'Alarm' },
  concerning: { color: '#9A7A24', label: 'Elevated' },
  normal:     { color: '#2F6B4F', label: 'Normal' },
};

export function BiomarkerChart({ readings, marker }: Props) {
  const data: DataPoint[] = readings.map(r => ({
    date: new Date(r.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: Number((r[marker.key] as number).toFixed(marker.decimals ?? 1)),
  }));

  const latestVal = data.length > 0 ? data[data.length - 1].value : null;
  const isAlarm = latestVal !== null && (marker.inverted ? latestVal < marker.alarmAt : latestVal > marker.alarmAt);
  const isConcerning = !isAlarm && latestVal !== null && (marker.inverted ? latestVal < marker.normalMax : latestVal > marker.normalMax);
  const status = isAlarm ? STATUS.alarm : isConcerning ? STATUS.concerning : STATUS.normal;

  const gradientId = `grad-${String(marker.key)}`;

  return (
    <div className="card px-5 pt-4 pb-3">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-serif text-ink leading-tight" style={{ fontSize: '1.0625rem', fontWeight: 440 }}>
            {marker.label}
          </h3>
          <p className="eyebrow mt-1">{marker.unit}</p>
        </div>
        {latestVal !== null && (
          <div className="text-right">
            <div className="font-mono tnum text-ink" style={{ fontSize: '1.25rem', fontWeight: 500, lineHeight: 1 }}>
              {latestVal.toFixed(marker.decimals ?? 1)}
            </div>
            <span className="font-mono uppercase" style={{ fontSize: '0.625rem', letterSpacing: '0.1em', color: status.color }}>
              {status.label}
            </span>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={132}>
        <AreaChart data={data} margin={{ top: 4, right: 6, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={INK} stopOpacity={0.08} />
              <stop offset="100%" stopColor={INK} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={LINE} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: FAINT, fontFamily: 'Spline Sans Mono' }}
            tickLine={false}
            axisLine={{ stroke: LINE }}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis
            tick={{ fontSize: 9, fill: FAINT, fontFamily: 'Spline Sans Mono' }}
            tickLine={false}
            axisLine={false}
            domain={[0, 'auto']}
            width={34}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 4, background: '#FCFBF8', border: '1px solid #D2CCBD', color: '#1B1A17', fontFamily: 'Spline Sans Mono' }}
            labelStyle={{ color: '#8C8779' }}
            formatter={(v) => [`${Number(v).toFixed(marker.decimals ?? 1)} ${marker.unit}`, marker.label]}
          />
          <ReferenceLine
            y={marker.normalMax}
            stroke={FAINT}
            strokeDasharray="3 3"
            label={{ value: `normal ≤${marker.normalMax}`, position: 'insideTopRight', fontSize: 8, fill: FAINT, fontFamily: 'Spline Sans Mono' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={INK}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 3, fill: INK }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
