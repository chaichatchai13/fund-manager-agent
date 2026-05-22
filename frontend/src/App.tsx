import React, { useEffect, useState } from 'react'
import type { OptionPosition } from './types'
import { ChatPane } from './components/ChatPane'
import { LoginPage } from './components/LoginPage'
import { PnlChart } from './components/PnlChart'
import { PositionsTable } from './components/PositionsTable'
import { RulesPanel } from './components/RulesPanel'
import { AccountHoldings } from './components/AccountHoldings'
import { SettingsPanel } from './components/SettingsPanel'
import { ThetaFlowLogo } from './components/ThetaFlowLogo'
import { useAuth } from './hooks/useAuth'
import { useWebSocket } from './hooks/useWebSocket'
import type { PerformanceSummary } from './types'

type Tab = 'dashboard' | 'positions' | 'rules' | 'chat' | 'settings'

// ── Design tokens ──────────────────────────────────────────────────────────────
const BG = '#0d1117'
const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const GREEN = '#3fb950'
const RED = '#f85149'
const BLUE_BTN = '#1f6feb'

export default function App() {
  const { authenticated, loading: authLoading, recheck, logout } = useAuth()

  // Show nothing while checking auth (avoids flash of login page on hard refresh)
  if (authLoading) return null

  // Show login page if not authenticated — main app not rendered (no API calls fire)
  if (!authenticated) return <LoginPage onLogin={recheck} />

  return <Dashboard logout={logout} />
}

