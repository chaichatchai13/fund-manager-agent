import React, { useEffect, useRef, useState } from 'react'
import { ThetaFlowLogo } from './ThetaFlowLogo'
import type { ChatMessage, OptionPosition } from '../types'

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
  display: 'flex',
  flexDirection: 'column',
  height: 620,
}

const QUICK_PROMPTS = [
  'Summarize my portfolio',
  'Show open positions',
  'Scan now',
  'Create a rule',
  'Research TSLA',
  'Weekly performance',
]

const GREEN = '#3fb950'
const RED = '#f85149'

interface PendingOrder {
  id: string
  symbol: string
  order_type: string
  quantity: number
  limit_price: number | null
  status: string
  is_gtc: boolean
}

interface ChatPaneProps {
  prefillMessage?: string
  onPrefillConsumed?: () => void
  positions?: OptionPosition[]
  account?: { portfolio_value: number | null; buying_power: number | null } | null
}

// ── Portfolio context builder ──────────────────────────────────────────────────
function buildPortfolioContext(
  positions: OptionPosition[],
  orders: PendingOrder[],
  account: { portfolio_value: number | null; buying_power: number | null } | null
): object[] {
  const fmt = (n: number | null) =>
    n == null ? 'unknown' : `$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const lines: string[] = []

  // Account summary
  lines.push('=== PORTFOLIO SNAPSHOT ===')
  lines.push(`Portfolio value: ${fmt(account?.portfolio_value ?? null)}`)
  lines.push(`Buying power: ${fmt(account?.buying_power ?? null)}`)

  // Open positions
  const open = positions.filter(p => p.status === 'OPEN')
  const closing = positions.filter(p => p.status === 'CLOSING')
  lines.push(`\nOPEN POSITIONS (${open.length}):`)
  if (open.length === 0) {
    lines.push('  None')
  } else {
    for (const p of open) {
      const pnlPct = p.unrealized_pnl != null && p.total_credit > 0
        ? ` (${((p.unrealized_pnl / p.total_credit) * 100).toFixed(1)}%)`
        : ''
      lines.push(
        `  ${p.underlying_symbol} — $${p.strike} ${p.expiration_date} × ${p.contracts} contract${p.contracts !== 1 ? 's' : ''}` +
        ` | Entry: ${fmt(p.premium_received)} | Now: ${fmt(p.current_price)} | P&L: ${p.unrealized_pnl != null ? (p.unrealized_pnl >= 0 ? '+' : '') + fmt(p.unrealized_pnl) + pnlPct : '—'}`
      )
    }
  }

  if (closing.length > 0) {
    lines.push(`\nCLOSING POSITIONS (${closing.length}):`)
    for (const p of closing) {
      lines.push(`  ${p.underlying_symbol} — $${p.strike} ${p.expiration_date} × ${p.contracts} contracts [CLOSING]`)
    }
  }

  // Pending orders
  const pending = orders.filter(o => ['PENDING', 'WORKING', 'AWAITING_PARENT_ORDER'].includes(o.status))
  lines.push(`\nPENDING ORDERS (${pending.length}):`)
  if (pending.length === 0) {
    lines.push('  None')
  } else {
    for (const o of pending) {
      lines.push(`  ${o.symbol} — ${o.order_type} × ${o.quantity} | Limit: ${fmt(o.limit_price)} | ${o.is_gtc ? 'GTC' : 'DAY'} [${o.status}]`)
    }
  }

  const totalCredit = open.reduce((s, p) => s + p.total_credit, 0)
  const totalPnl = open.reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0)
  lines.push(`\nSUMMARY: Total premium collected: ${fmt(totalCredit)} | Unrealized P&L: ${totalPnl >= 0 ? '+' : ''}${fmt(totalPnl)}`)

  return [
    {
      role: 'user',
      content: `${lines.join('\n')}\n\nThis is my current portfolio state. Use this as context for all my questions.`,
    },
    {
      role: 'assistant',
      content: `Got it — I can see your full portfolio: ${open.length} open position${open.length !== 1 ? 's' : ''}${pending.length > 0 ? `, ${pending.length} pending order${pending.length !== 1 ? 's' : ''}` : ''}${account?.buying_power != null ? `, ${fmt(account.buying_power)} buying power` : ''}. What would you like to do?`,
    },
  ]
}

export function ChatPane({ prefillMessage, onPrefillConsumed, positions = [], account = null }: ChatPaneProps = {}) {
  const [pendingOrders, setPendingOrders] = useState<PendingOrder[]>([])
  const contextRef = useRef<{ positions: OptionPosition[]; orders: PendingOrder[]; account: typeof account }>({ positions: [], orders: [], account: null })

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Hey! I'm your ThetaFlow agent — your personal automated trading system.\n\nHere's what I can do for you:\n\n📉 Sell Puts & 📈 Covered Calls — create rules, run scans, manage positions, roll ITM trades\n📊 Market Data — live quotes, option chains, IV rank for any symbol\n🛒 Direct Trading — buy/sell shares or options on demand\n🔍 Research — web search, stock news, analyst targets, earnings dates\n📣 Social Intel — summaries of what your favourite X accounts are saying about stocks\n\nI already have your current portfolio loaded as context — just ask!\n\nWhat would you like to do?",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiMessages, setApiMessages] = useState<object[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  // Fetch pending orders once on mount
  useEffect(() => {
    fetch('/api/orders?limit=50')
      .then(r => r.ok ? r.json() : [])
      .then(setPendingOrders)
      .catch(() => {})
  }, [])

  // Re-inject portfolio context whenever positions, orders, or account change
  useEffect(() => {
    const prev = contextRef.current
    const posChanged = positions.length !== prev.positions.length ||
      positions.some((p, i) => p.id !== prev.positions[i]?.id || p.unrealized_pnl !== prev.positions[i]?.unrealized_pnl)
    const ordChanged = pendingOrders.length !== prev.orders.length
    const accChanged = account?.buying_power !== prev.account?.buying_power

    if (!posChanged && !ordChanged && !accChanged) return
    contextRef.current = { positions, orders: pendingOrders, account }
    setApiMessages(buildPortfolioContext(positions, pendingOrders, account))
  }, [positions, pendingOrders, account])

  // Pre-fill input when triggered from another tab
  useEffect(() => {
    if (prefillMessage) {
      setInput(prefillMessage)
      onPrefillConsumed?.()
    }
  }, [prefillMessage, onPrefillConsumed])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const userText = (text ?? input).trim()
    if (!userText || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userText }])
    setLoading(true)

    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages, user_message: userText }),
      })
      const data = await res.json()
      setApiMessages(data.messages || [])
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error contacting agent. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  // Portfolio status chip shown in header
  const open = positions.filter(p => p.status === 'OPEN')
  const totalPnl = open.reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0)
  const pnlColor = totalPnl >= 0 ? GREEN : RED
  const hasPortfolio = positions.length > 0 || account != null

  return (
    <div style={CARD}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ThetaFlowLogo size={32} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: '#e6edf3', fontWeight: 700, fontSize: 15 }}>
              Theta<span style={{ color: '#3fb950' }}>Flow</span>
              <span style={{ marginLeft: 8, background: '#1a3028', color: '#3fb950', fontSize: 10, padding: '1px 7px', borderRadius: 4, fontWeight: 600, verticalAlign: 'middle' }}>Agent</span>
            </div>
            <div style={{ color: '#8b949e', fontSize: 11, marginTop: 1 }}>
              Sell Puts · Covered Calls · Automated income
            </div>
          </div>
          {/* Live portfolio chip */}
          {hasPortfolio && (
            <div style={{
              flexShrink: 0, textAlign: 'right',
              background: '#21262d', border: '1px solid #30363d',
              borderRadius: 8, padding: '4px 10px', fontSize: 11,
            }}>
              <div style={{ color: '#8b949e' }}>{open.length} position{open.length !== 1 ? 's' : ''}</div>
              {open.length > 0 && (
                <div style={{ color: pnlColor, fontWeight: 700 }}>
                  {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toFixed(2)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '80%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              background: msg.role === 'user' ? '#1f6feb' : '#21262d',
              color: msg.role === 'user' ? '#fff' : '#e6edf3',
              fontSize: 13,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '10px 14px',
              borderRadius: '16px 16px 16px 4px',
              background: '#21262d',
              color: '#8b949e',
              fontSize: 13,
            }}>
              <span style={{ animation: 'pulse 1.2s infinite' }}>Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div style={{ padding: '8px 16px', display: 'flex', flexWrap: 'wrap', gap: 6, borderTop: '1px solid #21262d', flexShrink: 0 }}>
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => sendMessage(p)}
            disabled={loading}
            style={{
              background: '#21262d',
              color: '#58a6ff',
              border: '1px solid #30363d',
              borderRadius: 6,
              padding: '3px 10px',
              fontSize: 11,
              cursor: 'pointer',
              transition: 'background 0.15s',
              fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#30363d')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#21262d')}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #30363d', display: 'flex', gap: 8, flexShrink: 0 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder="Ask me anything about your portfolio…"
          disabled={loading}
          style={{
            flex: 1,
            padding: '9px 14px',
            fontSize: 13,
            background: '#21262d',
            border: '1px solid #30363d',
            borderRadius: 8,
            color: '#e6edf3',
            outline: 'none',
            fontFamily: 'inherit',
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
          onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')}
        />
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          style={{
            padding: '9px 18px',
            background: loading || !input.trim() ? '#21262d' : '#1f6feb',
            color: loading || !input.trim() ? '#484f58' : '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
            fontFamily: 'inherit',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
