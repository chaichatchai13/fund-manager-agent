import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { OptionPosition } from './types'
import { ChatPane } from './components/ChatPane'
import { LoginPage } from './components/LoginPage'
import { LandingPage } from './components/LandingPage'
import { PnlChart } from './components/PnlChart'
import { PositionsTable } from './components/PositionsTable'
import { RulesPanel } from './components/RulesPanel'
import { AccountHoldings } from './components/AccountHoldings'
import { SettingsPanel } from './components/SettingsPanel'
import { AlertsPanel } from './components/AlertsPanel'
import { SocialIntelTab } from './components/SocialIntelTab'
import { ThetaFlowLogo } from './components/ThetaFlowLogo'
import { useAuth } from './hooks/useAuth'
import { useWebSocket } from './hooks/useWebSocket'
import { usePushNotifications } from './hooks/usePushNotifications'
import type { PerformanceSummary } from './types'

type Tab = 'dashboard' | 'positions' | 'rules' | 'chat' | 'social' | 'alerts' | 'settings'

// ── Design tokens ──────────────────────────────────────────────────────────────
const BG = '#0d1117'
const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const GREEN = '#3fb950'
const RED = '#f85149'
const BLUE_BTN = '#1f6feb'

// ── Mobile detection hook ─────────────────────────────────────────────────────
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])
  return isMobile
}

export default function App() {
  const { authenticated, loading: authLoading, recheck, logout } = useAuth()
  const [showLogin, setShowLogin] = useState(false)

  if (authLoading) return null
  if (!authenticated) {
    if (showLogin) return <LoginPage onLogin={recheck} />
    return <LandingPage onSignIn={() => setShowLogin(true)} />
  }
  return <Dashboard logout={logout} />
}

const AUTO_REFRESH_MS = 15 * 60 * 1000  // 15 minutes
const PULL_THRESHOLD = 70               // px to pull before triggering refresh

