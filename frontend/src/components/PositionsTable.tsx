import React, { useEffect, useState } from 'react'
import type { OptionPosition, Order } from '../types'

interface Props {
  positions: OptionPosition[]
  connected: boolean
  onClosePosition: (positionId: string) => void
  onDeletePosition: (positionId: string) => void
  onRollPosition?: (positionId: string) => void
  onReconcile?: () => void
}

// ── Design tokens ──────────────────────────────────────────────────────────────
const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const ROW_HOVER = '#1c2128'
const GREEN = '#3fb950'
const RED = '#f85149'
const YELLOW = '#d29922'
const BLUE = '#58a6ff'

const CARD: React.CSSProperties = { background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }
const TH: React.CSSProperties = { padding: '10px 16px', color: MUTED, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', textAlign: 'left', background: CARD_BG, borderBottom: '1px solid #21262d', whiteSpace: 'nowrap' }
const TD: React.CSSProperties = { padding: '12px 16px', borderBottom: '1px solid #21262d', fontSize: 13, verticalAlign: 'middle' }

type Tab = 'active' | 'closing' | 'pending' | 'closed'
type SortField = 'date' | 'symbol' | 'pnl'
type SortDir = 'asc' | 'desc'

// ── Helpers ────────────────────────────────────────────────────────────────────
const fmt = (n: number | null) =>
  n == null ? '—' : Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function relDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, React.CSSProperties> = {
    OPEN:      { background: '#1a3028', color: GREEN },
    CLOSING:   { background: '#2d2a14', color: YELLOW },
    CLOSED:    { background: '#21262d', color: MUTED },
    EXPIRED:   { background: '#21262d', color: MUTED },
    ASSIGNED:  { background: '#2d1e2e', color: RED },
    PENDING:   { background: '#1a1f2e', color: '#79c0ff' },
    WORKING:   { background: '#2d2a14', color: YELLOW },
    FILLED:    { background: '#1a3028', color: GREEN },
    CANCELLED: { background: '#21262d', color: MUTED },
    REJECTED:  { background: '#2d1e2e', color: RED },
  }
  return (
    <span style={{ ...(map[status] ?? map.CLOSED), padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
      {status}
    </span>
  )
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 11px', borderRadius: 6, fontSize: 12, fontWeight: 500,
      cursor: 'pointer', border: 'none', fontFamily: 'inherit', whiteSpace: 'nowrap',
      background: active ? '#1f6feb' : '#21262d',
      color: active ? '#fff' : MUTED,
      transition: 'all 0.15s',
    }}>{children}</button>
  )
}

