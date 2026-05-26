import { useEffect, useState, useCallback } from 'react'

const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const GREEN = '#3fb950'
const RED = '#f85149'
const YELLOW = '#d29922'
const BLUE_BTN = '#1f6feb'

interface SchwabStatus {
  connected: boolean
  mock_mode: boolean
  token_file_exists: boolean
  token_expiry: string | null
  refresh_token_expiry: string | null
  error: string | null
  account_hash_preview: string | null
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function isExpiringSoon(iso: string | null, withinHours = 24): boolean {
  if (!iso) return false
  const diff = new Date(iso).getTime() - Date.now()
  return diff < withinHours * 3600 * 1000 && diff > 0
}

function isExpired(iso: string | null): boolean {
  if (!iso) return false
  return new Date(iso).getTime() < Date.now()
}

export function SettingsPanel() {
  const [status, setStatus] = useState<SchwabStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/schwab/status')
      if (res.ok) setStatus(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Also check if we just came back from OAuth
    const params = new URLSearchParams(window.location.search)
    if (params.get('schwab_connected')) {
      setMessage({ text: 'Schwab connected successfully!', ok: true })
      window.history.replaceState({}, '', '/')
    } else if (params.get('schwab_error')) {
      setMessage({ text: `Schwab error: ${params.get('schwab_error')}`, ok: false })
      window.history.replaceState({}, '', '/')
    }
  }, [])

  const handleReconnect = () => {
    // Opens Schwab OAuth in the same tab — Schwab will redirect back
    window.location.href = '/api/schwab/connect'
  }

  const handleRefresh = async () => {
    setActionLoading('refresh')
    setMessage(null)
    try {
      const res = await fetch('/api/schwab/refresh', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setMessage({ text: 'Token refreshed successfully.', ok: true })
        await fetchStatus()
      } else {
        setMessage({ text: `Refresh failed: ${data.error ?? 'Unknown error'}`, ok: false })
      }
    } catch {
      setMessage({ text: 'Refresh request failed.', ok: false })
    } finally {
      setActionLoading(null)
    }
  }

  const handleReinitialize = async () => {
    setActionLoading('reinit')
    setMessage(null)
    try {
      const res = await fetch('/api/schwab/reconnect', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setMessage({ text: 'Schwab reconnected successfully.', ok: true })
        await fetchStatus()
      } else {
        setMessage({ text: `Reconnect failed: ${data.status?.error ?? 'Unknown error'}`, ok: false })
      }
    } catch {
      setMessage({ text: 'Reconnect request failed.', ok: false })
    } finally {
      setActionLoading(null)
    }
  }

  const connColor = status?.connected ? GREEN : RED
  const connLabel = status?.mock_mode ? 'MOCK MODE' : status?.connected ? 'CONNECTED' : 'DISCONNECTED'

  const refreshExpired = isExpired(status?.refresh_token_expiry ?? null)
  const refreshSoon = isExpiringSoon(status?.refresh_token_expiry ?? null, 48)
  const accessSoon = isExpiringSoon(status?.token_expiry ?? null, 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* AI Model Card */}
      <AIModelCard />

