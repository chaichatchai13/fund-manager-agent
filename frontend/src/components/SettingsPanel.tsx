import { useEffect, useState } from 'react'

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
