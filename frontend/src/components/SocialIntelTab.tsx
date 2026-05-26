import React, { useEffect, useRef, useState, useCallback } from 'react'
import type { ChatMessage } from '../types'

// ── Design tokens ─────────────────────────────────────────────────────────────
const BG = '#0d1117'
const CARD_BG = '#161b22'
const BORDER = '#30363d'
const MUTED = '#8b949e'
const GREEN = '#3fb950'
const BLUE_BTN = '#1f6feb'

// ── Types ─────────────────────────────────────────────────────────────────────
interface WatchlistEntry {
  id: string
  x_handle: string
  display_name: string
  stocks: string[]
}

interface SocialPost {
  id: string
  post_id: string
  x_handle: string
  stock: string
  content: string
  summary: string
  summary_language: string | null
  image_urls: string[]
  referenced_content: string | null
  posted_at: string
}

// ── Relative time helper ──────────────────────────────────────────────────────
function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) return 'Just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins} minute${mins !== 1 ? 's' : ''} ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} hour${hrs !== 1 ? 's' : ''} ago`
  const days = Math.floor(hrs / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return new Date(iso).toLocaleDateString()
}

// ── Shared input style ────────────────────────────────────────────────────────
const inputBase: React.CSSProperties = {
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

// ── SocialIntelTab ────────────────────────────────────────────────────────────
export function SocialIntelTab() {
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([])
  const [posts, setPosts] = useState<SocialPost[]>([])
  const [filterHandle, setFilterHandle] = useState<string>('all')
  const [filterStock, setFilterStock] = useState<string>('all')
  const [loadingFeed, setLoadingFeed] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [resummarizing, setResummarizing] = useState(false)
  const [language, setLanguage] = useState<string>(() => localStorage.getItem('social_lang') ?? 'English')

  // Seed language from server default on first visit (no localStorage key yet)
  useEffect(() => {
    if (localStorage.getItem('social_lang')) return   // user already has a preference
    fetch('/api/social/config')
      .then(r => r.json())
      .then(d => { if (d.default_language) setLanguage(d.default_language) })
      .catch(() => {})
  }, [])
  const [showWatchlist, setShowWatchlist] = useState(true)

  const LANGUAGES = ['English', 'Thai', 'Japanese', 'Chinese', 'Spanish', 'French', 'German', 'Korean']
  const isMobile = window.innerWidth < 900

  const allStocks = Array.from(new Set(watchlist.flatMap((w) => w.stocks))).sort()
  const allHandles = watchlist.map((w) => w.x_handle)

  const fetchWatchlist = async () => {
    try {
      const res = await fetch('/api/social/watchlist')
      if (res.ok) setWatchlist(await res.json())
    } catch { /* ignore */ }
  }

  const fetchFeed = useCallback(async () => {
    setLoadingFeed(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (filterStock !== 'all') params.set('stock', filterStock)
      const res = await fetch(`/api/social/feed?${params}`)
      if (res.ok) setPosts(await res.json())
    } catch { /* ignore */ }
    setLoadingFeed(false)
  }, [filterStock])

  useEffect(() => { fetchWatchlist() }, [])
  useEffect(() => { fetchFeed() }, [fetchFeed])

  const refresh = async () => {
    setRefreshing(true)
    const stocks = filterStock !== 'all' ? [filterStock] : allStocks
    try {
      await fetch('/api/social/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stocks, language }),
      })
      await fetchFeed()
    } catch { /* ignore */ }
    setRefreshing(false)
  }

  const visiblePosts = filterHandle === 'all'
    ? posts
    : posts.filter((p) => p.x_handle === filterHandle)

  // Posts whose summary_language doesn't match the selected language
  const staleCount = visiblePosts.filter(p => p.summary_language !== language).length

  const changeLanguage = (lang: string) => {
    setLanguage(lang)
    localStorage.setItem('social_lang', lang)
  }

  const applyLanguage = async () => {
    setResummarizing(true)
    try {
      const ids = visiblePosts.map((p) => p.post_id)
      await fetch('/api/social/resummary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_ids: ids.length ? ids : null, language }),
      })
      await fetchFeed()
    } catch { /* ignore */ }
    setResummarizing(false)
  }

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', minHeight: 0 }}>

      {/* ── Left panel: Watchlist ─────────────────────────────────────────── */}
      {(!isMobile || showWatchlist) && (
        <div style={{
          flex: `0 0 ${isMobile ? '100%' : '240px'}`,
          background: CARD_BG,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          overflow: 'hidden',
          position: isMobile ? undefined : 'sticky',
          top: isMobile ? undefined : 16,
          maxHeight: isMobile ? undefined : 'calc(100vh - 120px)',
          overflowY: 'auto',
        }}>
          <div style={{ padding: '12px 16px', borderBottom: `1px solid ${BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 14, margin: 0 }}>X Watchlist</h3>
            {isMobile && (
              <button onClick={() => setShowWatchlist(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', fontSize: 18 }}>×</button>
            )}
          </div>

          {watchlist.length === 0 && (
            <div style={{ padding: '20px 16px', color: '#484f58', fontSize: 13, textAlign: 'center' }}>
              No accounts yet.
            </div>
          )}

          {watchlist.map((entry, idx) => (
            <WatchlistRow
              key={entry.x_handle}
              entry={entry}
              isLast={idx === watchlist.length - 1}
              onRemove={() => {
                fetch(`/api/social/watchlist/${entry.x_handle}`, { method: 'DELETE' })
                  .then(fetchWatchlist)
              }}
            />
          ))}

          <AddWatchlistForm onAdded={fetchWatchlist} />
        </div>
      )}

      {/* ── Center panel: Feed ───────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Mobile toggle for watchlist */}
        {isMobile && !showWatchlist && (
          <button
            onClick={() => setShowWatchlist(true)}
            style={{
              marginBottom: 10, padding: '6px 12px', fontSize: 12,
              background: '#21262d', border: `1px solid ${BORDER}`,
              borderRadius: 7, color: MUTED, cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            ☰ Watchlist
          </button>
        )}

        {/* Feed toolbar */}
        <div style={{
          background: CARD_BG,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: '10px 14px',
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
        }}>
          <select
            value={filterHandle}
            onChange={(e) => setFilterHandle(e.target.value)}
            style={{ ...inputBase, width: 'auto', minWidth: 110, cursor: 'pointer', padding: '5px 8px', fontSize: 12 }}
          >
            <option value="all">All accounts</option>
            {allHandles.map((h) => (
              <option key={h} value={h}>@{h}</option>
            ))}
          </select>

          <select
            value={filterStock}
            onChange={(e) => setFilterStock(e.target.value)}
            style={{ ...inputBase, width: 'auto', minWidth: 90, cursor: 'pointer', padding: '5px 8px', fontSize: 12 }}
          >
            <option value="all">All stocks</option>
            {allStocks.map((s) => (
              <option key={s} value={s}>${s}</option>
            ))}
          </select>

          <div style={{ flex: 1 }} />

          {/* Language selector + Apply */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ fontSize: 13, color: MUTED }}>🌐</span>
            <select
              value={language}
              onChange={(e) => changeLanguage(e.target.value)}
              disabled={resummarizing}
              style={{
                ...inputBase,
                width: 'auto', minWidth: 90, cursor: resummarizing ? 'wait' : 'pointer',
                padding: '5px 8px', fontSize: 12,
                opacity: resummarizing ? 0.6 : 1,
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <button
              onClick={applyLanguage}
              disabled={resummarizing || staleCount === 0}
              title={staleCount === 0 ? `All posts already in ${language}` : `Re-summarize ${staleCount} post${staleCount !== 1 ? 's' : ''} in ${language}`}
              style={{
                padding: '5px 10px', fontSize: 12, fontWeight: 600,
                background: staleCount === 0 ? '#21262d' : '#1a3028',
                color: staleCount === 0 ? '#484f58' : GREEN,
                border: `1px solid ${staleCount === 0 ? BORDER : '#3fb95044'}`,
                borderRadius: 7, cursor: (resummarizing || staleCount === 0) ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit', whiteSpace: 'nowrap',
              }}
            >
              {resummarizing ? 'Translating…' : staleCount > 0 ? `Apply (${staleCount})` : 'Up to date ✓'}
            </button>
          </div>

          <button
            onClick={refresh}
            disabled={refreshing || resummarizing}
            style={{
              background: refreshing ? '#21262d' : BLUE_BTN,
              color: refreshing ? MUTED : '#fff',
              border: 'none', borderRadius: 7,
              padding: '5px 12px', fontSize: 12, fontWeight: 600,
              cursor: refreshing ? 'not-allowed' : 'pointer', fontFamily: 'inherit',
            }}
          >
            {refreshing ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>

        {loadingFeed && (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
            Loading feed…
          </div>
        )}

        {!loadingFeed && visiblePosts.length === 0 && (
          <div style={{
            background: CARD_BG, border: `1px solid ${BORDER}`,
            borderRadius: 12, padding: '40px 20px',
            textAlign: 'center', color: '#484f58', fontSize: 13,
          }}>
            No posts found. Add accounts to the watchlist and click Refresh.
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {visiblePosts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      </div>

      {/* ── Right panel: Inline Agent Chat ───────────────────────────────── */}
      {!isMobile && (
        <div style={{
          flex: '0 0 320px',
          position: 'sticky',
          top: 16,
          height: 'calc(100vh - 120px)',
        }}>
          <InlineChat posts={visiblePosts} />
        </div>
      )}

      {/* Mobile: floating chat button + bottom sheet */}
      {isMobile && (
        <MobileChatSheet posts={visiblePosts} />
      )}
    </div>
  )
}

// ── Inline Chat Panel ─────────────────────────────────────────────────────────
const SOCIAL_QUICK_PROMPTS = [
  'Summarize $IREN news',
  'What is unusual_whales saying?',
  'Should I sell a put on $IREN?',
  'Check IV rank for $TSLA',
  'Scan for opportunities',
]

function buildFeedContext(posts: SocialPost[]): object[] {
  if (posts.length === 0) return []
  const lines = posts.map((p, i) =>
    `${i + 1}. $${p.stock} — @${p.x_handle} (${relativeTime(p.posted_at)})\n   ${p.summary || p.content.slice(0, 300)}`
  ).join('\n\n')
  return [
    {
      role: 'user',
      content: `Here is the current Social Intel feed I'm looking at (${posts.length} post${posts.length !== 1 ? 's' : ''}):\n\n${lines}\n\nI'll ask you questions about these posts and the stocks mentioned.`,
    },
    {
      role: 'assistant',
      content: `Got it — I've read all ${posts.length} post${posts.length !== 1 ? 's' : ''} in your feed. Ask me anything about them.`,
    },
  ]
}

function InlineChat({ posts }: { posts: SocialPost[] }) {
  const contextRef = useRef<SocialPost[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: posts.length > 0
        ? `I've read all ${posts.length} post${posts.length !== 1 ? 's' : ''} in your feed. Ask me anything about them.`
        : "I'm watching the feed with you. Once posts load, I'll have full context of every summary. Ask me anything about the stocks in your watchlist.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiMessages, setApiMessages] = useState<object[]>(() => buildFeedContext(posts))
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Re-inject context when posts change (e.g. after Refresh)
  useEffect(() => {
    const prev = contextRef.current
    const changed = posts.length !== prev.length || posts.some((p, i) => p.id !== prev[i]?.id)
    if (!changed) return
    contextRef.current = posts
    setApiMessages(buildFeedContext(posts))
    if (posts.length > 0) {
      setMessages([{
        role: 'assistant',
        content: `I've read all ${posts.length} post${posts.length !== 1 ? 's' : ''} in your feed. Ask me anything about them.`,
      }])
    }
  }, [posts])

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
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error contacting agent. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      background: CARD_BG,
      border: `1px solid ${BORDER}`,
      borderRadius: 12,
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px',
        borderBottom: `1px solid ${BORDER}`,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'linear-gradient(135deg, #1f6feb, #3fb950)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, flexShrink: 0,
        }}>
          🤖
        </div>
        <div>
          <div style={{ color: '#e6edf3', fontWeight: 600, fontSize: 13 }}>
            Agent Chat
          </div>
          <div style={{ color: MUTED, fontSize: 10 }}>Discuss the feed with your AI</div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: GREEN, display: 'inline-block',
            animation: 'pulse 2s infinite',
          }} />
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '88%',
              padding: '8px 11px',
              borderRadius: msg.role === 'user' ? '14px 14px 3px 14px' : '14px 14px 14px 3px',
              background: msg.role === 'user' ? BLUE_BTN : '#21262d',
              color: msg.role === 'user' ? '#fff' : '#e6edf3',
              fontSize: 12.5,
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
              padding: '8px 11px', borderRadius: '14px 14px 14px 3px',
              background: '#21262d', color: MUTED, fontSize: 12.5,
            }}>
              <span style={{ animation: 'pulse 1.2s infinite' }}>Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div style={{
        padding: '6px 10px',
        borderTop: `1px solid #21262d`,
        display: 'flex',
        flexWrap: 'wrap',
        gap: 5,
        flexShrink: 0,
      }}>
        {SOCIAL_QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => sendMessage(p)}
            disabled={loading}
            style={{
              background: '#21262d', color: '#58a6ff',
              border: '1px solid #30363d', borderRadius: 5,
              padding: '2px 8px', fontSize: 10.5,
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#30363d')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#21262d')}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 12px',
        borderTop: `1px solid ${BORDER}`,
        display: 'flex',
        gap: 7,
        flexShrink: 0,
      }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder="Ask about the feed…"
          disabled={loading}
          style={{
            flex: 1,
            padding: '7px 11px',
            fontSize: 12.5,
            background: '#21262d',
            border: '1px solid #30363d',
            borderRadius: 7,
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
            padding: '7px 14px',
            background: loading || !input.trim() ? '#21262d' : BLUE_BTN,
            color: loading || !input.trim() ? '#484f58' : '#fff',
            border: 'none', borderRadius: 7,
            fontSize: 12.5, fontWeight: 600,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          ↑
        </button>
      </div>
    </div>
  )
}

// ── Mobile: floating chat button + slide-up sheet ─────────────────────────────
function MobileChatSheet({ posts }: { posts: SocialPost[] }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          style={{
            position: 'fixed', bottom: 20, right: 16, zIndex: 50,
            width: 52, height: 52, borderRadius: '50%',
            background: 'linear-gradient(135deg, #1f6feb, #3fb950)',
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, boxShadow: '0 4px 20px rgba(31,111,235,0.5)',
          }}
        >
          💬
        </button>
      )}

      {/* Sheet */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
          height: '65vh',
          background: CARD_BG,
          borderTop: `2px solid ${BORDER}`,
          borderRadius: '14px 14px 0 0',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 -8px 40px rgba(0,0,0,0.6)',
        }}>
          {/* Sheet handle */}
          <div style={{ padding: '10px', display: 'flex', justifyContent: 'center', flexShrink: 0 }}>
            <div style={{ width: 36, height: 4, borderRadius: 2, background: BORDER }} />
          </div>
          {/* Close */}
          <button
            onClick={() => setOpen(false)}
            style={{
              position: 'absolute', top: 8, right: 14,
              background: 'none', border: 'none', color: MUTED,
              fontSize: 22, cursor: 'pointer', lineHeight: 1,
            }}
          >
            ×
          </button>
          {/* Inline chat fills the sheet */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <InlineChat posts={posts} />
          </div>
        </div>
      )}
    </>
  )
}