// ── Mobile: position card ──────────────────────────────────────────────────────
function PositionCard({
  p, showActions, onClose, onDelete, onRoll,
}: {
  p: OptionPosition; showActions: boolean
  onClose?: () => void; onDelete?: () => void; onRoll?: () => void
}) {
  const isClosed = ['CLOSED', 'EXPIRED', 'ASSIGNED'].includes(p.status)
  const pnl = isClosed
    ? (p.current_price != null ? (p.premium_received - p.current_price) * p.contracts * 100 : null)
    : p.unrealized_pnl
  const pct = pnl != null && p.total_credit > 0 ? (pnl / p.total_credit) * 100 : null
  const pnlPositive = (pnl ?? 0) >= 0
  const barW = pct == null ? 0 : Math.min(100, Math.max(0, (pct / 75) * 100))
  const barColor = pct == null || pct < 0 ? RED : pct >= 60 ? GREEN : YELLOW

  return (
    <div style={{
      background: '#1c2128', border: `1px solid ${BORDER}`, borderRadius: 10, padding: '12px 14px',
    }}>
      {/* Symbol + status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 16 }}>{p.underlying_symbol}</span>
          <span style={{ color: MUTED, fontSize: 11 }}>{p.dte_at_entry} DTE · {p.contracts} contract{p.contracts !== 1 ? 's' : ''}</span>
        </div>
        <StatusBadge status={p.status} />
      </div>

      {/* Strike / expiry */}
      <div style={{ color: '#58a6ff', fontSize: 12, fontFamily: 'monospace', marginBottom: 10 }}>
        ${p.strike} · {p.expiration_date}
      </div>

      {/* P&L row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 8, fontSize: 13 }}>
        <span style={{ color: MUTED }}>Entry <span style={{ color: '#e6edf3', fontWeight: 600 }}>${fmt(p.premium_received)}</span></span>
        {p.current_price != null && (
          <span style={{ color: MUTED }}>
            {isClosed ? 'Close' : 'Now'}{' '}
            <span style={{ color: '#e6edf3', fontWeight: 600 }}>${fmt(p.current_price)}</span>
          </span>
        )}
      </div>

      {pnl != null && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isClosed ? 0 : 5 }}>
            <span style={{ color: pnlPositive ? GREEN : RED, fontWeight: 700, fontSize: 14 }}>
              {pnlPositive ? '+' : '-'}${fmt(Math.abs(pnl))}
            </span>
            {pct != null && (
              <span style={{ color: pnlPositive ? GREEN : RED, fontWeight: 600, fontSize: 13 }}>
                {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
              </span>
            )}
          </div>
          {!isClosed && (
            <>
              <div style={{ background: '#21262d', borderRadius: 3, height: 5, marginBottom: 3 }}>
                <div style={{ background: barColor, width: `${barW}%`, height: 5, borderRadius: 3, transition: 'width 0.4s' }} />
              </div>
              <div style={{ color: '#484f58', fontSize: 10, marginBottom: 10 }}>
                {pct != null ? `${pct.toFixed(0)}% toward 75% target` : '—'}
              </div>
            </>
          )}
        </>
      )}

      <div style={{ color: '#484f58', fontSize: 11, marginTop: 10, marginBottom: showActions ? 10 : 0 }}>
        {isClosed && p.closed_at
          ? `Closed ${relDate(p.closed_at)} · opened ${relDate(p.opened_at)}`
          : `Opened ${relDate(p.opened_at)}`}
      </div>

      {/* Actions */}
      {showActions && (
        <div style={{ display: 'flex', gap: 8, borderTop: `1px solid #21262d`, paddingTop: 10 }}>
          {p.status === 'OPEN' && onRoll && (
            <button onClick={() => { if (confirm(`Roll "${p.option_symbol}"?`)) onRoll() }}
              style={{
                flex: 1, padding: '8px 0', fontSize: 13, fontWeight: 600,
                background: '#2d2a14', color: YELLOW, border: `1px solid ${YELLOW}44`,
                borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
              }}>↻ Roll</button>
          )}
          {(p.status === 'OPEN' || p.status === 'CLOSING') && onClose && (
            <button onClick={onClose}
              style={{
                flex: 1, padding: '8px 0', fontSize: 13, fontWeight: 600,
                background: '#2d1414', color: RED, border: `1px solid ${RED}44`,
                borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
              }}>✕ Close</button>
          )}
          <button onClick={() => { if (confirm(`Remove "${p.option_symbol}" from ThetaFlow?`)) onDelete?.() }}
            style={{
              padding: '8px 12px', fontSize: 13, fontWeight: 600,
              background: '#21262d', color: '#484f58', border: `1px solid ${BORDER}`,
              borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
            }}>⊗</button>
        </div>
      )}
    </div>
  )
}

