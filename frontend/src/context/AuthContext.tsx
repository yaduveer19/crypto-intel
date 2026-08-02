'use client'
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface User {
  id: number
  email: string
  name: string
  plan: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem('token')
    if (t) {
      setToken(t)
      fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${t}` } })
        .then((r) => r.ok ? r.json() : Promise.reject())
        .then((u) => setUser(u))
        .catch(() => { localStorage.removeItem('token'); setToken(null) })
        .finally(() => setLoading(false))
    } else {
      // Login bypass: demo session so all pages work without auth
      setToken('demo-session')
      setUser({ id: 1, email: 'demo@cryptointel.io', name: 'Demo User', plan: 'pro' })
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const r = await fetch(`${API}/api/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Login failed') }
    const d = await r.json()
    localStorage.setItem('token', d.token)
    setToken(d.token)
    setUser(d.user)
  }, [])

  const register = useCallback(async (email: string, password: string, name: string) => {
    const r = await fetch(`${API}/api/auth/register`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    })
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Registration failed') }
    const d = await r.json()
    localStorage.setItem('token', d.token)
    setToken(d.token)
    setUser(d.user)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
