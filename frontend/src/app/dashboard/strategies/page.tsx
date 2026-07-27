'use client'
import React, { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

interface Strategy {
  key: string
  name: string
  description: string
  default_params: Record<string, any>
}

interface UserStrat {
  id: number
  strategy_key: string
  name: string
  description: string
  symbol: string
  is_enabled: boolean
  params: Record<string, any>
}

export default function StrategiesPage() {
  const { token } = useAuth()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [userStrats, setUserStrats] = useState<UserStrat[]>([])
  const [loading, setLoading] = useState(true)
  const [configuring, setConfiguring] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchData = async () => {
    try {
      const [s, u] = await Promise.all([
        fetch(`${API}/api/strategies/list`, { headers }).then(r => r.json()),
        fetch(`${API}/api/strategies/my`, { headers }).then(r => r.json()),
      ])
      setStrategies(Array.isArray(s) ? s : [])
      setUserStrats(Array.isArray(u) ? u : [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { if (token) fetchData() }, [token])

  const configure = async (strategyKey: string, symbol: string, isEnabled: boolean) => {
    setConfiguring(strategyKey)
    setMsg('')
    try {
      const r = await fetch(`${API}/api/strategies/configure`, {
        method: 'POST', headers,
        body: JSON.stringify({ strategy_key: strategyKey, symbol, is_enabled: isEnabled }),
      })
      const d = await r.json()
      setMsg(d.message || 'Configured')
      fetchData()
    } catch (e: any) {
      setMsg('Failed: ' + e.message)
    }
    setConfiguring(null)
  }

  const runAll = async () => {
    setMsg('Running all strategies...')
    try {
      const r = await fetch(`${API}/api/strategies/run-all`, { method: 'POST', headers })
      const d = await r.json()
      setMsg(`${d.signals_generated || 0} signals generated!`)
      fetchData()
    } catch (e: any) {
      setMsg('Error: ' + e.message)
    }
  }

  const isEnabled = (key: string, sym: string) => userStrats.some(u => u.strategy_key === key && u.symbol === sym && u.is_enabled)

  if (loading) return <div className="text-text-secondary animate-pulse">Loading strategies...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Trading Strategies</h1>
        <button onClick={runAll} className="bg-accent-purple/20 text-accent-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-purple/30 transition">
          🚀 Run All Strategies
        </button>
      </div>

      {msg && <div className="bg-dark-700/50 border border-dark-500 rounded-lg px-4 py-2 text-sm text-text-secondary">{msg}</div>}

      <div className="grid gap-4">
        {strategies.map((strat) => (
          <div key={strat.key} className="glass rounded-xl p-5 border border-dark-500">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-white font-semibold text-lg">{strat.name}</h3>
                <p className="text-text-secondary text-sm">{strat.description}</p>
              </div>
            </div>

            <div className="text-xs text-text-secondary mb-3">Default params: {JSON.stringify(strat.default_params)}</div>

            <div className="grid grid-cols-3 gap-3">
              {SYMBOLS.map(sym => {
                const enabled = isEnabled(strat.key, sym)
                return (
                  <button key={sym}
                    onClick={() => configure(strat.key, sym, !enabled)}
                    disabled={configuring === strat.key}
                    className={`p-3 rounded-lg border text-sm font-medium transition ${
                      enabled
                        ? 'bg-accent-green/10 text-accent-green border-accent-green/30'
                        : 'bg-dark-700 text-text-secondary border-dark-500 hover:text-white'
                    }`}>
                    <div>{sym.replace('USDT', '')}/USDT</div>
                    <div className="text-[10px] mt-1">{enabled ? '✅ Active' : 'Click to enable'}</div>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