// ── Mobile: order card ─────────────────────────────────────────────────────────
function OrderCard({ o }: { o: Order }) {
  return (
    <div style={{
      background: '#1c2128', border: `1px solid ${BORDER}`, borderRadius: 10, padding: '12px 14px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 14, fontFamily: 'monospace' }}>{o.symbol}</span>
        <StatusBadge status={o.status} />
      </div>
      <div style={{ display: 'flex', gap: 14, fontSize: 12, flexWrap: 'wrap' }}>
        <span style={{ color: MUTED }}>Qty <span style={{ color: '#e6edf3', fontWeight: 600 }}>{o.quantity}</span></span>
        <span style={{ color: MUTED }}>{o.order_type}</span>
        <span style={{ color: o.is_gtc ? '#79c0ff' : MUTED, fontWeight: 600 }}>{o.is_gtc ? 'GTC' : 'DAY'}</span>
        {o.limit_price != null && <span style={{ color: MUTED }}>Limit <span style={{ color: '#e6edf3', fontWeight: 600 }}>${fmt(o.limit_price)}</span></span>}
        {o.fill_price != null && <span style={{ color: GREEN, fontWeight: 600 }}>Filled ${fmt(o.fill_price)}</span>}
      </div>
      <div style={{ color: '#484f58', fontSize: 11, marginTop: 5 }}>{relDate(o.created_at)}</div>
    </div>
  )
}

// ── Filter bar ─────────────────────────────────────────────────────────────────
function FilterBar({
  symbolFilter, onSymbolChange,
  dateFrom, dateTo, onDateFrom, onDateTo,
  sortField, sortDir, onSort,
  showDateFilter, isMobile,
}: {
  symbolFilter: string; onSymbolChange: (v: string) => void
  dateFrom: string; dateTo: string; onDateFrom: (v: string) => void; onDateTo: (v: string) => void
  sortField: SortField; sortDir: SortDir; onSort: (f: SortField) => void
  showDateFilter: boolean; isMobile: boolean
}) {
  const sortBtn = (field: SortField, label: string) => {
    const active = sortField === field
    return (
      <button onClick={() => onSort(field)} style={{
        padding: '4px 8px', fontSize: 11, borderRadius: 5,
        border: `1px solid ${active ? BLUE : BORDER}`,
        background: active ? '#1f2d3d' : '#21262d',
        color: active ? BLUE : MUTED,
        cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap',
      }}>
        {label} {active ? (sortDir === 'asc' ? '↑' : '↓') : ''}
      </button>
    )
  }

  return (
    <div style={{
      padding: isMobile ? '10px 12px' : '10px 16px',
      borderBottom: `1px solid #21262d`,
      display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center',
      background: '#0d1117',
    }}>
      <input
        value={symbolFilter}
        onChange={e => onSymbolChange(e.target.value)}
        placeholder="Filter ticker…"
        style={{
          padding: '5px 10px', fontSize: 12, background: '#21262d',
          border: `1px solid ${BORDER}`, borderRadius: 6, color: '#e6edf3',
          outline: 'none', width: isMobile ? '100%' : 150, fontFamily: 'inherit', boxSizing: 'border-box',
        }}
        onFocus={e => (e.currentTarget.style.borderColor = BLUE)}
        onBlur={e => (e.currentTarget.style.borderColor = BORDER)}
      />

      {showDateFilter && (
        <>
          <input type="date" value={dateFrom} onChange={e => onDateFrom(e.target.value)}
            style={{ padding: '5px 8px', fontSize: 12, background: '#21262d', border: `1px solid ${BORDER}`, borderRadius: 6, color: '#e6edf3', outline: 'none', fontFamily: 'inherit', colorScheme: 'dark', flex: 1 }} />
          <input type="date" value={dateTo} onChange={e => onDateTo(e.target.value)}
            style={{ padding: '5px 8px', fontSize: 12, background: '#21262d', border: `1px solid ${BORDER}`, borderRadius: 6, color: '#e6edf3', outline: 'none', fontFamily: 'inherit', colorScheme: 'dark', flex: 1 }} />
          {(dateFrom || dateTo) && (
            <button onClick={() => { onDateFrom(''); onDateTo('') }} style={{ fontSize: 11, color: MUTED, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>✕ Clear</button>
          )}
        </>
      )}

      <div style={{ marginLeft: isMobile ? 0 : 'auto', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <span style={{ color: MUTED, fontSize: 11, alignSelf: 'center' }}>Sort:</span>
        {sortBtn('date', 'Date')}
        {sortBtn('symbol', 'Symbol')}
        {showDateFilter && sortBtn('pnl', 'P&L')}
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export function PositionsTable({ positions, connected, onClosePosition, onDeletePosition, onRollPosition, onReconcile }: Props) {
  const [tab, setTab] = useState<Tab>('active')
  const [syncing, setSyncing] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const [closedPositions, setClosedPositions] = useState<OptionPosition[]>([])
  const [closedLoading, setClosedLoading] = useState(false)
  const [pendingOrders, setPendingOrders] = useState<Order[]>([])
  const [ordersLoading, setOrdersLoading] = useState(false)

  const [symbolFilter, setSymbolFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortField, setSortField] = useState<SortField>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  useEffect(() => {
    if (tab !== 'closed') return
    setClosedLoading(true)
    Promise.all([
      fetch('/api/positions?status=CLOSED').then(r => r.json()),
      fetch('/api/positions?status=EXPIRED').then(r => r.json()),
      fetch('/api/positions?status=ASSIGNED').then(r => r.json()),
    ]).then(([closed, expired, assigned]) => {
      setClosedPositions([...closed, ...expired, ...assigned])
    }).catch(() => {}).finally(() => setClosedLoading(false))
  }, [tab])

  useEffect(() => {
    if (tab !== 'pending') return
    setOrdersLoading(true)
    fetch('/api/orders?limit=100')
      .then(r => r.json())
      .then(setPendingOrders)
      .catch(() => {})
      .finally(() => setOrdersLoading(false))
  }, [tab])

  const handleReconcile = async () => {
    setSyncing(true)
    await fetch('/api/positions/reconcile', { method: 'POST' })
    setSyncing(false)
    onReconcile?.()
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('desc') }
  }

  const activeCount = positions.filter(p => p.status === 'OPEN').length
  const closingCount = positions.filter(p => p.status === 'CLOSING').length
  const pendingCount = pendingOrders.filter(o => ['PENDING', 'WORKING', 'AWAITING_PARENT_ORDER'].includes(o.status)).length

  const applyFilters = (list: OptionPosition[]): OptionPosition[] => {
    let out = [...list]
    if (symbolFilter) out = out.filter(p => p.underlying_symbol.toUpperCase().includes(symbolFilter.toUpperCase()))
    if (dateFrom) out = out.filter(p => { const d = p.closed_at ?? p.opened_at; return d >= dateFrom })
    if (dateTo) out = out.filter(p => { const d = p.closed_at ?? p.opened_at; return d <= dateTo + 'T23:59:59' })
    out.sort((a, b) => {
      let cmp = 0
      if (sortField === 'date') cmp = new Date(a.opened_at).getTime() - new Date(b.opened_at).getTime()
      else if (sortField === 'symbol') cmp = a.underlying_symbol.localeCompare(b.underlying_symbol)
      else if (sortField === 'pnl') cmp = (a.unrealized_pnl ?? 0) - (b.unrealized_pnl ?? 0)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return out
  }

  const applyOrderFilters = (list: Order[]): Order[] => {
    let out = [...list]
    if (symbolFilter) out = out.filter(o => o.symbol.toUpperCase().includes(symbolFilter.toUpperCase()))
    out.sort((a, b) => {
      const cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortDir === 'asc' ? cmp : -cmp
    })
    return out
  }

  const activeRows = applyFilters(positions.filter(p => p.status === 'OPEN'))
  const closingRows = applyFilters(positions.filter(p => p.status === 'CLOSING'))
  const closedRows = applyFilters(closedPositions)
  const orderRows = applyOrderFilters(pendingOrders)

  const barColor = (pct: number | null) => pct == null || pct < 0 ? RED : pct >= 60 ? GREEN : YELLOW

  // For OPEN/CLOSING: use unrealized_pnl from Schwab stream.
  // For CLOSED/EXPIRED/ASSIGNED: compute realized P&L from entry vs closing price.
  const computePnl = (p: OptionPosition): number | null => {
    const isClosed = ['CLOSED', 'EXPIRED', 'ASSIGNED'].includes(p.status)
    if (isClosed) {
      if (p.current_price == null) return null
      // Sold option: realized = (entry - close) * contracts * 100
      return (p.premium_received - p.current_price) * p.contracts * 100
    }
    return p.unrealized_pnl
  }

  const computePct = (p: OptionPosition, pnl: number | null): number | null => {
    if (pnl == null || p.total_credit <= 0) return null
    return (pnl / p.total_credit) * 100
  }

  // ── Desktop table row ──────────────────────────────────────────────────────
  const renderPositionRow = (p: OptionPosition, showActions: boolean, isHistory = false) => {
    const pnl = computePnl(p)
    const pct = computePct(p, pnl)
    const barW = pct == null ? 0 : Math.min(100, Math.max(0, (pct / 75) * 100))
    const pnlPositive = (pnl ?? 0) >= 0
    return (
      <tr key={p.id}
        onMouseEnter={e => (e.currentTarget.style.background = ROW_HOVER)}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        style={{ transition: 'background 0.1s' }}
      >
        <td style={TD}>
          <div style={{ fontWeight: 600, color: '#e6edf3' }}>{p.underlying_symbol}</div>
          <div style={{ color: MUTED, fontSize: 11, marginTop: 1 }}>{p.option_symbol}</div>
        </td>
        <td style={TD}>
          <div style={{ color: '#e6edf3' }}>${p.strike} / {p.expiration_date}</div>
          <div style={{ color: MUTED, fontSize: 11, marginTop: 1 }}>{p.dte_at_entry} DTE at entry</div>
        </td>
        <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>{p.contracts}</td>
        <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>${fmt(p.premium_received)}</td>
        <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>
          {p.current_price != null ? `$${fmt(p.current_price)}` : '—'}
        </td>
        <td style={{ ...TD, textAlign: 'right', color: pnlPositive ? GREEN : RED, fontWeight: 600 }}>
          {pnl != null ? `${pnlPositive ? '+' : '-'}$${fmt(Math.abs(pnl))}` : '—'}
        </td>
        <td style={{ ...TD, textAlign: 'right', color: pnlPositive ? GREEN : RED, fontWeight: 600 }}>
          {pct != null ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%` : '—'}
        </td>
        {!isHistory && (
        <td style={{ ...TD, minWidth: 110 }}>
          <div style={{ background: '#21262d', borderRadius: 4, height: 6, width: 90 }}>
            <div style={{ background: barColor(pct), width: `${barW}%`, height: 6, borderRadius: 4, transition: 'width 0.4s' }} />
          </div>
          <div style={{ color: MUTED, fontSize: 10, marginTop: 3 }}>
            {pct != null ? `${pct.toFixed(0)}% → 75%` : '—'}
          </div>
        </td>
        )}
        <td style={TD}>
          {isHistory && p.closed_at ? (
            <>
              <div style={{ color: MUTED, fontSize: 11 }}>{relDate(p.closed_at)}</div>
              <div style={{ color: '#484f58', fontSize: 10, marginTop: 1 }}>opened {relDate(p.opened_at)}</div>
            </>
          ) : (
            <div style={{ color: MUTED, fontSize: 11 }}>{relDate(p.opened_at)}</div>
          )}
        </td>
        <td style={TD}><StatusBadge status={p.status} /></td>
        {showActions && (
          <td style={TD}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {p.status === 'OPEN' && onRollPosition && (
                <button onClick={() => { if (confirm(`Roll "${p.option_symbol}"?`)) onRollPosition(p.id) }}
                  style={{ color: YELLOW, fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}
                  onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                  onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}>Roll</button>
              )}
              {(p.status === 'OPEN' || p.status === 'CLOSING') && (
                <button onClick={() => onClosePosition(p.id)}
                  style={{ color: RED, fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}
                  onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                  onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}>Close</button>
              )}
              <button onClick={() => { if (confirm(`Remove "${p.option_symbol}" from ThetaFlow?`)) onDeletePosition(p.id) }}
                style={{ color: '#484f58', fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}
                onMouseEnter={e => (e.currentTarget.style.color = MUTED)}
                onMouseLeave={e => (e.currentTarget.style.color = '#484f58')}>Remove</button>
            </div>
          </td>
        )}
      </tr>
    )
  }

  // ── Position section (desktop = table, mobile = cards) ─────────────────────
  const renderPositionsSection = (rows: OptionPosition[], showActions: boolean, emptyMsg: string, loading = false, isHistory = false) => {
    if (loading) return <div style={{ padding: '32px 16px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>Loading…</div>
    if (rows.length === 0) return <div style={{ padding: '32px 16px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>{emptyMsg}</div>

    if (isMobile) {
      return (
        <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rows.map(p => (
            <PositionCard
              key={p.id}
              p={p}
              showActions={showActions}
              onClose={() => onClosePosition(p.id)}
              onDelete={() => onDeletePosition(p.id)}
              onRoll={onRollPosition ? () => onRollPosition(p.id) : undefined}
            />
          ))}
        </div>
      )
    }

    return (
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={TH}>Symbol</th>
              <th style={TH}>Strike / Exp</th>
              <th style={{ ...TH, textAlign: 'right' }}>Contracts</th>
              <th style={{ ...TH, textAlign: 'right' }}>Entry</th>
              <th style={{ ...TH, textAlign: 'right' }}>{isHistory ? 'Close' : 'Current'}</th>
              <th style={{ ...TH, textAlign: 'right' }}>P&L $</th>
              <th style={{ ...TH, textAlign: 'right' }}>P&L %</th>
              {!isHistory && <th style={TH}>Progress</th>}
              <th style={TH}>Date</th>
              <th style={TH}>Status</th>
              {showActions && <th style={TH}></th>}
            </tr>
          </thead>
          <tbody>
            {rows.map(p => renderPositionRow(p, showActions, isHistory))}
          </tbody>
        </table>
      </div>
    )
  }

  // ── Orders section ─────────────────────────────────────────────────────────
  const renderOrdersSection = () => {
    if (ordersLoading) return <div style={{ padding: '32px 16px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>Loading…</div>
    if (orderRows.length === 0) return <div style={{ padding: '32px 16px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>No orders found</div>

    if (isMobile) {
      return (
        <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {orderRows.map(o => <OrderCard key={o.id} o={o} />)}
        </div>
      )
    }

    return (
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={TH}>Symbol</th>
              <th style={{ ...TH, textAlign: 'right' }}>Qty</th>
              <th style={TH}>Type</th>
              <th style={{ ...TH, textAlign: 'right' }}>Limit Price</th>
              <th style={{ ...TH, textAlign: 'right' }}>Fill Price</th>
              <th style={TH}>Duration</th>
              <th style={TH}>Placed</th>
              <th style={TH}>Status</th>
            </tr>
          </thead>
          <tbody>
            {orderRows.map(o => (
              <tr key={o.id}
                onMouseEnter={e => (e.currentTarget.style.background = ROW_HOVER)}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                style={{ transition: 'background 0.1s' }}
              >
                <td style={TD}><span style={{ fontWeight: 600, color: '#e6edf3' }}>{o.symbol}</span></td>
                <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>{o.quantity}</td>
                <td style={TD}><span style={{ color: MUTED, fontSize: 12 }}>{o.order_type}</span></td>
                <td style={{ ...TD, textAlign: 'right', color: '#e6edf3' }}>{o.limit_price != null ? `$${fmt(o.limit_price)}` : '—'}</td>
                <td style={{ ...TD, textAlign: 'right', color: o.fill_price != null ? GREEN : MUTED }}>
                  {o.fill_price != null ? `$${fmt(o.fill_price)}` : '—'}
                </td>
                <td style={TD}>
                  <span style={{ color: o.is_gtc ? '#79c0ff' : MUTED, fontSize: 12 }}>
                    {o.is_gtc ? 'GTC' : 'DAY'}
                  </span>
                </td>
                <td style={{ ...TD, color: MUTED, fontSize: 12 }}>{relDate(o.created_at)}</td>
                <td style={TD}><StatusBadge status={o.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div style={CARD}>
      {/* ── Header ── */}
      <div style={{
        padding: isMobile ? '12px 14px' : '14px 20px',
        borderBottom: `1px solid ${BORDER}`,
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        {/* Title row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Positions</h2>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: connected ? GREEN : RED, display: 'inline-block', animation: connected ? 'pulse 2s infinite' : 'none' }} />
            <span style={{ color: MUTED, fontSize: 12 }}>{connected ? 'Live' : 'Reconnecting…'}</span>
          </div>
          <button
            onClick={handleReconcile} disabled={syncing}
            style={{ padding: '5px 10px', fontSize: 12, fontWeight: 500, background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, color: syncing ? '#484f58' : BLUE, cursor: syncing ? 'default' : 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}
            title="Sync positions with Schwab account"
          >
            {syncing ? '↻ Syncing…' : isMobile ? '↻ Sync' : '↻ Sync Schwab'}
          </button>
        </div>

        {/* Tabs — scrollable on mobile */}
        <div style={{ display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 2 }}>
          <TabBtn active={tab === 'active'} onClick={() => setTab('active')}>Active ({activeCount})</TabBtn>
          <TabBtn active={tab === 'closing'} onClick={() => setTab('closing')}>Closing ({closingCount})</TabBtn>
          <TabBtn active={tab === 'pending'} onClick={() => setTab('pending')}>
            Orders{pendingCount > 0 ? ` (${pendingCount})` : ''}
          </TabBtn>
          <TabBtn active={tab === 'closed'} onClick={() => setTab('closed')}>History</TabBtn>
        </div>
      </div>

      {/* ── Filter bar ── */}
      <FilterBar
        symbolFilter={symbolFilter} onSymbolChange={setSymbolFilter}
        dateFrom={dateFrom} dateTo={dateTo} onDateFrom={setDateFrom} onDateTo={setDateTo}
        sortField={sortField} sortDir={sortDir} onSort={handleSort}
        showDateFilter={tab === 'closed'} isMobile={isMobile}
      />

      {/* ── Content ── */}
      {tab === 'active'  && renderPositionsSection(activeRows,  true,  'No active positions')}
      {tab === 'closing' && renderPositionsSection(closingRows, true,  'No closing positions')}
      {tab === 'pending' && renderOrdersSection()}
      {tab === 'closed'  && renderPositionsSection(closedRows,  false, 'No closed positions', closedLoading, true)}
    </div>
  )
}
