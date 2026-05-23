/**
 * usePushNotifications — registers the service worker and subscribes to push.
 * Call this once in the Dashboard after login.
 */
import { useEffect } from 'react'

export function usePushNotifications() {
  useEffect(() => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return

    const setup = async () => {
      try {
        // Register service worker
        const reg = await navigator.serviceWorker.register('/sw.js')

        // Get VAPID public key from server
        const res = await fetch('/api/push/vapid-public-key')
        const { vapid_public_key } = await res.json()
        if (!vapid_public_key) return  // not configured

        // Check existing subscription
        let sub = await reg.pushManager.getSubscription()
        if (!sub) {
          // Request permission + subscribe
          const permission = await Notification.requestPermission()
          if (permission !== 'granted') return

          sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: _urlBase64ToUint8Array(vapid_public_key) as BufferSource,
          })
        }

        // Send subscription to server
        await fetch('/api/push/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            endpoint: sub.endpoint,
            keys: {
              p256dh: _arrayBufferToBase64(sub.getKey('p256dh')),
              auth: _arrayBufferToBase64(sub.getKey('auth')),
            },
          }),
        })
      } catch (err) {
        // Non-fatal — push is optional
        console.warn('Push notification setup failed:', err)
      }
    }

    setup()
  }, [])
}

function _urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

function _arrayBufferToBase64(buffer: ArrayBuffer | null): string {
  if (!buffer) return ''
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
}
