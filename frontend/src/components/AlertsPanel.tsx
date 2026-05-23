import React, { useEffect, useState } from 'react'

// ── Design tokens ─────────────────────────────────────────────────────────────
const BG = '#0d1117'
const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const GREEN = '#3fb950'
const RED = '#f85149'
const BLUE_BTN = '#1f6feb'

// ── Types ─────────────────────────────────────────────────────────────────────
type Condition = 'drop_pct' | 'rise_pct' | 'below_price' | 'above_price'
type Action = 'notify_only' | 'notify_and_suggest'

interface PriceAlert {
  id: string
  symbol: string
  condition: Condition
  threshold: number
  action: Action
  enabled: boolean
  cooldown_minutes: number
  last_triggered_at: string | null
}

// ── Shared style helpers ──────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  fontSize: 13,
  background: '#21262d',
  border: '1px solid #30363d',
  borderRadius: 7,
  color: '#e6edf3',
  outline: 'none',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 11,
  fontWeight: 600,
  color: MUTED,
  marginBottom: 4,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.04em',
}

const CONDITION_LABELS: Record<Condition, string> = {
  drop_pct: 'Drop % ≥',
  rise_pct: 'Rise % ≥',
  below_price: 'Price below',
  above_price: 'Price above',
}

const ACTION_LABELS: Record<Action, string> = {
  notify_only: 'Notify only',
  notify_and_suggest: 'Notify + suggest',
}

function conditionDisplay(c: Condition, threshold: number): string {
  if (c === 'drop_pct') return `drop ≥${threshold}%`
  if (c === 'rise_pct') return `rise ≥${threshold}%`
  if (c === 'below_price') return `below $${threshold}`
  if (c === 'above_price') return `above $${threshold}`
  return `${c} ${threshold}`
}

