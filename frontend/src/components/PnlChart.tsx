import React, { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailySnapshot, PerformanceSummary } from '../types'

const PERIODS = ['today', 'week', 'month', 'all_time'] as const
type Period = (typeof PERIODS)[number]

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Today',
  week: '1W',
  month: '1M',
  all_time: 'All',
}

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
  padding: 20,
}

export function PnlChart() {
  const [period, setPeriod] = useState<Period>('month')
  const [summary, setSummary] = useState<PerformanceSummary | null>(null)
  const [dailyData, setDailyData] = useState<DailySnapshot[]>([])

  useEffect(() => {
    fetch(`/api/performance/summary?period=${period}`)
      .then((r) => r.json())
      .then(setSummary)
      .catch(console.error)
  }, [period])

  useEffect(() => {
    const end = new Date().toISOString().slice(0, 10)
    const start = new Date(Date.now() - 90 * 864e5).toISOString().slice(0, 10)
    fetch(`/api/performance/daily?start_date=${start}&end_date=${end}`)
      .then((r) => r.json())
      .then(setDailyData)
      .catch(console.error)
  }, [])

  const fmt = (n: number | null) =>
    n == null
      ? '—'
      : `${n >= 0 ? '+' : '-'}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const pnlColor = (n: number | null) => (n == null ? '#8b949e' : n >= 0 ? '#3fb950' : '#f85149')

  const chartData = dailyData.map((d) => ({
    date: d.snapshot_date,
    realized: d.cumulative_realized_pnl,
    daily: d.daily_realized_pnl,
  }))

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '4px 12px',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: active ? '#1f6feb' : '#21262d',
    color: active ? '#fff' : '#8b949e',
    transition: 'all 0.15s',
  })

  return (
    <div style={CARD}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Cumulative P&L</h2>
        <div style={{ display: 'flex', gap: 4 }}>
          {PERIODS.map((p) => (
            <button key={p} style={tabStyle(period === p)} onClick={() => setPeriod(p)}>
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        <StatItem label="Realized" value={fmt(summary?.realized_pnl ?? null)} color={pnlColor(summary?.realized_pnl ?? null)} />
        <StatItem label="Unrealized" value={fmt(summary?.unrealized_pnl ?? null)} color={pnlColor(summary?.unrealized_pnl ?? null)} />
        <StatItem
          label="Total"
          value={`${fmt(summary?.total_pnl ?? null)}${summary?.pnl_pct != null ? ` (${summary.pnl_pct.toFixed(1)}%)` : ''}`}
          color={pnlColor(summary?.total_pnl ?? null)}
          large
        />
        <StatItem
          label="Win Rate"
          value={summary?.win_rate != null ? `${summary.win_rate}%` : '—'}
          color="#e6edf3"
        />
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3fb950" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#3fb950" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#8b949e' }}
            tickFormatter={(v) => v.slice(5)}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#8b949e' }}
            tickFormatter={(v) => `$${v}`}
            axisLine={false}
            tickLine={false}
            width={55}
          />
          <Tooltip
            contentStyle={{ background: '#1c2128', border: '1px solid #30363d', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#8b949e' }}
            itemStyle={{ color: '#3fb950' }}
            formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Cumulative P&L']}
          />
          <Area
            type="monotone"
            dataKey="realized"
            stroke="#3fb950"
            fill="url(#greenGrad)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3fb950', stroke: '#0d1117', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {chartData.length === 0 && (
        <div style={{ textAlign: 'center', color: '#484f58', fontSize: 13, marginTop: 8 }}>
          No performance data yet. Data appears after the first daily snapshot.
        </div>
      )}
    </div>
  )
}

function StatItem({
  label,
  value,
  color,
  large,
}: {
  label: string
  value: string
  color: string
  large?: boolean
}) {
  return (
    <div>
      <div style={{ color: '#8b949e', fontSize: 11 }}>{label}</div>
      <div style={{ color, fontWeight: 700, fontSize: large ? 16 : 14, marginTop: 2 }}>{value}</div>
    </div>
  )
}
