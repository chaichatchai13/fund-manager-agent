import React, { useEffect, useRef, useState } from 'react'
import { ThetaFlowLogo } from './ThetaFlowLogo'
import type { ChatMessage } from '../types'

const CARD: React.CSSProperties = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 12,
  display: 'flex',
  flexDirection: 'column',
  height: 620,
}

const QUICK_PROMPTS = [
  'Show open positions',
  'Weekly performance',
  'Create a rule',
  'Scan now',
  'List all rules',
]

interface ChatPaneProps {
  prefillMessage?: string
  onPrefillConsumed?: () => void
}

export function ChatPane({ prefillMessage, onPrefillConsumed }: ChatPaneProps = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Hey! I'm your ThetaFlow agent — your automated options income system. I run two strategies for you:\n\n📉 Sell Puts — collect premium below market price, sized to your available cash\n📈 Covered Calls — generate income on shares you already hold\n\nI can create & manage rules, monitor open positions, trigger scans, close trades, and analyze your P&L.\n\nWhat would you like to do?",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiMessages, setApiMessages] = useState<object[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  // Pre-fill input when "Ask agent →" is clicked from Social Intel tab
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

  return (
    <div style={CARD}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ThetaFlowLogo size={32} />
          <div>
            <div style={{ color: '#e6edf3', fontWeight: 700, fontSize: 15 }}>
              Theta<span style={{ color: '#3fb950' }}>Flow</span>
              <span style={{ marginLeft: 8, background: '#1a3028', color: '#3fb950', fontSize: 10, padding: '1px 7px', borderRadius: 4, fontWeight: 600, verticalAlign: 'middle' }}>Agent</span>
            </div>
            <div style={{ color: '#8b949e', fontSize: 11, marginTop: 1 }}>
              Sell Puts · Covered Calls · Automated income
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
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