      {/* Schwab Connection Card */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <h2 style={{ margin: 0, color: '#e6edf3', fontSize: 16, fontWeight: 600 }}>Schwab Connection</h2>
          <span style={{
            background: status?.connected ? '#1a3a2a' : '#3a1a1a',
            color: connColor,
            padding: '3px 10px',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: '0.5px',
          }}>
            {loading ? '...' : connLabel}
          </span>
        </div>

        {/* Status grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <StatusRow label="Account" value={status?.account_hash_preview ?? '—'} />
          <StatusRow label="Token file" value={status?.token_file_exists ? 'Present' : 'Missing'} valueColor={status?.token_file_exists ? GREEN : RED} />
          <StatusRow
            label="Access token expires"
            value={fmtDate(status?.token_expiry ?? null)}
            valueColor={accessSoon ? YELLOW : undefined}
          />
          <StatusRow
            label="Refresh token expires"
            value={fmtDate(status?.refresh_token_expiry ?? null)}
            valueColor={refreshExpired ? RED : refreshSoon ? YELLOW : undefined}
          />
        </div>

        {/* Error message */}
        {status?.error && (
          <div style={{
            background: '#3a1a1a', border: `1px solid ${RED}`, borderRadius: 8,
            padding: '10px 14px', marginBottom: 16, color: RED, fontSize: 13,
          }}>
            {status.error}
          </div>
        )}

        {/* Warnings */}
        {refreshExpired && (
          <div style={{
            background: '#2a1a1a', border: `1px solid ${RED}`, borderRadius: 8,
            padding: '10px 14px', marginBottom: 16, color: '#e6edf3', fontSize: 13,
          }}>
            ⚠️ <strong>Refresh token expired.</strong> You need to reconnect via Schwab OAuth below.
          </div>
        )}
        {refreshSoon && !refreshExpired && (
          <div style={{
            background: '#2a1f0a', border: `1px solid ${YELLOW}`, borderRadius: 8,
            padding: '10px 14px', marginBottom: 16, color: '#e6edf3', fontSize: 13,
          }}>
            ⚠️ <strong>Refresh token expiring soon.</strong> Reconnect within 48 hours to avoid interruption.
          </div>
        )}

        {/* Action message */}
        {message && (
          <div style={{
            background: message.ok ? '#0d2a1a' : '#2a0d0d',
            border: `1px solid ${message.ok ? GREEN : RED}`,
            borderRadius: 8, padding: '10px 14px', marginBottom: 16,
            color: message.ok ? GREEN : RED, fontSize: 13,
          }}>
            {message.text}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <ActionButton
            label="Reconnect via Schwab OAuth"
            onClick={handleReconnect}
            disabled={!!actionLoading || !!status?.mock_mode}
            primary
          />
          <ActionButton
            label={actionLoading === 'refresh' ? 'Refreshing…' : 'Refresh Access Token'}
            onClick={handleRefresh}
            disabled={!!actionLoading || !!status?.mock_mode || refreshExpired}
            title={refreshExpired ? 'Refresh token expired — use Reconnect instead' : undefined}
          />
          <ActionButton
            label={actionLoading === 'reinit' ? 'Reconnecting…' : 'Reinitialize Client'}
            onClick={handleReinitialize}
            disabled={!!actionLoading}
            title="Re-read token from DB/file without OAuth flow"
          />
        </div>

        {status?.mock_mode && (
          <p style={{ color: MUTED, fontSize: 12, margin: '12px 0 0' }}>
            Mock mode is enabled (MOCK_SCHWAB=true) — OAuth actions are disabled.
          </p>
        )}
      </div>

      {/* SMS Alerts Opt-In */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '20px 24px' }}>
        <h2 style={{ margin: '0 0 4px', color: '#e6edf3', fontSize: 16, fontWeight: 600 }}>📱 SMS Trading Alerts</h2>
        <p style={{ color: MUTED, fontSize: 13, margin: '0 0 16px' }}>
          Receive SMS alerts for price movements, position updates, and trade confirmations. Reply YES/NO to act on alerts directly from your phone.
        </p>

        {/* Compliant opt-in checkbox */}
        <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer', marginBottom: 16 }}>
          <input
            type="checkbox"
            id="sms-consent"
            defaultChecked={false}
            style={{ marginTop: 2, width: 16, height: 16, cursor: 'pointer', accentColor: BLUE_BTN }}
          />
          <span style={{ color: '#e6edf3', fontSize: 13, lineHeight: 1.6 }}>
            I agree to receive SMS trading alerts from <strong>ThetaFlow</strong>. Message frequency varies (up to 10 messages per trading day based on market activity). Message and data rates may apply.{' '}
            Reply <strong>STOP</strong> to unsubscribe at any time. Reply <strong>HELP</strong> for help.{' '}
            <a href="https://theta-flows.com/privacy" target="_blank" rel="noreferrer" style={{ color: BLUE_BTN }}>Privacy Policy</a>{' · '}
            <a href="https://theta-flows.com/terms" target="_blank" rel="noreferrer" style={{ color: BLUE_BTN }}>Terms of Service</a>
          </span>
        </label>

        <p style={{ color: MUTED, fontSize: 11, margin: '0 0 12px', fontStyle: 'italic' }}>
          You can use ThetaFlow without SMS alerts — this consent is optional.
        </p>

        <div style={{ background: '#0d1117', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: MUTED }}>
          Alert phone number is configured via the <code style={{ color: '#e6edf3' }}>ALERT_PHONE_NUMBER</code> environment variable on the server.
        </div>
      </div>

      {/* How to reconnect info */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '20px 24px' }}>
        <h2 style={{ margin: '0 0 12px', color: '#e6edf3', fontSize: 16, fontWeight: 600 }}>How to reconnect</h2>
        <ol style={{ color: MUTED, fontSize: 13, margin: 0, paddingLeft: 20, lineHeight: 2 }}>
          <li>Make sure <code style={{ color: '#e6edf3' }}>SCHWAB_CALLBACK_URL</code> in your <code style={{ color: '#e6edf3' }}>.env</code> points to <code style={{ color: '#e6edf3' }}>https://yourdomain.com/api/schwab/callback</code></li>
          <li>This URL must also be registered in your <a href="https://developer.schwab.com" target="_blank" rel="noreferrer" style={{ color: BLUE_BTN }}>Schwab developer app</a></li>
          <li>Click <strong style={{ color: '#e6edf3' }}>Reconnect via Schwab OAuth</strong> above</li>
          <li>Log in to Schwab and approve the app</li>
          <li>You'll be redirected back here automatically</li>
        </ol>
      </div>

    </div>
  )
}

