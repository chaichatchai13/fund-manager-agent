import React, { useState } from 'react'
import { ThetaFlowLogo } from './ThetaFlowLogo'

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (res.ok) {
        onLogin()
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.detail ?? 'Invalid password')
      }
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0d1117',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: 16,
        padding: '40px 36px',
        width: '100%',
        maxWidth: 380,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 32 }}>
          <ThetaFlowLogo size={48} />
          <div style={{ marginTop: 12, fontSize: 22, fontWeight: 700, color: '#e6edf3', letterSpacing: '-0.3px' }}>
            Theta<span style={{ color: '#3fb950' }}>Flow</span>
          </div>
          <div style={{ marginTop: 4, fontSize: 13, color: '#8b949e' }}>
            Automated options trading
          </div>
        </div>

        {/* Form */}
        <form onSubmit={submit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#8b949e', marginBottom: 6 }}>
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoFocus
              style={{
                width: '100%',
                padding: '10px 14px',
                fontSize: 14,
                background: '#21262d',
                border: `1px solid ${error ? '#f85149' : '#30363d'}`,
                borderRadius: 8,
                color: '#e6edf3',
                outline: 'none',
                fontFamily: 'inherit',
                boxSizing: 'border-box',
                transition: 'border-color 0.15s',
              }}
              onFocus={(e) => { if (!error) e.currentTarget.style.borderColor = '#58a6ff' }}
              onBlur={(e) => { if (!error) e.currentTarget.style.borderColor = '#30363d' }}
            />
          </div>

          {error && (
            <div style={{
              marginBottom: 14,
              padding: '8px 12px',
              background: '#2d1515',
              border: '1px solid #f8514944',
              borderRadius: 8,
              fontSize: 13,
              color: '#f85149',
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            style={{
              width: '100%',
              padding: '10px 0',
              fontSize: 14,
              fontWeight: 600,
              background: loading || !password ? '#21262d' : '#1f6feb',
              color: loading || !password ? '#484f58' : '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: loading || !password ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              transition: 'background 0.15s',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
