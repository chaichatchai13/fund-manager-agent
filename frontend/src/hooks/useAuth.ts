import { useCallback, useEffect, useState } from 'react'

interface AuthState {
  authenticated: boolean
  loading: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({ authenticated: false, loading: true })

  const check = useCallback(async () => {
    try {
      const res = await fetch('/auth/me')
      setState({ authenticated: res.ok, loading: false })
    } catch {
      setState({ authenticated: false, loading: false })
    }
  }, [])

  useEffect(() => { check() }, [check])

  const logout = useCallback(async () => {
    await fetch('/auth/logout', { method: 'POST' })
    setState({ authenticated: false, loading: false })
  }, [])

  return { ...state, recheck: check, logout }
}