function Dashboard({ logout }: { logout: () => void }) {
  const [tab, setTab] = useState<Tab>('dashboard')
  const { positions, connected, setPositions } = useWebSocket()
  const [summary, setSummary] = useState<PerformanceSummary | null>(null)
  const [account, setAccount] = useState<{ portfolio_value: number | null; buying_power: number | null } | null>(null)

  useEffect(() => {
    fetch('/api/performance/summary?period=today').then((r) => r.json()).then(setSummary).catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/api/account').then((r) => r.json()).then(setAccount).catch(() => {})
  }, [])

  const closePosition = async (positionId: string) => {
    const price = prompt('Enter limit price for buy-to-close (leave blank for auto):')
    const body: Record<string, number> = {}
    if (price) body.limit_price = parseFloat(price)
    await fetch(`/api/positions/${positionId}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  const deletePosition = async (positionId: string) => {
    await fetch(`/api/positions/${positionId}`, { method: 'DELETE' })
    setPositions((prev) => prev.filter((p: OptionPosition) => p.id !== positionId))
  }

  const rollPosition = async (positionId: string) => {
    const res = await fetch(`/api/positions/${positionId}/roll`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      alert(`Roll executed! New position ID: ${data.new_position_id}`)
      await refreshPositions()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
      alert(`Roll failed: ${err.detail}`)
    }
  }

  const refreshPositions = async () => {
    // Re-fetch only active positions after reconciliation (OPEN + CLOSING)
    const res = await fetch('/api/positions?status=OPEN')
    if (res.ok) {
      const open = await res.json()
      const res2 = await fetch('/api/positions?status=CLOSING')
      const closing = res2.ok ? await res2.json() : []
      setPositions([...open, ...closing])
    }
  }

  const openPositions = positions.filter((p) => p.status === 'OPEN' || p.status === 'CLOSING')
  const totalCredit = openPositions.reduce((sum, p) => sum + p.total_credit, 0)
  const unrealizedPnl = openPositions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0)

  const portfolioValue = account?.portfolio_value ?? null
  const buyingPower = account?.buying_power ?? null
  const dayPnl = summary?.total_pnl ?? null

  const fmt = (n: number | null, signed = false) =>
    n == null
      ? '—'
      : `${signed && n >= 0 ? '+' : ''}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const tabs: { id: Tab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'positions', label: `Positions (${openPositions.length})` },
    { id: 'rules', label: 'Rules' },
    { id: 'chat', label: 'Agent Chat' },
    { id: 'settings', label: 'Settings' },
  ]

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 16px',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: active ? BLUE_BTN : '#21262d',
    color: active ? '#fff' : MUTED,
    transition: 'all 0.15s',
    fontFamily: 'inherit',
  })

  return (
    <div style={{ minHeight: '100vh', background: BG, fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* ── Header ── */}
      <header style={{
        background: CARD_BG,
        borderBottom: `1px solid ${BORDER}`,
        position: 'sticky',
        top: 0,
        zIndex: 40,
        padding: '10px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ThetaFlowLogo size={32} />
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 18, letterSpacing: '-0.3px' }}>
            Theta<span style={{ color: '#3fb950' }}>Flow</span>
          </span>
          <span style={{ background: '#21262d', color: MUTED, fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* Nav tabs */}
        <nav style={{ display: 'flex', gap: 4 }}>
          {tabs.map((t) => (
            <button key={t.id} style={tabBtnStyle(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>

        {/* Header stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, fontSize: 13 }}>
          <HeaderStat label="Portfolio" value={fmt(portfolioValue)} />
          <HeaderStat
            label="Day P&L"
            value={fmt(dayPnl, true)}
            valueColor={dayPnl == null ? '#e6edf3' : dayPnl >= 0 ? GREEN : RED}
          />
          <HeaderStat label="Buying Power" value={fmt(buyingPower)} />
          {/* Live dot */}
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: connected ? GREEN : RED,
            display: 'inline-block',
            animation: connected ? 'pulse 2s infinite' : 'none',
          }} />
          <button
            onClick={logout}
            style={{
              background: 'none', border: '1px solid #30363d', borderRadius: 6,
              color: '#8b949e', fontSize: 12, padding: '4px 10px',
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#e6edf3')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#8b949e')}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main content ── */}
      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ── DASHBOARD ── */}
        {tab === 'dashboard' && (
          <>
            {/* Stat cards row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              <StatCard
                label="Total Portfolio Value"
                value={fmt(portfolioValue)}
                sub={unrealizedPnl !== 0 ? `Unrealized P&L: ${fmt(unrealizedPnl, true)}` : undefined}
                subColor={unrealizedPnl >= 0 ? GREEN : RED}
              />
              <StatCard
                label="Open Positions"
                value={String(openPositions.length)}
                sub={`${positions.filter((p) => p.status === 'OPEN').length} OPEN · ${positions.filter((p) => p.status === 'CLOSING').length} CLOSING`}
              />
              <StatCard
                label="Total Premium Collected"
                value={`$${totalCredit.toFixed(2)}`}
                sub={unrealizedPnl !== 0 ? `▲ Unrealized P&L: ${fmt(unrealizedPnl, true)}` : undefined}
                subColor={GREEN}
              />
              <StatCard
                label="Win Rate (All Time)"
                value={summary?.win_rate != null ? `${summary.win_rate}%` : '—'}
                sub={summary?.trades_closed != null ? `${summary.trades_closed} trades closed` : undefined}
              />
            </div>

            {/* Holdings + Chart row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16 }}>
              <AccountHoldings />
              <PnlChart />
            </div>

            {/* Positions table */}
            <PositionsTable positions={openPositions} connected={connected} onClosePosition={closePosition} onDeletePosition={deletePosition} onRollPosition={rollPosition} onReconcile={refreshPositions} />
          </>
        )}

        {/* ── POSITIONS ── */}
        {tab === 'positions' && (
          <PositionsTable positions={positions} connected={connected} onClosePosition={closePosition} onDeletePosition={deletePosition} onRollPosition={rollPosition} onReconcile={refreshPositions} />
        )}

        {/* ── RULES ── */}
        {tab === 'rules' && <RulesPanel />}

        {/* ── CHAT ── */}
        {tab === 'chat' && <ChatPane />}

        {/* ── SETTINGS ── */}
        {tab === 'settings' && <SettingsPanel />}

      </main>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function HeaderStat({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ color: MUTED, fontSize: 11 }}>{label}</div>
      <div style={{ color: valueColor ?? '#e6edf3', fontWeight: 700, fontSize: 14 }}>{value}</div>
    </div>
  )
}

function StatCard({
  label,
  value,
  sub,
  subColor,
}: {
  label: string
  value: string
  sub?: string
  subColor?: string
}) {
  return (
    <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '16px 18px' }}>
      <div style={{ color: MUTED, fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#e6edf3', fontSize: 22, fontWeight: 700 }}>{value}</div>
      {sub && (
        <div style={{ color: subColor ?? MUTED, fontSize: 12, marginTop: 4 }}>{sub}</div>
      )}
    </div>
  )
}