function formatLastTriggered(at: string | null): string {
  if (!at) return 'Never triggered'
  const diff = Date.now() - new Date(at).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ── AlertsPanel ───────────────────────────────────────────────────────────────
export function AlertsPanel() {
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [testPushStatus, setTestPushStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')

  const fetchAlerts = async () => {
    try {
      const res = await fetch('/api/alerts')
      if (res.ok) setAlerts(await res.json())
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAlerts() }, [])

  const toggleAlert = async (id: string) => {
    await fetch(`/api/alerts/${id}/toggle`, { method: 'PATCH' })
    fetchAlerts()
  }

  const deleteAlert = async (id: string) => {
    if (!confirm('Delete this alert?')) return
    await fetch(`/api/alerts/${id}`, { method: 'DELETE' })
    fetchAlerts()
  }

  const sendTestPush = async () => {
    setTestPushStatus('sending')
    try {
      const res = await fetch('/api/push/test', { method: 'POST' })
      setTestPushStatus(res.ok ? 'sent' : 'error')
    } catch {
      setTestPushStatus('error')
    }
    setTimeout(() => setTestPushStatus('idle'), 3000)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Main card */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${BORDER}` }}>
          <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Price Alerts</h2>
          <button
            onClick={() => setShowForm((v) => !v)}
            style={{
              background: showForm ? '#21262d' : BLUE_BTN,
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {showForm ? '✕ Cancel' : '+ Add Alert'}
          </button>
        </div>

        {/* Alert list */}
        {loading && (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
            Loading alerts…
          </div>
        )}

        {!loading && alerts.length === 0 && !showForm && (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
            No alerts yet. Click "+ Add Alert" to create one.
          </div>
        )}

        {!loading && alerts.length > 0 && (
          <div>
            {alerts.map((alert, idx) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                isLast={idx === alerts.length - 1 && !showForm}
                onToggle={() => toggleAlert(alert.id)}
                onDelete={() => deleteAlert(alert.id)}
              />
            ))}
          </div>
        )}

        {/* Add alert form */}
        {showForm && (
          <AddAlertForm
            onSaved={() => { setShowForm(false); fetchAlerts() }}
            onCancel={() => setShowForm(false)}
          />
        )}
      </div>

      {/* Notifications info card */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e6edf3', marginBottom: 6 }}>Notification Delivery</div>
            <p style={{ fontSize: 12, color: MUTED, margin: 0, lineHeight: 1.6 }}>
              Alerts are sent via SMS + push notification. Configure{' '}
              <code style={{ background: '#21262d', padding: '1px 5px', borderRadius: 4, fontSize: 11, color: '#79c0ff' }}>TWILIO_*</code>
              {' '}and{' '}
              <code style={{ background: '#21262d', padding: '1px 5px', borderRadius: 4, fontSize: 11, color: '#79c0ff' }}>ALERT_PHONE_NUMBER</code>
              {' '}in your .env to activate.
            </p>
          </div>
          <button
            onClick={sendTestPush}
            disabled={testPushStatus === 'sending'}
            style={{
              background: testPushStatus === 'sent' ? '#1a3028' : testPushStatus === 'error' ? '#2d1414' : '#21262d',
              color: testPushStatus === 'sent' ? GREEN : testPushStatus === 'error' ? RED : MUTED,
              border: `1px solid ${testPushStatus === 'sent' ? '#3fb95044' : testPushStatus === 'error' ? '#f8514944' : BORDER}`,
              borderRadius: 7,
              padding: '7px 14px',
              fontSize: 13,
              fontWeight: 500,
              cursor: testPushStatus === 'sending' ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              whiteSpace: 'nowrap' as const,
              flexShrink: 0,
            }}
          >
            {testPushStatus === 'sending' ? 'Sending…' : testPushStatus === 'sent' ? '✓ Sent!' : testPushStatus === 'error' ? '✕ Failed' : 'Send Test Push'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Alert row ─────────────────────────────────────────────────────────────────
function AlertRow({
  alert,
  isLast,
  onToggle,
  onDelete,
}: {
  alert: PriceAlert
  isLast: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 20px',
        borderBottom: isLast ? 'none' : `1px solid #21262d`,
        gap: 12,
        transition: 'background 0.1s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#1c2128')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      {/* Symbol + condition */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            background: '#1f2937', color: '#58a6ff',
            border: '1px solid #1f6feb44',
            borderRadius: 4, padding: '1px 7px',
            fontSize: 12, fontWeight: 700,
          }}>
            {alert.symbol}
          </span>
          <span style={{ fontSize: 13, color: '#e6edf3' }}>
            {conditionDisplay(alert.condition, alert.threshold)}
          </span>
          <span style={{
            fontSize: 11, color: MUTED,
            background: '#21262d',
            padding: '1px 7px', borderRadius: 4,
          }}>
            {ACTION_LABELS[alert.action]}
          </span>
        </div>
        <div style={{ fontSize: 11, color: '#484f58', marginTop: 4 }}>
          Cooldown {alert.cooldown_minutes}m · {formatLastTriggered(alert.last_triggered_at)}
        </div>
      </div>

      {/* Toggle + delete */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {/* Toggle pill */}
        <button
          onClick={onToggle}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            fontFamily: 'inherit',
          }}
          title={alert.enabled ? 'Click to disable' : 'Click to enable'}
        >
          <span
            style={{
              display: 'inline-block',
              width: 36, height: 20,
              borderRadius: 10,
              background: alert.enabled ? GREEN : '#30363d',
              position: 'relative',
              transition: 'background 0.2s',
              flexShrink: 0,
            }}
          >
            <span style={{
              position: 'absolute', top: 3,
              left: alert.enabled ? 19 : 3,
              width: 14, height: 14,
              borderRadius: '50%',
              background: '#fff',
              transition: 'left 0.2s',
            }} />
          </span>
          <span style={{ fontSize: 11, color: alert.enabled ? GREEN : '#484f58', fontWeight: 600, minWidth: 26 }}>
            {alert.enabled ? 'ON' : 'OFF'}
          </span>
        </button>

        <button
          onClick={onDelete}
          style={{
            color: '#484f58', fontSize: 12,
            background: 'none', border: 'none',
            cursor: 'pointer', padding: '2px 4px',
            fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = RED)}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}
        >
          Del
        </button>
      </div>
    </div>
  )
}

