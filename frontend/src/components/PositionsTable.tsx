import React, { useState } from 'react'
import type { OptionPosition } from '../types'

interface Props {
  positions: OptionPosition[]
  connected: boolean
  onClosePosition: (positionId: string) => void
  onDeletePosition: (positionId: string) => void
  onRollPosition?: (positionId: string) => void
  onReconcile?: () => void
}

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
  overflow: 'hidden',
}

const TH: React.CSSProperties = {
  padding: '10px 16px',
  color: '#8b949e',
  fontSize: 11,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  textAlign: 'left',
  background: '#161b22',
  borderBottom: '1px solid #21262d',
  whiteSpace: 'nowrap',
}

const TD: React.CSSProperties = {
  padding: '12px 16px',
  borderBottom: '1px solid #21262d',
  fontSize: 13,
  verticalAlign: 'middle',
}

type Filter = 'all' | 'open' | 'closing'

export function PositionsTable({ positions, connected, onClosePosition, onDeletePosition, onRollPosition, onReconcile }: Props) {
  const [filter, setFilter] = useState<Filter>('open')
  const [syncing, setSyncing] = useState(false)

  const handleReconcile = async () => {
    setSyncing(true)
    await fetch('/api/positions/reconcile', { method: 'POST' })
    setSyncing(false)
    onReconcile?.()
  }

  const openCount = positions.filter((p) => p.status === 'OPEN').length
  const closingCount = positions.filter((p) => p.status === 'CLOSING').length

  const filtered = positions.filter((p) => {
    if (filter === 'open') return p.status === 'OPEN'
    if (filter === 'closing') return p.status === 'CLOSING'
    return true
  })

  const fmt = (n: number | null, prefix = '') =>
    n == null
      ? '—'
      : `${prefix}${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const profitPct = (p: OptionPosition): number | null => {
    if (p.unrealized_pnl == null || p.total_credit <= 0) return null
    return (p.unrealized_pnl / p.total_credit) * 100
  }

  const barColor = (pct: number | null) => {
    if (pct == null || pct < 0) return '#f85149'
    if (pct >= 60) return '#3fb950'
    return '#d29922'
  }

  const statusBadge = (status: string) => {
    const styles: Record<string, React.CSSProperties> = {
      OPEN: { background: '#1a3028', color: '#3fb950' },
      CLOSING: { background: '#2d2a14', color: '#d29922' },
      CLOSED: { background: '#21262d', color: '#8b949e' },
      EXPIRED: { background: '#21262d', color: '#8b949e' },
      ASSIGNED: { background: '#2d1e2e', color: '#f85149' },
    }
    return (
      <span style={{
        ...( styles[status] ?? styles.CLOSED),
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
      }}>
        {status}
      </span>
    )
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '5px 14px',
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
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid #30363d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Open Positions</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: connected ? '#3fb950' : '#f85149', display: 'inline-block', animation: connected ? 'pulse 2s infinite' : 'none' }} />
            <span style={{ color: '#8b949e', fontSize: 12 }}>{connected ? 'Live' : 'Reconnecting…'}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <button style={tabStyle(filter === 'open')} onClick={() => setFilter('open')}>
            Active ({openCount})
          </button>
          <button style={tabStyle(filter === 'closing')} onClick={() => setFilter('closing')}>
            Closing ({closingCount})
          </button>
          <button style={tabStyle(filter === 'all')} onClick={() => setFilter('all')}>
            All
          </button>
          <button
            onClick={handleReconcile}
            disabled={syncing}
            style={{
              marginLeft: 6,
              padding: '5px 12px', fontSize: 12, fontWeight: 500,
              background: 'none',
              border: '1px solid #30363d',
              borderRadius: 6,
              color: syncing ? '#484f58' : '#58a6ff',
              cursor: syncing ? 'default' : 'pointer',
              fontFamily: 'inherit',
              transition: 'all 0.15s',
            }}
            title="Sync positions with Schwab account — removes phantom positions and marks expired/closed ones"
          >
            {syncing ? '↻ Syncing…' : '↻ Sync Schwab'}
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={TH}>Symbol</th>
              <th style={{ ...TH, textAlign: 'left' }}>Strike / Exp</th>
              <th style={{ ...TH, textAlign: 'right' }}>Contracts</th>
              <th style={{ ...TH, textAlign: 'right' }}>Entry</th>
              <th style={{ ...TH, textAlign: 'right' }}>Current</th>
              <th style={{ ...TH, textAlign: 'right' }}>P&L $</th>
              <th style={{ ...TH, textAlign: 'right' }}>P&L %</th>
              <th style={{ ...TH }}>Progress</th>
              <th style={TH}>Status</th>
              <th style={TH}></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={10} style={{ ...TD, textAlign: 'center', color: '#484f58', padding: '32px 16px' }}>
                  No positions
                </td>
              </tr>
            )}
            {filtered.map((p) => {
              const pct = profitPct(p)
              const barW = pct == null ? 0 : Math.min(100, Math.max(0, (pct / 75) * 100))
              const pnlPositive = (p.unrealized_pnl ?? 0) >= 0

              return (
                <tr key={p.id} style={{ transition: 'background 0.1s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#1c2128')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Symbol */}
                  <td style={TD}>
                    <div style={{ fontWeight: 600, color: '#e6edf3' }}>{p.underlying_symbol}</div>
                    <div style={{ color: '#8b949e', fontSize: 11, marginTop: 1 }}>{p.option_symbol}</div>
                  </td>

                  {/* Strike / Exp */}
                  <td style={TD}>
                    <div style={{ color: '#e6edf3' }}>${p.strike} / {p.expiration_date}</div>
                    <div style={{ color: '#8b949e', fontSize: 11, marginTop: 1 }}>{p.dte_at_entry} DTE at entry</div>
                  </td>

                  {/* Contracts */}
                  <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>{p.contracts}</td>

                  {/* Entry */}
                  <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>${fmt(p.premium_received)}</td>

                  {/* Current */}
                  <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>
                    {p.current_price != null ? `$${fmt(p.current_price)}` : '—'}
                  </td>

                  {/* P&L $ */}
                  <td style={{ ...TD, textAlign: 'right', color: pnlPositive ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                    {p.unrealized_pnl != null ? `${pnlPositive ? '+' : '-'}$${fmt(p.unrealized_pnl)}` : '—'}
                  </td>

                  {/* P&L % */}
                  <td style={{ ...TD, textAlign: 'right', color: pnlPositive ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                    {pct != null ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%` : '—'}
                  </td>

                  {/* Progress bar */}
                  <td style={{ ...TD, minWidth: 120 }}>
                    <div style={{ background: '#21262d', borderRadius: 4, height: 6, width: 90 }}>
                      <div style={{
                        background: barColor(pct),
                        width: `${barW}%`,
                        height: 6,
                        borderRadius: 4,
                        transition: 'width 0.4s',
                      }} />
                    </div>
                    <div style={{ color: '#8b949e', fontSize: 10, marginTop: 3 }}>
                      {pct != null ? `${pct.toFixed(0)}% → 75% target` : '—'}
                    </div>
                  </td>

                  {/* Status */}
                  <td style={TD}>{statusBadge(p.status)}</td>

                  {/* Action */}
                  <td style={TD}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
                      {p.status === 'OPEN' && onRollPosition && (
                        <button
                          onClick={() => {
                            if (confirm(`Roll "${p.option_symbol}"? This will BTC the current position and STO a new OTM option at the closest premium.`))
                              onRollPosition(p.id)
                          }}
                          style={{ color: '#d29922', fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
                          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
                          title="Roll this position to a new OTM strike at a similar premium"
                        >
                          Roll
                        </button>
                      )}
                      {(p.status === 'OPEN' || p.status === 'CLOSING') && (
                        <button
                          onClick={() => onClosePosition(p.id)}
                          style={{ color: '#f85149', fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
                          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
                        >
                          Close
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (confirm(`Remove "${p.option_symbol}" from ThetaFlow? Use this only for phantom positions that were never filled in Schwab.`))
                            onDeletePosition(p.id)
                        }}
                        style={{ color: '#484f58', fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#8b949e')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}
                      >
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
