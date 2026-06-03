import { useState } from 'react'
import { ThetaFlowLogo } from './ThetaFlowLogo'

const features = [
  {
    tag: 'Dashboard',
    title: 'Full Portfolio at a Glance',
    description:
      'See your portfolio value, buying power, day P&L, and cumulative performance chart — all live-synced from Schwab. Account holdings split into equities and short options with real-time profit tracking.',
    img: '/screenshots/dashboard.png',
    color: '#3fb950',
    icon: '📊',
  },
  {
    tag: 'Positions',
    title: 'Live Position Tracking',
    description:
      'Track every open option position with live P&L, progress toward your profit target, DTE, and status. One-click Roll or Close directly from the table — no need to open Schwab.',
    img: '/screenshots/positions.png',
    color: '#58a6ff',
    icon: '📈',
  },
  {
    tag: 'Rules Engine',
    title: 'Automated Trading Rules',
    description:
      'Set up sell-put and covered-call rules with strike range, DTE window, premium filter, implied volatility filter, and bid/ask fill price. ThetaFlow scans every 15 minutes and places orders automatically.',
    img: '/screenshots/rules.png',
    color: '#d2a8ff',
    icon: '⚙️',
  },
  {
    tag: 'Agent Chat',
    title: 'AI Trading Agent',
    description:
      'Ask questions, run scans, place trades, and analyse your portfolio in plain English. The agent has full context of your positions, rules, and live market data — powered by Claude.',
    img: '/screenshots/agent-chat.png',
    color: '#ffa657',
    icon: '🤖',
  },
  {
    tag: 'Social Intel',
    title: 'X Feed Intelligence',
    description:
      'Monitor your favourite traders on X, filtered by the stocks you care about. Every post is AI-summarised into an actionable insight. Ask the embedded agent to compare sentiment across accounts.',
    img: '/screenshots/social-intel.png',
    color: '#ff7b72',
    icon: '🔍',
  },
]

const stats = [
  { value: '15m', label: 'Scan interval' },
  { value: '100%', label: 'Win rate (1M)' },
  { value: '$0', label: 'Monthly platform fee' },
  { value: '24/7', label: 'Automated monitoring' },
]