function Dashboard({ logout }: { logout: () => void }) {
  const isMobile = useIsMobile()
  const [tab, setTab] = useState<Tab>('dashboard')
  const { positions, connected, setPositions } = useWebSocket()
  const [summary, setSummary] = useState<PerformanceSummary | null>(null)
  const [account, setAccount] = useState<{ portfolio_value: number | null; buying_power: number | null; cash_balance: number | null; available_funds: number | null; sell_put_buying_power: number | null } | null>(null)
  const [chatPrefill, setChatPrefill] = useState<string | undefined>(undefined)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Pull-to-refresh tracking refs
  const touchStartY = useRef(0)
  const [pullProgress, setPullProgress] = useState(0)  // 0–1
  const refreshFnRef = useRef<() => Promise<void>>(async () => {})

  usePushNotifications()

  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent<{ message: string }>).detail?.message
      if (msg) { setChatPrefill(msg); setTab('chat') }
    }
    window.addEventListener('open-chat', handler)
    return () => window.removeEventListener('open-chat', handler)
  }, [])

  const refreshPositions = useCallback(async () => {
    const [res1, res2] = await Promise.all([
      fetch('/api/positions?status=OPEN'),
      fetch('/api/positions?status=CLOSING'),
    ])
    if (res1.ok && res2.ok) {
      const [open, closing] = await Promise.all([res1.json(), res2.json()])
      setPositions([...open, ...closing])
    }
  }, [setPositions])

  const refresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        fetch('/api/performance/summary?period=today').then(r => r.json()).then(setSummary).catch(() => {}),
        fetch('/api/account').then(r => r.json()).then(setAccount).catch(() => {}),
        refreshPositions(),
      ])
    } finally {
      setIsRefreshing(false)
    }
  }, [refreshPositions])

  // Keep refreshFnRef current so the touch handler always calls the latest version
  useEffect(() => { refreshFnRef.current = refresh }, [refresh])

  // Initial data fetch
  useEffect(() => { refresh() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // 15-minute full auto-refresh (positions + performance + account)
  useEffect(() => {
    const id = setInterval(() => { refreshFnRef.current() }, AUTO_REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  // 90-second account refresh — keeps buying power / portfolio value in the header current
  useEffect(() => {
    const id = setInterval(() => {
      fetch('/api/account').then(r => r.ok ? r.json() : null).then(d => { if (d) setAccount(d) }).catch(() => {})
    }, 90_000)
    return () => clearInterval(id)
  }, [])

  // Pull-to-refresh touch handlers
  useEffect(() => {
    const onTouchStart = (e: TouchEvent) => {
      if (window.scrollY === 0) touchStartY.current = e.touches[0].clientY
    }
    const onTouchMove = (e: TouchEvent) => {
      if (touchStartY.current === 0) return
      const delta = e.touches[0].clientY - touchStartY.current
      if (delta > 0 && window.scrollY === 0) {
        setPullProgress(Math.min(delta / PULL_THRESHOLD, 1))
      }
    }
    const onTouchEnd = () => {
      setPullProgress(p => {
        if (p >= 1) refreshFnRef.current()
        return 0
      })
      touchStartY.current = 0
    }
    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: true })
    document.addEventListener('touchend', onTouchEnd)
    return () => {
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchmove', onTouchMove)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [])

  const closePosition = async (positionId: string) => {
    const price = prompt('Enter limit price for buy-to-close (leave blank for auto):')
    const body: Record<string, number> = {}
    if (price) body.limit_price = parseFloat(price)
    await fetch(`/api/positions/${positionId}/close`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  }

  const deletePosition = async (positionId: string) => {
    await fetch(`/api/positions/${positionId}`, { method: 'DELETE' })
    setPositions(prev => prev.filter((p: OptionPosition) => p.id !== positionId))
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

  const openPositions = positions.filter(p => p.status === 'OPEN' || p.status === 'CLOSING')
  const totalCredit = openPositions.reduce((sum, p) => sum + p.total_credit, 0)
  const unrealizedPnl = openPositions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0)
  const portfolioValue = account?.portfolio_value ?? null
  // Use sell_put_buying_power (conservative, cash-based) for display.
  // If Schwab returns a margin account, raw buying_power may be 2× actual cash.
  const buyingPower = account?.sell_put_buying_power ?? account?.buying_power ?? null
  const isBuyingPowerInflated = account != null &&
    account.buying_power != null && account.sell_put_buying_power != null &&
    account.buying_power > (account.sell_put_buying_power * 1.15)
  const dayPnl = summary?.total_pnl ?? null

  const fmt = (n: number | null, signed = false) =>
    n == null ? '—' : `${signed && n >= 0 ? '+' : ''}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  // Mobile: short labels to fit the tab bar
  const tabs: { id: Tab; label: string; mobileLabel: string }[] = [
    { id: 'dashboard',  label: 'Dashboard',    mobileLabel: '⊞ Home'     },
    { id: 'positions',  label: `Positions (${openPositions.length})`, mobileLabel: `📋 Pos (${openPositions.length})` },
    { id: 'rules',      label: 'Rules',         mobileLabel: '⚙ Rules'   },
    { id: 'chat',       label: 'Agent Chat',    mobileLabel: '💬 Chat'    },
    { id: 'social',     label: 'Social Intel',  mobileLabel: '📡 Social'  },
    { id: 'alerts',     label: 'Alerts',        mobileLabel: '🔔 Alerts'  },
    { id: 'settings',   label: 'Settings',      mobileLabel: '⚙ Config'  },
  ]

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: isMobile ? '8px 12px' : '8px 16px',
    borderRadius: 6,
    fontSize: isMobile ? 12 : 13,
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: active ? BLUE_BTN : '#21262d',
    color: active ? '#fff' : MUTED,
    transition: 'all 0.15s',
    fontFamily: 'inherit',
    whiteSpace: 'nowrap',
    flexShrink: 0,
  })

  return (
    <div style={{ minHeight: '100vh', background: BG, fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* ── Pull-to-refresh indicator ── */}
      {(pullProgress > 0 || isRefreshing) && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          height: isRefreshing ? 44 : `${pullProgress * 44}px`,
          background: '#1f6feb',
          overflow: 'hidden',
          transition: isRefreshing ? 'none' : 'height 0.1s',
        }}>
          <span style={{
            color: '#fff', fontSize: 13, fontWeight: 600,
            opacity: pullProgress >= 1 || isRefreshing ? 1 : pullProgress,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ display: 'inline-block', animation: isRefreshing ? 'spin 1s linear infinite' : 'none', fontSize: 16 }}>
              {isRefreshing ? '↻' : pullProgress >= 1 ? '↓ Release to refresh' : '↓ Pull to refresh'}
            </span>
            {isRefreshing && 'Refreshing…'}
          </span>
        </div>
      )}

      {/* ── Header ── */}
      <header style={{
        background: CARD_BG,
        borderBottom: `1px solid ${BORDER}`,
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}>
        {/* Top row: Logo + stats + sign out */}
        <div style={{
          padding: isMobile ? '10px 16px' : '10px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <ThetaFlowLogo size={isMobile ? 26 : 32} />
            <span style={{ color: '#fff', fontWeight: 700, fontSize: isMobile ? 16 : 18, letterSpacing: '-0.3px' }}>
              Theta<span style={{ color: GREEN }}>Flow</span>
            </span>
            <span style={{
              background: connected ? '#1a3028' : '#21262d',
              color: connected ? GREEN : MUTED,
              fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
            }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>

          {/* Stats row (desktop: inline | mobile: compact) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 12 : 20, fontSize: 13 }}>
            <HeaderStat label="Portfolio" value={fmt(portfolioValue)} isMobile={isMobile} />
            {!isMobile && (
              <HeaderStat label="Day P&L" value={fmt(dayPnl, true)}
                valueColor={dayPnl == null ? '#e6edf3' : dayPnl >= 0 ? GREEN : RED} isMobile={false} />
            )}
            {!isMobile && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}
                title={isBuyingPowerInflated
                  ? `Margin account: Schwab reports $${(account?.buying_power ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} margin BP — showing available cash instead`
                  : 'Available for trading (cash-secured)'}
              >
                <HeaderStat label={isBuyingPowerInflated ? 'Cash Avail.' : 'Buying Power'} value={fmt(buyingPower)} isMobile={false} />
                {isBuyingPowerInflated && (
                  <span style={{ fontSize: 10, color: '#8b949e', marginTop: -4 }}>margin acct</span>
                )}
              </div>
            )}
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? GREEN : RED,
              display: 'inline-block',
              animation: connected ? 'pulse 2s infinite' : 'none',
              flexShrink: 0,
            }} />
            <button onClick={logout} style={{
              background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6,
              color: MUTED, fontSize: 12, padding: '4px 10px',
              cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = '#e6edf3')}
              onMouseLeave={e => (e.currentTarget.style.color = MUTED)}
            >
              {isMobile ? '↩' : 'Sign out'}
            </button>
          </div>
        </div>

        {/* Mobile: compact stats bar */}
        {isMobile && (
          <div style={{
            display: 'flex', gap: 0, borderTop: `1px solid #21262d`,
          }}>
            {[
              { label: 'Day P&L', value: fmt(dayPnl, true), color: dayPnl == null ? '#e6edf3' : dayPnl >= 0 ? GREEN : RED },
              { label: isBuyingPowerInflated ? 'Cash Avail.' : 'Buying Power', value: fmt(buyingPower), color: '#e6edf3' },
              { label: 'Positions', value: String(openPositions.length), color: '#e6edf3' },
            ].map((s, i) => (
              <div key={i} style={{
                flex: 1, textAlign: 'center', padding: '6px 8px',
                borderRight: i < 2 ? `1px solid #21262d` : 'none',
              }}>
                <div style={{ color: MUTED, fontSize: 10 }}>{s.label}</div>
                <div style={{ color: s.color, fontWeight: 700, fontSize: 13 }}>{s.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Nav tabs — horizontally scrollable on mobile */}
        <nav style={{
          display: 'flex',
          gap: 4,
          padding: isMobile ? '8px 12px' : '0 24px 10px',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'none',
          borderTop: isMobile ? `1px solid #21262d` : 'none',
        }}>
          {tabs.map(t => (
            <button key={t.id} style={tabBtnStyle(tab === t.id)} onClick={() => setTab(t.id)}>
              {isMobile ? t.mobileLabel : t.label}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Main content ── */}
      <main style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: isMobile ? '12px' : '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: isMobile ? 12 : 20,
      }}>

        {/* ── DASHBOARD ── */}
        {tab === 'dashboard' && (
          <>
            {/* Stat cards: 2-col on mobile, 4-col on desktop */}
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: isMobile ? 10 : 16 }}>
              <StatCard label="Portfolio Value" value={fmt(portfolioValue)}
                sub={unrealizedPnl !== 0 ? `Unrealized: ${fmt(unrealizedPnl, true)}` : undefined}
                subColor={unrealizedPnl >= 0 ? GREEN : RED} />
              <StatCard label="Open Positions" value={String(openPositions.length)}
                sub={`${positions.filter(p => p.status === 'OPEN').length} open · ${positions.filter(p => p.status === 'CLOSING').length} closing`} />
              <StatCard label="Premium Collected" value={`$${totalCredit.toFixed(2)}`}
                sub={unrealizedPnl !== 0 ? `▲ ${fmt(unrealizedPnl, true)}` : undefined} subColor={GREEN} />
              <StatCard label="Win Rate" value={summary?.win_rate != null ? `${summary.win_rate}%` : '—'}
                sub={summary?.trades_closed != null ? `${summary.trades_closed} trades` : undefined} />
            </div>

            {/* Holdings + Chart: stacked on mobile */}
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 2fr', gap: isMobile ? 12 : 16 }}>
              <AccountHoldings />
              {!isMobile && <PnlChart />}
            </div>
            {isMobile && <PnlChart />}

            <PositionsTable positions={openPositions} connected={connected}
              onClosePosition={closePosition} onDeletePosition={deletePosition}
              onRollPosition={rollPosition} onReconcile={refreshPositions} />
          </>
        )}

        {tab === 'positions' && (
          <PositionsTable positions={positions} connected={connected}
            onClosePosition={closePosition} onDeletePosition={deletePosition}
            onRollPosition={rollPosition} onReconcile={refreshPositions} />
        )}

        {tab === 'rules'    && <RulesPanel />}
        {tab === 'chat'     && <ChatPane prefillMessage={chatPrefill} onPrefillConsumed={() => setChatPrefill(undefined)} positions={openPositions} account={account} />}
        {tab === 'social'   && <SocialIntelTab />}
        {tab === 'alerts'   && <AlertsPanel />}
        {tab === 'settings' && <SettingsPanel />}

      </main>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function HeaderStat({ label, value, valueColor, isMobile }: { label: string; value: string; valueColor?: string; isMobile: boolean }) {
  if (isMobile) return null  // Mobile stats shown in compact bar below
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ color: MUTED, fontSize: 11 }}>{label}</div>
      <div style={{ color: valueColor ?? '#e6edf3', fontWeight: 700, fontSize: 14 }}>{value}</div>
    </div>
  )
}

function StatCard({ label, value, sub, subColor }: { label: string; value: string; sub?: string; subColor?: string }) {
  return (
    <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '14px 16px' }}>
      <div style={{ color: MUTED, fontSize: 11, marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#e6edf3', fontSize: 20, fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ color: subColor ?? MUTED, fontSize: 11, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}
