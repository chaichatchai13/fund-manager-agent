import { useEffect, useRef, useState } from 'react'
import type { OptionPosition } from '../types'

interface WsMessage {
  type: 'initial_state' | 'position_update' | 'price_update'
  positions?: OptionPosition[]
  position_id?: string
  option_symbol?: string
  current_price?: number
  unrealized_pnl?: number
  pnl_pct?: number
}

export function useWebSocket() {
  const [positions, setPositions] = useState<OptionPosition[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      reconnectTimeout.current = setTimeout(connect, 3000)
    }
    ws.onerror = () => ws.close()

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'initial_state' && msg.positions) {
          setPositions(msg.positions)
        } else if (msg.type === 'position_update' && msg.position_id) {
          setPositions((prev) =>
            prev.map((p) =>
              p.id === msg.position_id
                ? { ...p, current_price: msg.current_price ?? p.current_price, unrealized_pnl: msg.unrealized_pnl ?? p.unrealized_pnl }
                : p
            )
          )
        }
      } catch {
        // ignore parse errors
      }
    }
  }

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      wsRef.current?.close()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { positions, connected, setPositions }
}
