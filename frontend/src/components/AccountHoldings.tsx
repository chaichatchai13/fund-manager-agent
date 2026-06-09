import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { AccountData, AccountHolding } from '../types'

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
}

const POLL_MS = 30_000   // refresh every 30 seconds

export function AccountHoldings() {
  const [data, setData] = useState<AccountData | null>(null)
  const [error, setError] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  const load = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true)
    try {
      const res = await fetch('/api/account')
      if (!res.ok) throw new Error('failed')
      setData(await res.json())
      setError(false)
      setLastUpdated(new Date())
    } catch {
      setError(true)
    } finally {
      if (isManual) setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
    timerRef.current = setInterval(() => load(), POLL_MS)
    return () => clearInterval(timerRef.current)
  }, [load])

  const equities = data?.holdings.filter((h) => h.asset_type === 'EQUITY') ?? []
  const options  = data?.holdings.filter((h) => h.asset_type === 'OPTION')  ?? []
  const shortOptions = options.filter((h) => h.quantity < 0)
  const longOptions  = options.filter((h) => h.quantity >= 0)

  const fmtVal = (n: number | null | undefined) =>
    n == null ? '—' : `$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const sectionLabel: React.CSSProperties = {
    color: '#8b949e', fontSize: 11, textTransform: 'uppercase',
    letterSpacing: '0.05em', marginBottom: 8,
  }

  return (
    <div style={CARD} className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Account Holdings</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {lastUpdated && (
            <span style={{ color: '#484f58', fontSize: 11 }}>
              {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            style={{
              background: 'none', border: '1px solid #30363d', borderRadius: 6,
              color: refreshing ? '#484f58' : '#58a6ff', fontSize: 11, padding: '3px 9px',
              cursor: refreshing ? 'default' : 'pointer', fontFamily: 'inherit',
            }}
          >
            {refreshing ? '↻ …' : '↻ Refresh'}
          </button>
          <span style={{ color: '#58a6ff', fontSize: 12 }}>Schwab Live</span>
        </div>
      </div>

      {error && (
        <div style={{ color: '#8b949e', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>
          Could not load account data
        </div>
      )}
      {!error && !data && (
        <div style={{ color: '#8b949e', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>Loading…</div>
      )}

      {data && (
        <>
          {/* ── Equities ── */}
          <div style={sectionLabel}>Equities</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 16 }}>
            {equities.length === 0
              ? <div style={{ color: '#484f58', fontSize: 12 }}>No equity positions</div>
              : equities.map((h) => (
                  <EquityRow key={h.symbol} h={h} fmtVal={fmtVal} />
                ))}
          </div>

          {/* ── Short Options ── */}
          {(shortOptions.length > 0 || longOptions.length === 0) && (
            <div style={{ borderTop: '1px solid #21262d', paddingTop: 12, marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ ...sectionLabel, marginBottom: 0 }}>Short Options</div>
                {shortOptions.length > 0 && (
                  <span style={{ color: '#58a6ff', fontSize: 11, fontWeight: 600 }}>
                    {shortOptions.reduce((sum, h) => sum + Math.abs(h.quantity), 0)} contract{shortOptions.reduce((sum, h) => sum + Math.abs(h.quantity), 0) !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {shortOptions.length === 0
                  ? <div style={{ color: '#484f58', fontSize: 12 }}>No short option positions</div>
                  : shortOptions.map((h) => <OptionRow key={h.symbol} h={h} />)}
              </div>
            </div>
          )}

          {/* ── Long Options (rare, but show them too) ── */}
          {longOptions.length > 0 && (
            <div style={{ borderTop: '1px solid #21262d', paddingTop: 12, marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ ...sectionLabel, marginBottom: 0 }}>Long Options</div>
                <span style={{ color: '#58a6ff', fontSize: 11, fontWeight: 600 }}>
                  {longOptions.reduce((sum, h) => sum + Math.abs(h.quantity), 0)} contract{longOptions.reduce((sum, h) => sum + Math.abs(h.quantity), 0) !== 1 ? 's' : ''}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {longOptions.map((h) => <OptionRow key={h.symbol} h={h} />)}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function EquityRow({
  h,
  fmtVal,
}: {
  h: AccountHolding
  fmtVal: (n: number | null | undefined) => string
}) {
  const qty = Math.abs(h.quantity)
  const costBasis = h.average_price != null ? h.average_price * qty : null
  const marketValue = h.market_value ?? null
  const totalGain = costBasis != null && marketValue != null ? marketValue - costBasis : null
  const totalGainPct = costBasis != null && costBasis > 0 && totalGain != null
    ? (totalGain / costBasis) * 100
    : null
  const gainColor = totalGain == null ? '#8b949e' : totalGain >= 0 ? '#3fb950' : '#f85149'
  const gainArrow = totalGain == null ? '' : totalGain >= 0 ? '▲' : '▼'

  return (
    <div className="flex items-center justify-between" style={{ padding: '6px 0', borderBottom: '1px solid #21262d' }}>
      <div>
        <div style={{ fontWeight: 500, color: '#e6edf3', fontSize: 13 }}>{h.symbol}</div>
        <div style={{ color: '#8b949e', fontSize: 11 }}>
          {qty.toLocaleString()} shares
          {h.average_price != null && (
            <span style={{ marginLeft: 6 }}>· avg ${h.average_price.toFixed(2)}</span>
          )}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500 }}>{fmtVal(marketValue)}</div>
        <div style={{ color: gainColor, fontSize: 11 }}>
          {totalGain != null
            ? `${gainArrow} ${totalGainPct != null ? `${Math.abs(totalGainPct).toFixed(1)}%` : ''} (${totalGain >= 0 ? '+' : '−'}$${Math.abs(totalGain).toFixed(2)})`
            : '—'}
        </div>
      </div>
    </div>
  )
}

function parseOptionSymbol(symbol: string): { underlying: string; strike: number | null; putCall: 'CALL' | 'PUT' | null } {
  // Schwab option symbols: "IREN 260508C00060000" (space) or "IREN_260508C00060000" (underscore)
  // OCC format: UNDERLYING[6-digit date][C/P][8-digit strike * 1000]
  const m = symbol.match(/^([A-Z]+)[\s_](\d{6})([CP])(\d{8})$/)
  if (m) {
    const underlying = m[1]
    const putCall = m[3] === 'C' ? 'CALL' : 'PUT'
    const strike = parseInt(m[4], 10) / 1000
    return { underlying, strike, putCall }
  }
  // Fallback: split on space or underscore
  const underlying = symbol.split(/[\s_]/)[0] || symbol.replace(/\d.*/, '').trim()
  const pcMatch = symbol.match(/[CP]\d{8}/)
  const putCall = pcMatch ? (pcMatch[0].startsWith('C') ? 'CALL' : 'PUT') : null
  const strikeMatch = symbol.match(/[CP](\d{8})/)
  const strike = strikeMatch ? parseInt(strikeMatch[1], 10) / 1000 : null
  return { underlying, strike, putCall }
}

function OptionRow({ h }: { h: AccountHolding }) {
  const isShort = h.quantity < 0
  const contracts = Math.abs(h.quantity)
  const isExpired = h.dte != null && h.dte < 0

  // Parse symbol to extract underlying, strike, put/call reliably
  const parsed = parseOptionSymbol(h.symbol)
  const strike = h.strike ?? parsed.strike
  const putCallRaw = h.put_call ?? parsed.putCall
  const underlying = parsed.underlying
  const isCall = putCallRaw === 'CALL'
  const putCall = putCallRaw ?? 'OPTION'
  const optionTypeLabel = isCall ? 'C' : 'P'
  const typeColor = isCall ? '#58a6ff' : '#d2a8ff'

  // P&L
  const entryCredit = (h.average_price ?? 0) * contracts * 100
  const currentValue = Math.abs(h.market_value ?? 0)
  const profit = isShort ? entryCredit - currentValue : currentValue - entryCredit
  const profitPct = entryCredit > 0 ? (profit / entryCredit) * 100 : null
  const profitColor = profit >= 0 ? '#3fb950' : '#f85149'

  const dteLabel = h.dte != null
    ? (h.dte < 0 ? `Expired ${Math.abs(h.dte)}d ago` : `${h.dte} DTE`)
    : ''
  const label = h.expiration_date
    ? `${h.expiration_date.slice(5)} · ${dteLabel} · ${contracts} contract${contracts !== 1 ? 's' : ''}`
    : ''

  return (
    <div className="flex items-center justify-between" style={{
      padding: '6px 0', borderBottom: '1px solid #21262d',
      opacity: isExpired ? 0.55 : 1,
    }}>
      <div>
        <div style={{ fontWeight: 500, fontSize: 13, display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
          <span style={{ color: typeColor }}>{underlying}</span>
          <span style={{ color: '#e6edf3' }}>
            {strike != null ? `$${strike % 1 === 0 ? strike.toFixed(0) : strike}` : ''}{optionTypeLabel}
          </span>
          <span style={{
            fontSize: 10, padding: '1px 5px', borderRadius: 4, fontWeight: 600,
            background: isCall ? '#1f2d45' : '#2d1f45', color: typeColor,
          }}>
            {isShort ? 'SHORT' : 'LONG'} {putCall}
          </span>
          {isExpired && (
            <span style={{ fontSize: 10, padding: '1px 5px', borderRadius: 4, fontWeight: 600, background: '#21262d', color: '#8b949e' }}>
              SETTLING
            </span>
          )}
        </div>
        <div style={{ color: '#8b949e', fontSize: 11 }}>{label}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ color: profitColor, fontSize: 13, fontWeight: 500 }}>
          {profit >= 0 ? '+' : '−'}${Math.abs(profit).toFixed(0)}
        </div>
        <div style={{ color: '#8b949e', fontSize: 11 }}>
          {profitPct != null ? `${profitPct.toFixed(0)}% ${isShort ? 'profit' : 'gain'}` : '—'}
        </div>
      </div>
    </div>
  )
}