function StatusRow({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ background: '#0d1117', borderRadius: 8, padding: '10px 14px' }}>
      <div style={{ color: MUTED, fontSize: 11, marginBottom: 2 }}>{label}</div>
      <div style={{ color: valueColor ?? '#e6edf3', fontSize: 13, fontWeight: 500 }}>{value}</div>
    </div>
  )
}

// ── AI Model Card ─────────────────────────────────────────────────────────────

interface AIProvider {
  id: string
  label: string
  configured: boolean
}

const PROVIDER_ICONS: Record<string, string> = {
  claude: '🟠',
  gpt:    '🟢',
  gemini: '🔵',
  grok:   '⚫',
}

function AIModelCard() {
  const [active, setActive] = useState<string | null>(null)
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const fetchModel = useCallback(async () => {
    try {
      const res = await fetch('/api/ai/model')
      if (res.ok) {
        const data = await res.json()
        setActive(data.active)
        setProviders(data.providers)
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchModel() }, [fetchModel])

  const select = async (id: string) => {
    if (id === active) return
    setSaving(true); setMsg(null)
    try {
      const res = await fetch('/api/ai/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: id }),
      })
      if (res.ok) {
        setActive(id)
        const p = providers.find(p => p.id === id)
        setMsg({ text: `Switched to ${p?.label ?? id}`, ok: true })
      } else {
        setMsg({ text: 'Failed to switch model', ok: false })
      }
    } catch { setMsg({ text: 'Network error', ok: false }) }
    setSaving(false)
  }

  return (
    <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '20px 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: '0 0 4px', color: '#e6edf3', fontSize: 16, fontWeight: 600 }}>🤖 AI Model</h2>
        <p style={{ margin: 0, color: MUTED, fontSize: 13 }}>
          Used for Social Intel post summaries. Agent Chat always uses Claude (required for tool use).
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, marginBottom: 16 }}>
        {providers.map((p) => {
          const isActive = p.id === active
          const disabled = !p.configured || saving
          return (
            <button
              key={p.id}
              onClick={() => !disabled && select(p.id)}
              disabled={disabled}
              title={!p.configured ? 'API key not configured — add to .env' : undefined}
              style={{
                padding: '12px 16px',
                borderRadius: 10,
                border: isActive
                  ? `2px solid ${GREEN}`
                  : `1px solid ${disabled ? '#21262d' : BORDER}`,
                background: isActive ? '#0d2a1a' : disabled ? '#0d1117' : '#21262d',
                cursor: disabled ? 'not-allowed' : 'pointer',
                textAlign: 'left',
                opacity: disabled && !isActive ? 0.45 : 1,
                transition: 'all 0.15s',
                fontFamily: 'inherit',
              }}
              onMouseEnter={(e) => { if (!disabled) e.currentTarget.style.borderColor = '#58a6ff' }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = isActive ? GREEN : disabled ? '#21262d' : BORDER }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 16 }}>{PROVIDER_ICONS[p.id]}</span>
                {isActive && (
                  <span style={{ fontSize: 10, fontWeight: 700, color: GREEN, background: '#1a3028', padding: '1px 6px', borderRadius: 4 }}>
                    ACTIVE
                  </span>
                )}
                {!p.configured && (
                  <span style={{ fontSize: 10, color: '#484f58', background: '#21262d', padding: '1px 6px', borderRadius: 4 }}>
                    NO KEY
                  </span>
                )}
              </div>
              <div style={{ color: isActive ? '#e6edf3' : MUTED, fontSize: 13, fontWeight: 600 }}>{p.label}</div>
              {!p.configured && (
                <div style={{ color: '#484f58', fontSize: 11, marginTop: 2 }}>Add key to .env</div>
              )}
            </button>
          )
        })}
      </div>

      {msg && (
        <div style={{
          padding: '8px 12px', borderRadius: 8, fontSize: 13,
          background: msg.ok ? '#0d2a1a' : '#2a0d0d',
          border: `1px solid ${msg.ok ? GREEN : RED}`,
          color: msg.ok ? GREEN : RED,
        }}>
          {msg.text}
        </div>
      )}
    </div>
  )
}

function ActionButton({
  label, onClick, disabled, primary, title,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  title?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        padding: '8px 16px',
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 500,
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: primary ? 'none' : `1px solid ${BORDER}`,
        background: primary ? BLUE_BTN : '#21262d',
        color: disabled ? MUTED : '#e6edf3',
        opacity: disabled ? 0.6 : 1,
        fontFamily: 'inherit',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )
}