// ── Watchlist row ─────────────────────────────────────────────────────────────
function WatchlistRow({
  entry, isLast, onRemove,
}: {
  entry: WatchlistEntry
  isLast: boolean
  onRemove: () => void
}) {
  return (
    <div
      style={{ padding: '10px 14px', borderBottom: isLast ? 'none' : `1px solid #21262d` }}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#1c2128')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: '#e6edf3' }}>@{entry.x_handle}</div>
          {entry.display_name && (
            <div style={{ fontSize: 11, color: MUTED, marginTop: 1 }}>{entry.display_name}</div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {entry.stocks.map((s) => (
              <span key={s} style={{
                background: '#1f2937', color: '#58a6ff',
                border: '1px solid #1f6feb44', borderRadius: 4,
                padding: '1px 6px', fontSize: 11, fontWeight: 600,
              }}>
                ${s}
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onRemove}
          style={{
            color: '#484f58', fontSize: 11, background: 'none', border: 'none',
            cursor: 'pointer', padding: '2px 4px', fontFamily: 'inherit',
            flexShrink: 0, marginLeft: 8,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#f85149')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#484f58')}
        >
          Remove
        </button>
      </div>
    </div>
  )
}

// ── Add watchlist form ────────────────────────────────────────────────────────
function AddWatchlistForm({ onAdded }: { onAdded: () => void }) {
  const [handle, setHandle] = useState('')
  const [stocksText, setStocksText] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const add = async () => {
    const cleanHandle = handle.replace(/^@/, '').trim()
    if (!cleanHandle) { setError('Handle is required'); return }
    setSaving(true); setError('')
    try {
      const stocks = stocksText
        .split(/[\s,]+/)
        .map((s) => s.replace(/^\$/, '').trim().toUpperCase())
        .filter(Boolean)
      const res = await fetch('/api/social/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x_handle: cleanHandle, stocks }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setError(d?.detail ?? 'Failed to add')
        setSaving(false); return
      }
      setHandle(''); setStocksText('')
      onAdded()
    } catch { setError('Network error') }
    setSaving(false)
  }

  const labelSt: React.CSSProperties = {
    display: 'block', fontSize: 10, fontWeight: 600,
    color: MUTED, marginBottom: 3,
    textTransform: 'uppercase', letterSpacing: '0.04em',
  }
  const focusInput = (e: React.FocusEvent<HTMLInputElement>) => { e.currentTarget.style.borderColor = '#58a6ff' }
  const blurInput = (e: React.FocusEvent<HTMLInputElement>) => { e.currentTarget.style.borderColor = '#30363d' }

  return (
    <div style={{ padding: '12px 14px', borderTop: `1px solid ${BORDER}`, background: BG }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: MUTED, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        Add Account
      </div>
      <div style={{ marginBottom: 7 }}>
        <label style={labelSt}>Handle</label>
        <input type="text" placeholder="@unusual_whales" value={handle}
          onChange={(e) => setHandle(e.target.value)}
          style={inputBase} onFocus={focusInput} onBlur={blurInput} />
      </div>
      <div style={{ marginBottom: 9 }}>
        <label style={labelSt}>Stocks (comma or space separated)</label>
        <input type="text" placeholder="TSLA, NVDA" value={stocksText}
          onChange={(e) => setStocksText(e.target.value)}
          style={inputBase} onFocus={focusInput} onBlur={blurInput} />
      </div>
      {error && <div style={{ fontSize: 11, color: '#f85149', marginBottom: 8 }}>{error}</div>}
      <button
        onClick={add}
        disabled={saving || !handle.trim()}
        style={{
          width: '100%',
          background: saving || !handle.trim() ? '#21262d' : BLUE_BTN,
          color: saving || !handle.trim() ? '#484f58' : '#fff',
          border: 'none', borderRadius: 7,
          padding: '7px 0', fontSize: 13, fontWeight: 600,
          cursor: saving || !handle.trim() ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
        }}
      >
        {saving ? 'Adding…' : 'Add'}
      </button>
    </div>
  )
}

// ── Post card ─────────────────────────────────────────────────────────────────
function PostCard({ post }: { post: SocialPost }) {
  const [refExpanded, setRefExpanded] = useState(false)

  return (
    <div style={{
      background: CARD_BG, border: `1px solid ${BORDER}`,
      borderRadius: 12, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '9px 14px', borderBottom: `1px solid #21262d`,
        flexWrap: 'wrap',
      }}>
        <span style={{
          background: '#1f2937', color: '#58a6ff',
          border: '1px solid #1f6feb44', borderRadius: 4,
          padding: '1px 7px', fontSize: 12, fontWeight: 700,
        }}>
          ${post.stock}
        </span>
        <span style={{ fontSize: 13, color: MUTED }}>·</span>
        <span style={{ fontSize: 13, color: '#58a6ff', fontWeight: 500 }}>@{post.x_handle}</span>
        <span style={{ fontSize: 13, color: MUTED }}>·</span>
        <span style={{ fontSize: 12, color: '#484f58' }}>{relativeTime(post.posted_at)}</span>
      </div>

      {/* Body */}
      <div style={{ padding: '11px 14px' }}>
        {post.summary && (
          <div style={{
            background: '#1a2d1e', border: '1px solid #3fb95022',
            borderRadius: 8, padding: '8px 11px', marginBottom: 10,
          }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: GREEN, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Summary
            </span>
            <p style={{ fontSize: 13, color: '#cae8ca', margin: '4px 0 0', lineHeight: 1.55 }}>
              {post.summary}
            </p>
          </div>
        )}

        {!post.summary && (
          <p style={{ fontSize: 13, color: '#c9d1d9', lineHeight: 1.6, margin: '0 0 10px' }}>
            {post.content}
          </p>
        )}

        {post.image_urls && post.image_urls.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            {post.image_urls.map((url, i) => (
              <img key={i} src={url} alt="Post image" style={{
                maxWidth: '100%', maxHeight: 260, borderRadius: 8,
                border: `1px solid ${BORDER}`, objectFit: 'cover',
              }} />
            ))}
          </div>
        )}

        {post.referenced_content && (
          <div style={{ marginBottom: 10 }}>
            <button
              onClick={() => setRefExpanded((v) => !v)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                background: 'none', border: 'none', color: MUTED,
                fontSize: 12, cursor: 'pointer', padding: '2px 0', fontFamily: 'inherit',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#e6edf3')}
              onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
            >
              <span style={{ transition: 'transform 0.15s', display: 'inline-block', transform: refExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
              Referenced post
            </button>
            {refExpanded && (
              <div style={{
                marginTop: 8, padding: '10px 12px',
                background: '#21262d', border: `1px solid ${BORDER}`,
                borderRadius: 8, fontSize: 12, color: '#8b949e',
                lineHeight: 1.6, whiteSpace: 'pre-wrap' as const,
              }}>
                {post.referenced_content}
              </div>
            )}
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 6 }}>
          <a
            href={`https://x.com/${post.x_handle}/status/${post.post_id}`}
            target="_blank" rel="noopener noreferrer"
            style={{
              fontSize: 12, color: MUTED, textDecoration: 'none',
              padding: '4px 10px', border: `1px solid ${BORDER}`, borderRadius: 6,
            }}
            onMouseEnter={(e) => { const el = e.currentTarget as HTMLAnchorElement; el.style.color = '#58a6ff'; el.style.borderColor = '#1f6feb44' }}
            onMouseLeave={(e) => { const el = e.currentTarget as HTMLAnchorElement; el.style.color = MUTED; el.style.borderColor = BORDER }}
          >
            Read full post ↗
          </a>
        </div>
      </div>
    </div>
  )
}