export function LandingPage({ onSignIn }: { onSignIn: () => void }) {
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({})

  const handleImgError = (key: string) => {
    setImgErrors((prev) => ({ ...prev, [key]: true }))
  }

  return (
    <div style={{ background: '#0d1117', color: '#e6edf3', minHeight: '100vh', fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>

      {/* ── Nav ── */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 60, borderBottom: '1px solid #21262d',
        position: 'sticky', top: 0, background: 'rgba(13,17,23,0.9)',
        backdropFilter: 'blur(12px)', zIndex: 100,
      }}>
        <ThetaFlowLogo />
        <button
          onClick={onSignIn}
          style={{
            padding: '7px 20px', fontSize: 13, fontWeight: 600,
            background: '#1f6feb', color: '#fff', border: 'none',
            borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
            transition: 'background 0.15s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#388bfd')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#1f6feb')}
        >
          Sign in →
        </button>
      </nav>

      {/* ── Hero ── */}
      <section style={{ textAlign: 'center', padding: '80px 24px 60px' }}>
        <div style={{
          display: 'inline-block', background: '#1a3028', border: '1px solid #3fb95044',
          color: '#3fb950', fontSize: 12, fontWeight: 600, padding: '4px 12px',
          borderRadius: 20, marginBottom: 20, letterSpacing: '0.04em',
        }}>
          LIVE · Connected to Schwab
        </div>
        <h1 style={{
          fontSize: 'clamp(32px, 6vw, 64px)', fontWeight: 800, lineHeight: 1.15,
          margin: '0 auto 20px', maxWidth: 720,
          background: 'linear-gradient(135deg, #e6edf3 0%, #8b949e 100%)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>
          Automated Options Income.<br />While You Sleep.
        </h1>
        <p style={{ fontSize: 18, color: '#8b949e', maxWidth: 540, margin: '0 auto 36px', lineHeight: 1.7 }}>
          ThetaFlow sells puts and covered calls automatically using your Schwab account.
          Set your rules once — the AI handles scanning, placing, and managing every trade.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={onSignIn}
            style={{
              padding: '12px 32px', fontSize: 15, fontWeight: 700,
              background: '#1f6feb', color: '#fff', border: 'none',
              borderRadius: 10, cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#388bfd')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#1f6feb')}
          >
            Open Dashboard →
          </button>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section style={{
        display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 0,
        borderTop: '1px solid #21262d', borderBottom: '1px solid #21262d',
        margin: '0 0 80px',
      }}>
        {stats.map((s, i) => (
          <div key={i} style={{
            padding: '28px 48px', textAlign: 'center',
            borderRight: i < stats.length - 1 ? '1px solid #21262d' : 'none',
          }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#3fb950', lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontSize: 13, color: '#8b949e', marginTop: 6 }}>{s.label}</div>
          </div>
        ))}
      </section>

      {/* ── Feature sections ── */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px 80px' }}>
        {features.map((f, i) => {
          const isEven = i % 2 === 0
          return (
            <div key={f.tag} style={{
              display: 'flex',
              flexDirection: isEven ? 'row' : 'row-reverse',
              alignItems: 'center',
              gap: 56,
              marginBottom: 96,
              flexWrap: 'wrap',
            }}>
              {/* Text */}
              <div style={{ flex: '1 1 300px', minWidth: 260 }}>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  background: '#161b22', border: `1px solid ${f.color}44`,
                  color: f.color, fontSize: 11, fontWeight: 700, padding: '4px 10px',
                  borderRadius: 6, marginBottom: 16, letterSpacing: '0.05em',
                }}>
                  <span>{f.icon}</span> {f.tag.toUpperCase()}
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, color: '#e6edf3', marginBottom: 16, lineHeight: 1.3 }}>
                  {f.title}
                </h2>
                <p style={{ fontSize: 15, color: '#8b949e', lineHeight: 1.8 }}>
                  {f.description}
                </p>
              </div>

              {/* Screenshot */}
              <div style={{ flex: '1 1 480px', minWidth: 300 }}>
                <div style={{
                  borderRadius: 12,
                  border: '1px solid #30363d',
                  overflow: 'hidden',
                  boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
                  background: '#161b22',
                }}>
                  {imgErrors[f.tag] ? (
                    <div style={{
                      height: 280, display: 'flex', flexDirection: 'column',
                      alignItems: 'center', justifyContent: 'center',
                      color: '#484f58', gap: 10,
                    }}>
                      <span style={{ fontSize: 36 }}>{f.icon}</span>
                      <span style={{ fontSize: 13 }}>Add screenshot: public/screenshots/{f.img.split('/').pop()}</span>
                    </div>
                  ) : (
                    <img
                      src={f.img}
                      alt={f.title}
                      onError={() => handleImgError(f.tag)}
                      style={{ width: '100%', display: 'block' }}
                    />
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </section>

      {/* ── How it works ── */}
      <section style={{
        background: '#161b22', borderTop: '1px solid #21262d',
        borderBottom: '1px solid #21262d', padding: '72px 24px',
      }}>
        <div style={{ maxWidth: 860, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 12 }}>How it works</h2>
          <p style={{ color: '#8b949e', fontSize: 15, marginBottom: 56 }}>
            Three steps from setup to automated income.
          </p>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
            {[
              { step: '01', title: 'Connect Schwab', desc: 'Link your Schwab brokerage account via secure OAuth. ThetaFlow only places trades you authorise through rules.' },
              { step: '02', title: 'Create Rules', desc: 'Define your strategy: symbols, DTE range, premium target, position size, profit target, and stop loss.' },
              { step: '03', title: 'Collect Premium', desc: 'ThetaFlow scans every 15 minutes, places orders, monitors profit targets, and manages ITM positions automatically.' },
            ].map((item) => (
              <div key={item.step} style={{
                flex: '1 1 220px', background: '#0d1117', border: '1px solid #30363d',
                borderRadius: 12, padding: '28px 24px', textAlign: 'left',
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#1f6feb', letterSpacing: '0.08em', marginBottom: 12 }}>
                  STEP {item.step}
                </div>
                <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 10 }}>{item.title}</h3>
                <p style={{ fontSize: 14, color: '#8b949e', lineHeight: 1.7 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ textAlign: 'center', padding: '72px 24px' }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Ready to start collecting premium?</h2>
        <p style={{ color: '#8b949e', fontSize: 15, marginBottom: 32 }}>
          Sign in to your private ThetaFlow dashboard.
        </p>
        <button
          onClick={onSignIn}
          style={{
            padding: '13px 36px', fontSize: 16, fontWeight: 700,
            background: '#1f6feb', color: '#fff', border: 'none',
            borderRadius: 10, cursor: 'pointer', fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#388bfd')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#1f6feb')}
        >
          Sign in to ThetaFlow →
        </button>
      </section>

      {/* ── Footer ── */}
      <footer style={{
        borderTop: '1px solid #21262d', padding: '24px 32px',
        display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap',
        gap: 12, fontSize: 12, color: '#484f58',
      }}>
        <span>© 2026 ThetaFlow · Private automated trading system</span>
        <span style={{ display: 'flex', gap: 20 }}>
          <a href="/privacy" style={{ color: '#484f58', textDecoration: 'none' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#8b949e')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}>Privacy Policy</a>
          <a href="/terms" style={{ color: '#484f58', textDecoration: 'none' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#8b949e')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}>Terms of Service</a>
        </span>
      </footer>
    </div>
  )
}
