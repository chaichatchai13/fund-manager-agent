import React, { useEffect, useState, useCallback } from 'react'

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

  // Collect all unique stocks from watchlist
  const allStocks = Array.from(new Set(watchlist.flatMap((w) => w.stocks))).sort()
  // Collect all unique handles
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
        body: JSON.stringify({ stocks }),
      })
      await fetchFeed()
    } catch { /* ignore */ }
    setRefreshing(false)
  }

  // Apply handle filter client-side (API only filters by stock)
  const visiblePosts = filterHandle === 'all'
    ? posts
    : posts.filter((p) => p.x_handle === filterHandle)

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', minHeight: 0 }}>

      {/* ── Left panel: Watchlist ─────────────────────────────────────────── */}
      <div style={{
        flex: '0 0 280px',
        background: CARD_BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BORDER}` }}>
          <h3 style={{ color: '#e6edf3', fontWeight: 600, fontSize: 14, margin: 0 }}>X Watchlist</h3>
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

      {/* ── Right panel: Feed ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Feed toolbar */}
        <div style={{
          background: CARD_BG,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: '12px 16px',
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
        }}>
          {/* Handle filter */}
          <select
            value={filterHandle}
            onChange={(e) => setFilterHandle(e.target.value)}
            style={{ ...inputBase, width: 'auto', minWidth: 120, cursor: 'pointer' }}
          >
            <option value="all">All accounts</option>
            {allHandles.map((h) => (
              <option key={h} value={h}>@{h}</option>
            ))}
          </select>

          {/* Stock filter */}
          <select
            value={filterStock}
            onChange={(e) => setFilterStock(e.target.value)}
            style={{ ...inputBase, width: 'auto', minWidth: 100, cursor: 'pointer' }}
          >
            <option value="all">All stocks</option>
            {allStocks.map((s) => (
              <option key={s} value={s}>${s}</option>
            ))}
          </select>

          <div style={{ flex: 1 }} />

          <button
            onClick={refresh}
            disabled={refreshing}
            style={{
              background: refreshing ? '#21262d' : BLUE_BTN,
              color: refreshing ? MUTED : '#fff',
              border: 'none',
              borderRadius: 7,
              padding: '7px 14px',
              fontSize: 13,
              fontWeight: 600,
              cursor: refreshing ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {refreshing ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>

        {/* Posts */}
        {loadingFeed && (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: '#484f58', fontSize: 13 }}>
            Loading feed…
          </div>
        )}

        {!loadingFeed && visiblePosts.length === 0 && (
          <div style={{
            background: CARD_BG,
            border: `1px solid ${BORDER}`,
            borderRadius: 12,
            padding: '40px 20px',
            textAlign: 'center',
            color: '#484f58',
            fontSize: 13,
          }}>
            No posts found. Add accounts to the watchlist and click Refresh.
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {visiblePosts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Watchlist row ─────────────────────────────────────────────────────────────
function WatchlistRow({
  entry,
  isLast,
  onRemove,
}: {
  entry: WatchlistEntry
  isLast: boolean
  onRemove: () => void
}) {
  return (
    <div style={{
      padding: '12px 16px',
      borderBottom: isLast ? 'none' : `1px solid #21262d`,
    }}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#1c2128')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: '#e6edf3' }}>
            @{entry.x_handle}
          </div>
          {entry.display_name && (
            <div style={{ fontSize: 11, color: MUTED, marginTop: 1 }}>{entry.display_name}</div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {entry.stocks.map((s) => (
              <span key={s} style={{
                background: '#1f2937', color: '#58a6ff',
                border: '1px solid #1f6feb44',
                borderRadius: 4, padding: '1px 6px',
                fontSize: 11, fontWeight: 600,
              }}>
                ${s}
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onRemove}
          style={{
            color: '#484f58', fontSize: 11,
            background: 'none', border: 'none',
            cursor: 'pointer', padding: '2px 4px',
            fontFamily: 'inherit', flexShrink: 0, marginLeft: 8,
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
    setSaving(true)
    setError('')
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
        setSaving(false)
        return
      }
      setHandle('')
      setStocksText('')
      onAdded()
    } catch {
      setError('Network error')
    }
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
    <div style={{ padding: '14px 16px', borderTop: `1px solid ${BORDER}`, background: BG }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: MUTED, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
        Add Account
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={labelSt}>Handle</label>
        <input
          type="text"
          placeholder="@unusual_whales"
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          style={inputBase}
          onFocus={focusInput}
          onBlur={blurInput}
        />
      </div>
      <div style={{ marginBottom: 10 }}>
        <label style={labelSt}>Stocks (comma or space separated)</label>
        <input
          type="text"
          placeholder="TSLA, NVDA"
          value={stocksText}
          onChange={(e) => setStocksText(e.target.value)}
          style={inputBase}
          onFocus={focusInput}
          onBlur={blurInput}
        />
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

  const askAgent = () => {
    const msg = `Tell me more about this $${post.stock} post from @${post.x_handle}: ${post.summary || post.content.slice(0, 200)}`
    window.dispatchEvent(new CustomEvent('open-chat', { detail: { message: msg } }))
  }

  return (
    <div style={{
      background: CARD_BG,
      border: `1px solid ${BORDER}`,
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      {/* Card header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 16px',
        borderBottom: `1px solid #21262d`,
        flexWrap: 'wrap',
      }}>
        <span style={{
          background: '#1f2937', color: '#58a6ff',
          border: '1px solid #1f6feb44',
          borderRadius: 4, padding: '1px 7px',
          fontSize: 12, fontWeight: 700,
        }}>
          ${post.stock}
        </span>
        <span style={{ fontSize: 13, color: MUTED }}>·</span>
        <span style={{ fontSize: 13, color: '#58a6ff', fontWeight: 500 }}>@{post.x_handle}</span>
        <span style={{ fontSize: 13, color: MUTED }}>·</span>
        <span style={{ fontSize: 12, color: '#484f58' }}>{relativeTime(post.posted_at)}</span>
      </div>

      {/* Card body */}
      <div style={{ padding: '12px 16px' }}>
        {/* Summary */}
        {post.summary && (
          <div style={{
            background: '#1a2d1e',
            border: '1px solid #3fb95022',
            borderRadius: 8,
            padding: '8px 12px',
            marginBottom: 10,
          }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: GREEN, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Summary
            </span>
            <p style={{ fontSize: 13, color: '#cae8ca', margin: '4px 0 0', lineHeight: 1.55 }}>
              {post.summary}
            </p>
          </div>
        )}

        {/* Full content (if different from summary or no summary) */}
        {!post.summary && (
          <p style={{ fontSize: 13, color: '#c9d1d9', lineHeight: 1.6, margin: '0 0 10px' }}>
            {post.content}
          </p>
        )}

        {/* Images */}
        {post.image_urls && post.image_urls.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            {post.image_urls.map((url, i) => (
              <img
                key={i}
                src={url}
                alt="Post image"
                style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8, border: `1px solid ${BORDER}`, objectFit: 'cover' }}
              />
            ))}
          </div>
        )}

        {/* Referenced content (collapsible) */}
        {post.referenced_content && (
          <div style={{ marginBottom: 10 }}>
            <button
              onClick={() => setRefExpanded((v) => !v)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: 'none',
                border: 'none',
                color: MUTED,
                fontSize: 12,
                cursor: 'pointer',
                padding: '2px 0',
                fontFamily: 'inherit',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#e6edf3')}
              onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
            >
              <span style={{ transition: 'transform 0.15s', display: 'inline-block', transform: refExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
                ▶
              </span>
              Referenced post
            </button>
            {refExpanded && (
              <div style={{
                marginTop: 8,
                padding: '10px 12px',
                background: '#21262d',
                border: `1px solid ${BORDER}`,
                borderRadius: 8,
                fontSize: 12,
                color: '#8b949e',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap' as const,
              }}>
                {post.referenced_content}
              </div>
            )}
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
          <a
            href={`https://x.com/${post.x_handle}/status/${post.post_id}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: 12,
              color: MUTED,
              textDecoration: 'none',
              padding: '4px 10px',
              border: `1px solid ${BORDER}`,
              borderRadius: 6,
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLAnchorElement
              el.style.color = '#58a6ff'
              el.style.borderColor = '#1f6feb44'
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLAnchorElement
              el.style.color = MUTED
              el.style.borderColor = BORDER
            }}
          >
            Read full post ↗
          </a>
          <button
            onClick={askAgent}
            style={{
              fontSize: 12,
              color: '#e6edf3',
              background: BLUE_BTN,
              border: 'none',
              borderRadius: 6,
              padding: '4px 10px',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontWeight: 500,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#388bfd')}
            onMouseLeave={(e) => (e.currentTarget.style.background = BLUE_BTN)}
          >
            Ask agent →
          </button>
        </div>
      </div>
    </div>
  )
}
