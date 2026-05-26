import React, { useEffect, useState } from 'react'
import type { SellPutRule } from '../types'

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
  overflow: 'hidden',
}

function useIsMobile(bp = 768) {
  const [m, setM] = useState(() => window.innerWidth < bp)
  useEffect(() => {
    const h = () => setM(window.innerWidth < bp)
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [bp])
  return m
}

export function RulesPanel() {
  const [rules, setRules] = useState<SellPutRule[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editingRule, setEditingRule] = useState<SellPutRule | null>(null)
  const isMobile = useIsMobile()

  const fetchRules = async () => {
    const res = await fetch('/api/rules')
    setRules(await res.json())
    setLoading(false)
  }

  useEffect(() => { fetchRules() }, [])

  const toggleRule = async (rule: SellPutRule) => {
    await fetch(`/api/rules/${rule.id}/toggle`, { method: 'PATCH' })
    fetchRules()
  }

  const deleteRule = async (ruleId: string) => {
    if (!confirm('Delete this rule?')) return
    await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' })
    fetchRules()
  }

  return (
    <div style={CARD}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid #30363d' }}>
        <h2 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 15, margin: 0 }}>Trading Rules</h2>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            background: '#1f6feb', color: '#fff', border: 'none', borderRadius: 6,
            padding: '6px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          + New Rule
        </button>
      </div>

      {loading && (
        <div style={{ padding: '32px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
          Loading rules…
        </div>
      )}

      {!loading && rules.length === 0 && (
        <div style={{ padding: '32px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
          No rules yet. Create one or ask the agent to set one up.
        </div>
      )}

      {!loading && rules.length > 0 && (
        <div>
          {rules.map((rule, idx) => (
            <RuleRow
              key={rule.id}
              rule={rule}
              isLast={idx === rules.length - 1}
              onToggle={() => toggleRule(rule)}
              onEdit={() => setEditingRule(rule)}
              onDelete={() => deleteRule(rule.id)}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <RuleFormModal
          isMobile={isMobile}
          onSaved={() => { setShowCreate(false); fetchRules() }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {/* Edit modal */}
      {editingRule && (
        <RuleFormModal
          isMobile={isMobile}
          existingRule={editingRule}
          onSaved={() => { setEditingRule(null); fetchRules() }}
          onCancel={() => setEditingRule(null)}
        />
      )}
    </div>
  )
}

function RuleRow({
  rule,
  isLast,
  onToggle,
  onEdit,
  onDelete,
}: {
  rule: SellPutRule
  isLast: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const isCoveredCall = rule.strategy_type === 'SELL_COVERED_CALL'

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        padding: '14px 20px',
        borderBottom: isLast ? 'none' : '1px solid #21262d',
        transition: 'background 0.1s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#1c2128')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Toggle */}
        <button
          onClick={onToggle}
          style={{
            marginTop: 3, width: 36, height: 20, borderRadius: 10,
            background: rule.enabled ? '#3fb950' : '#30363d',
            border: 'none', cursor: 'pointer', position: 'relative',
            transition: 'background 0.2s', flexShrink: 0,
          }}
        >
          <span style={{
            position: 'absolute', top: 3, left: rule.enabled ? 19 : 3,
            width: 14, height: 14, borderRadius: '50%', background: '#fff',
            transition: 'left 0.2s',
          }} />
        </button>

        {/* Content */}
        <div>
          <div style={{ color: '#e6edf3', fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            {rule.name}
            {isCoveredCall ? (
              <span style={{ background: '#1f2d45', color: '#58a6ff', fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600, letterSpacing: '0.02em' }}>
                CALL
              </span>
            ) : (
              <span style={{ background: '#1a3028', color: '#3fb950', fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600, letterSpacing: '0.02em' }}>
                PUT
              </span>
            )}
            {!rule.enabled && (
              <span style={{ background: '#21262d', color: '#8b949e', fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 500 }}>
                PAUSED
              </span>
            )}
          </div>

          {/* Symbol tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {rule.symbols
              .sort((a, b) => a.priority - b.priority)
              .map((s) => (
                <span key={s.symbol} style={{
                  background: '#1f2937', color: '#58a6ff', border: '1px solid #1f6feb44',
                  borderRadius: 4, padding: '1px 7px', fontSize: 11, fontWeight: 600,
                }}>
                  {s.symbol}
                </span>
              ))}
          </div>

          {/* Stats row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 6 }}>
            <StatChip label="DTE" value={`${rule.min_dte}–${rule.max_dte}`} />
            <StatChip
              label="Premium"
              value={
                rule.min_premium_mode === 'dollar'
                  ? `≥$${rule.min_premium_dollar?.toFixed(2) ?? '—'}`
                  : `≥${rule.min_premium_pct}%${rule.max_premium_pct ? `–${rule.max_premium_pct}%` : ''}`
              }
            />
            <StatChip label="Profit target" value={`${(rule.profit_target_pct * 100).toFixed(0)}%`} color="#3fb950" />
            {rule.min_daily_drop_pct != null && (
              <StatChip
                label="Drop trigger"
                value={`${rule.min_daily_drop_pct}%${rule.max_daily_drop_pct ? `–${rule.max_daily_drop_pct}%` : '+'}`}
                color="#d29922"
              />
            )}
            <StatChip
              label="Size"
              value={
                rule.position_size_mode === 'contracts'
                  ? `${rule.position_size_contracts ?? '?'} contract${(rule.position_size_contracts ?? 0) !== 1 ? 's' : ''}`
                  : `${(rule.position_size_pct * 100).toFixed(0)}% BP`
              }
            />
            <StatChip label="Max positions" value={String(rule.max_open_positions)} />
            <StatChip label="Scan" value={`${rule.scan_interval_minutes}m`} />
            {rule.itm_action === 'roll' ? (
              <StatChip
                label="ITM"
                value={`Roll ≤${rule.roll_when_dte}DTE → ${rule.roll_target_weeks}w out`}
                color="#c9a227"
              />
            ) : (
              <StatChip label="ITM" value="Let assign" color="#8b949e" />
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, marginLeft: 12 }}>
        <button
          onClick={onEdit}
          style={{ color: '#58a6ff', fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#79c0ff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#58a6ff')}
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          style={{ color: '#484f58', fontSize: 12, background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#f85149')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}
        >
          Delete
        </button>
      </div>
    </div>
  )
}

function StatChip({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <span style={{ fontSize: 12, color: '#8b949e' }}>
      {label}: <span style={{ color: color ?? '#e6edf3', fontWeight: 500 }}>{value}</span>
    </span>
  )
}

// ── Shared form for create + edit ─────────────────────────────────────────────

function RuleFormModal({
  existingRule,
  onSaved,
  onCancel,
  isMobile = false,
}: {
  existingRule?: SellPutRule
  onSaved: () => void
  onCancel: () => void
  isMobile?: boolean
}) {
  const isEdit = !!existingRule

  // Derive symbolsText from existing rule's symbols array (sorted by priority)
  const initialSymbolsText = existingRule
    ? existingRule.symbols.sort((a, b) => a.priority - b.priority).map((s) => s.symbol).join(', ')
    : ''

  const [form, setForm] = useState({
    name: existingRule?.name ?? '',
    symbolsText: initialSymbolsText,
    strategy_type: (existingRule?.strategy_type ?? 'SELL_PUT') as 'SELL_PUT' | 'SELL_COVERED_CALL',
    min_dte: existingRule?.min_dte ?? 30,
    max_dte: existingRule?.max_dte ?? 45,
    // Premium
    min_premium_mode: (existingRule?.min_premium_mode ?? 'pct') as 'pct' | 'dollar',
    min_premium_pct: existingRule?.min_premium_pct ?? 1.0,
    min_premium_dollar: existingRule?.min_premium_dollar ?? 2.0,
    // Profit
    profit_target_pct: existingRule?.profit_target_pct ?? 0.75,
    min_daily_drop_pct: existingRule?.min_daily_drop_pct != null ? String(existingRule.min_daily_drop_pct) : '',
    // Position size
    position_size_mode: (existingRule?.position_size_mode ?? 'pct') as 'pct' | 'contracts',
    position_size_pct: existingRule?.position_size_pct ?? 0.05,
    position_size_contracts: existingRule?.position_size_contracts ?? 1,
    max_open_positions: existingRule?.max_open_positions ?? 5,
    scan_interval_minutes: existingRule?.scan_interval_minutes ?? 15,
    // ITM management
    itm_action: (existingRule?.itm_action ?? 'let_assign') as 'let_assign' | 'roll',
    roll_when_dte: existingRule?.roll_when_dte ?? 7,
    roll_target_weeks: existingRule?.roll_target_weeks ?? 4,
  })
  const [saving, setSaving] = useState(false)

  const isCoveredCall = form.strategy_type === 'SELL_COVERED_CALL'

  const save = async () => {
    setSaving(true)
    const symbolsList = form.symbolsText
      .split(',')
      .map((s, i) => ({ symbol: s.trim().toUpperCase(), priority: i + 1 }))
      .filter((s) => s.symbol)

    const body = {
      name: form.name,
      symbols: symbolsList,
      strategy_type: form.strategy_type,
      min_strike_otm_pct: null,
      min_dte: form.min_dte,
      max_dte: form.max_dte,
      min_premium_mode: form.min_premium_mode,
      min_premium_pct: form.min_premium_pct,
      min_premium_dollar: form.min_premium_mode === 'dollar' ? form.min_premium_dollar : null,
      profit_target_pct: form.profit_target_pct,
      min_daily_drop_pct: !isCoveredCall && form.min_daily_drop_pct
        ? parseFloat(form.min_daily_drop_pct)
        : null,
      position_size_mode: form.position_size_mode,
      position_size_pct: form.position_size_pct,
      position_size_contracts: form.position_size_mode === 'contracts' ? form.position_size_contracts : null,
      max_open_positions: form.max_open_positions,
      scan_interval_minutes: form.scan_interval_minutes,
      itm_action: form.itm_action,
      roll_when_dte: form.roll_when_dte,
      roll_target_weeks: form.roll_target_weeks,
    }

    await fetch(isEdit ? `/api/rules/${existingRule!.id}` : '/api/rules', {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setSaving(false)
    onSaved()
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px', fontSize: 13,
    background: '#21262d', border: '1px solid #30363d', borderRadius: 8,
    color: '#e6edf3', outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4,
  }

  const field = (label: string, key: keyof typeof form, type = 'text', step?: string) => (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type} step={step}
        value={form[key] as string | number}
        onChange={(e) =>
          setForm((f) => ({
            ...f,
            [key]: type === 'number' ? parseFloat(e.target.value) || '' : e.target.value,
          }))
        }
        style={inputStyle}
        onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
        onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')}
      />
    </div>
  )

  const PillToggle = ({
    labelA, labelB, value, onChange,
  }: { labelA: string; labelB: string; value: string; onChange: (v: string) => void }) => {
    const base: React.CSSProperties = {
      flex: 1, padding: '5px 0', fontSize: 12, fontWeight: 600,
      border: 'none', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s',
    }
    return (
      <div style={{ display: 'flex', background: '#21262d', border: '1px solid #30363d', borderRadius: 7, padding: 2, gap: 2 }}>
        <button type="button"
          style={{ ...base, background: value === 'a' ? '#1f6feb' : 'transparent', color: value === 'a' ? '#fff' : '#8b949e', borderRadius: 6 }}
          onClick={() => onChange('a')}>{labelA}</button>
        <button type="button"
          style={{ ...base, background: value === 'b' ? '#1f6feb' : 'transparent', color: value === 'b' ? '#fff' : '#8b949e', borderRadius: 6 }}
          onClick={() => onChange('b')}>{labelB}</button>
      </div>
    )
  }

  const strategyBtnStyle = (active: boolean): React.CSSProperties => ({
    flex: 1, padding: '8px 0', fontSize: 13, fontWeight: 600,
    border: active ? '1px solid #58a6ff' : '1px solid #30363d',
    borderRadius: 8, background: active ? '#1f2d45' : '#21262d',
    color: active ? '#58a6ff' : '#8b949e',
    cursor: isEdit ? 'not-allowed' : 'pointer',  // strategy locked when editing
    fontFamily: 'inherit', transition: 'all 0.15s', opacity: isEdit ? 0.6 : 1,
  })

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: isMobile ? 'flex-end' : 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{
        background: '#161b22', border: '1px solid #30363d',
        borderRadius: isMobile ? '16px 16px 0 0' : 12,
        padding: isMobile ? '20px 16px' : 24,
        width: '100%', maxWidth: isMobile ? '100%' : 560,
        maxHeight: isMobile ? '95vh' : '90vh', overflowY: 'auto',
      }}>

        {/* Title */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <h3 style={{ color: '#e6edf3', fontWeight: 700, fontSize: 16, margin: 0 }}>
            {isEdit ? `Edit Rule` : 'New Rule'}
          </h3>
          {isEdit && (
            <span style={{ fontSize: 11, color: '#8b949e', background: '#21262d', padding: '2px 8px', borderRadius: 4 }}>
              {existingRule!.strategy_type === 'SELL_COVERED_CALL' ? 'COVERED CALL' : 'SELL PUT'}
            </span>
          )}
        </div>

        {/* ── Strategy (locked when editing) ── */}
        <div style={{ marginBottom: 16 }}>
          {!isEdit && <label style={labelStyle}>Strategy</label>}
          {!isEdit && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" style={strategyBtnStyle(form.strategy_type === 'SELL_PUT')}
                onClick={() => setForm((f) => ({ ...f, strategy_type: 'SELL_PUT' }))}>
                Sell Put 📉
              </button>
              <button type="button" style={strategyBtnStyle(form.strategy_type === 'SELL_COVERED_CALL')}
                onClick={() => setForm((f) => ({ ...f, strategy_type: 'SELL_COVERED_CALL' }))}>
                Covered Call 📈
              </button>
            </div>
          )}
          {isCoveredCall ? (
            <div style={{ marginTop: isEdit ? 0 : 8, padding: '8px 12px', background: '#1f2d45', border: '1px solid #1f6feb44', borderRadius: 8, fontSize: 12, color: '#79c0ff' }}>
              📈 Requires <strong>100 shares</strong> per contract. Max contracts = floor(shares ÷ 100).
            </div>
          ) : (
            <div style={{ marginTop: isEdit ? 0 : 8, padding: '8px 12px', background: '#1a2d1e', border: '1px solid #3fb95044', borderRadius: 8, fontSize: 12, color: '#7ee787' }}>
              💵 Requires <strong>buying power</strong> = strike × $100 per contract.
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 14 }}>
          {field('Rule Name', 'name')}
          {field('Symbols (comma-separated, priority order)', 'symbolsText')}
          {field('Min DTE', 'min_dte', 'number')}
          {field('Max DTE', 'max_dte', 'number')}

          {/* ── Min Premium ── */}
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ ...labelStyle, marginBottom: 0 }}>Min Premium</label>
              <PillToggle
                labelA="% of stock price" labelB="$ amount"
                value={form.min_premium_mode === 'pct' ? 'a' : 'b'}
                onChange={(v) => setForm((f) => ({ ...f, min_premium_mode: v === 'a' ? 'pct' : 'dollar' }))}
              />
            </div>
            {form.min_premium_mode === 'pct' ? (
              <div>
                <input type="number" step="0.1" value={form.min_premium_pct}
                  onChange={(e) => setForm((f) => ({ ...f, min_premium_pct: parseFloat(e.target.value) || 0 }))}
                  style={inputStyle}
                  onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
                  onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')} />
                <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>e.g. 5% on a $38 stock → min premium ≈ $1.90</div>
              </div>
            ) : (
              <div>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#8b949e', fontSize: 13 }}>$</span>
                  <input type="number" step="0.01" value={form.min_premium_dollar}
                    onChange={(e) => setForm((f) => ({ ...f, min_premium_dollar: parseFloat(e.target.value) || 0 }))}
                    style={{ ...inputStyle, paddingLeft: 22 }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
                    onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')} />
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>e.g. $2.00 — scanner requires at least $2 mid-price premium</div>
              </div>
            )}
          </div>

          {field('Profit Target (e.g. 0.75 = 75%)', 'profit_target_pct', 'number', '0.05')}
          {!isCoveredCall && field('Daily Drop Trigger % (optional)', 'min_daily_drop_pct', 'number', '0.5')}

          {/* ── Position Size ── */}
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ ...labelStyle, marginBottom: 0 }}>Position Size</label>
              <PillToggle
                labelA={isCoveredCall ? '% of shares' : '% of buying power'}
                labelB="Fixed contracts"
                value={form.position_size_mode === 'pct' ? 'a' : 'b'}
                onChange={(v) => setForm((f) => ({ ...f, position_size_mode: v === 'a' ? 'pct' : 'contracts' }))}
              />
            </div>
            {form.position_size_mode === 'pct' ? (
              <div>
                <div style={{ position: 'relative' }}>
                  <input type="number" step="0.01" min="0.01" max="1" value={form.position_size_pct}
                    onChange={(e) => setForm((f) => ({ ...f, position_size_pct: parseFloat(e.target.value) || 0 }))}
                    style={{ ...inputStyle, paddingRight: 32 }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
                    onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')} />
                  <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#8b949e', fontSize: 13 }}>%</span>
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>
                  {isCoveredCall ? 'e.g. 1.0 (100%) = sell all available contracts (shares ÷ 100)' : 'e.g. 0.05 = 5% of buying power per trade'}
                </div>
              </div>
            ) : (
              <div>
                <input type="number" step="1" min="1" value={form.position_size_contracts}
                  onChange={(e) => setForm((f) => ({ ...f, position_size_contracts: parseInt(e.target.value) || 1 }))}
                  style={inputStyle}
                  onFocus={(e) => (e.currentTarget.style.borderColor = '#58a6ff')}
                  onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')} />
                <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>
                  {isCoveredCall ? 'e.g. 1 = sell 1 contract (requires 100 shares). Capped by shares owned.' : 'e.g. 2 = always trade exactly 2 contracts (if buying power allows)'}
                </div>
              </div>
            )}
          </div>

          {field('Max Open Positions', 'max_open_positions', 'number')}
          {field('Scan Interval (minutes)', 'scan_interval_minutes', 'number')}
        </div>

        {/* ── Assignment Management ── */}
        <div style={{ marginTop: 20, padding: '16px', background: '#0d1117', border: '1px solid #30363d', borderRadius: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
            ITM / Assignment Management
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <label style={{ fontSize: 12, color: '#e6edf3', fontWeight: 500 }}>When position goes ITM</label>
            <PillToggle
              labelA="Let Assign"
              labelB="Roll"
              value={form.itm_action === 'let_assign' ? 'a' : 'b'}
              onChange={(v) => setForm((f) => ({ ...f, itm_action: v === 'a' ? 'let_assign' : 'roll' }))}
            />
          </div>

          {form.itm_action === 'let_assign' ? (
            <div style={{ padding: '8px 12px', background: '#161b22', border: '1px solid #30363d', borderRadius: 8, fontSize: 12, color: '#8b949e' }}>
              🏷️ Position will be allowed to expire and get assigned at expiration. No action taken.
            </div>
          ) : (
            <div>
              <div style={{ padding: '8px 12px', background: '#2d2214', border: '1px solid #d2992244', borderRadius: 8, fontSize: 12, color: '#d29922', marginBottom: 12 }}>
                🔄 When ITM and DTE ≤ threshold, ThetaFlow will BTC the current position and STO a new OTM option at the closest available premium.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4 }}>
                    Roll when DTE ≤
                  </label>
                  <input
                    type="number" min="1" max="60" step="1"
                    value={form.roll_when_dte}
                    onChange={(e) => setForm((f) => ({ ...f, roll_when_dte: parseInt(e.target.value) || 7 }))}
                    style={{ ...inputStyle }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = '#d29922')}
                    onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')}
                  />
                  <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>days to expiry (e.g. 7)</div>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4 }}>
                    Roll out to
                  </label>
                  <select
                    value={form.roll_target_weeks}
                    onChange={(e) => setForm((f) => ({ ...f, roll_target_weeks: parseInt(e.target.value) }))}
                    style={{ ...inputStyle, cursor: 'pointer' }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = '#d29922')}
                    onBlur={(e) => (e.currentTarget.style.borderColor = '#30363d')}
                  >
                    <option value={1}>1 week out</option>
                    <option value={2}>2 weeks out</option>
                    <option value={3}>3 weeks out</option>
                    <option value={4}>4 weeks out (1 month)</option>
                    <option value={6}>6 weeks out</option>
                    <option value={8}>8 weeks out (2 months)</option>
                  </select>
                  <div style={{ marginTop: 4, fontSize: 11, color: '#8b949e' }}>from the roll date</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 20, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{
            padding: '8px 18px', fontSize: 13, background: '#21262d',
            color: '#8b949e', border: '1px solid #30363d', borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            Cancel
          </button>
          <button onClick={save} disabled={saving || !form.name} style={{
            padding: '8px 18px', fontSize: 13, fontWeight: 600,
            background: saving || !form.name ? '#21262d' : '#1f6feb',
            color: saving || !form.name ? '#484f58' : '#fff',
            border: 'none', borderRadius: 8,
            cursor: saving || !form.name ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}>
            {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Save Rule'}
          </button>
        </div>
      </div>
    </div>
  )
}