// ── Add alert form ────────────────────────────────────────────────────────────
function AddAlertForm({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const [form, setForm] = useState({
    symbol: '',
    condition: 'drop_pct' as Condition,
    threshold: 3,
    action: 'notify_and_suggest' as Action,
    cooldown_minutes: 60,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    if (!form.symbol.trim()) { setError('Symbol is required'); return }
    setSaving(true)
    setError('')
    try {
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, symbol: form.symbol.trim().toUpperCase() }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data?.detail ?? 'Save failed')
        setSaving(false)
        return
      }
      onSaved()
    } catch {
      setError('Network error')
      setSaving(false)
    }
  }

  const focusInput = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    e.currentTarget.style.borderColor = '#58a6ff'
  }
  const blurInput = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    e.currentTarget.style.borderColor = '#30363d'
  }

  return (
    <div style={{ padding: '16px 20px', borderTop: `1px solid ${BORDER}`, background: BG }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: MUTED, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
        Add Alert
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12, marginBottom: 14 }}>
        {/* Symbol */}
        <div>
          <label style={labelStyle}>Symbol</label>
          <input
            type="text"
            placeholder="TSLA"
            value={form.symbol}
            onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value.toUpperCase() }))}
            style={inputStyle}
            onFocus={focusInput}
            onBlur={blurInput}
          />
        </div>

        {/* Condition */}
        <div>
          <label style={labelStyle}>Condition</label>
          <select
            value={form.condition}
            onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value as Condition }))}
            style={{ ...inputStyle, cursor: 'pointer' }}
            onFocus={focusInput}
            onBlur={blurInput}
          >
            {(Object.keys(CONDITION_LABELS) as Condition[]).map((c) => (
              <option key={c} value={c}>{CONDITION_LABELS[c]}</option>
            ))}
          </select>
        </div>

        {/* Threshold */}
        <div>
          <label style={labelStyle}>
            {form.condition === 'drop_pct' || form.condition === 'rise_pct' ? 'Threshold %' : 'Price ($)'}
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={form.threshold}
            onChange={(e) => setForm((f) => ({ ...f, threshold: parseFloat(e.target.value) || 0 }))}
            style={inputStyle}
            onFocus={focusInput}
            onBlur={blurInput}
          />
        </div>

        {/* Action */}
        <div>
          <label style={labelStyle}>Action</label>
          <select
            value={form.action}
            onChange={(e) => setForm((f) => ({ ...f, action: e.target.value as Action }))}
            style={{ ...inputStyle, cursor: 'pointer' }}
            onFocus={focusInput}
            onBlur={blurInput}
          >
            {(Object.keys(ACTION_LABELS) as Action[]).map((a) => (
              <option key={a} value={a}>{ACTION_LABELS[a]}</option>
            ))}
          </select>
        </div>

        {/* Cooldown */}
        <div>
          <label style={labelStyle}>Cooldown (min)</label>
          <input
            type="number"
            step="1"
            min="1"
            value={form.cooldown_minutes}
            onChange={(e) => setForm((f) => ({ ...f, cooldown_minutes: parseInt(e.target.value) || 1 }))}
            style={inputStyle}
            onFocus={focusInput}
            onBlur={blurInput}
          />
        </div>
      </div>

      {error && (
        <div style={{ fontSize: 12, color: RED, marginBottom: 10 }}>{error}</div>
      )}

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button
          onClick={onCancel}
          style={{
            padding: '7px 14px', fontSize: 13,
            background: '#21262d', color: MUTED,
            border: `1px solid ${BORDER}`, borderRadius: 7,
            cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          Cancel
        </button>
        <button
          onClick={save}
          disabled={saving || !form.symbol.trim()}
          style={{
            padding: '7px 14px', fontSize: 13, fontWeight: 600,
            background: saving || !form.symbol.trim() ? '#21262d' : BLUE_BTN,
            color: saving || !form.symbol.trim() ? '#484f58' : '#fff',
            border: 'none', borderRadius: 7,
            cursor: saving || !form.symbol.trim() ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          {saving ? 'Saving…' : 'Save Alert'}
        </button>
      </div>
    </div>
  )
}
