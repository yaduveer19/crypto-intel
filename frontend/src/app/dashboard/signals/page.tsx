'use client'
import React, { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { getGradedSignals } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SignalsPage() {
  const { token } = useAuth()
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [graded, setGraded] = useState<Record<string, any>>({})

  useEffect(() => {
    if (!token) return
    fetch(`${API}/api/strategies/signals`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(d => {
        const list = Array.isArray(d) ? d : []
        setSignals(list)
        const pairs = new Map<string, { symbol: string; strategy: string }>()
        list.forEach((s: any) => {
          if (s.symbol && s.strategy) pairs.set(`${s.symbol}|${s.strategy}`, { symbol: s.symbol, strategy: s.strategy })
        })
        // Grade each unique (symbol, strategy) — historical calls scored TP / SL / open
        pairs.forEach(async ({ symbol, strategy }, key) => {
          try {
            const g = await getGradedSignals(symbol, strategy, '15m')
            if (g && !g.error && g.summary && g.summary.total > 0) {
              setGraded(prev => ({ ...prev, [key]: g.summary }))
            }
          } catch {}
        })
      })
      .catch(() => {}).finally(() => setLoading(false))
  }, [token])

  const biasColor = (b: string) => b === 'BULL' ? 'text-accent-green' : b === 'BEAR' ? 'text-accent-red' : 'text-accent-yellow'

  if (loading) return <div className="text-text-secondary animate-pulse">Loading signals...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Trade Signals</h1>

      {signals.length === 0 && (
        <div className="glass rounded-xl p-8 text-center border border-dark-500">
          <p className="text-text-secondary">No signals yet. Configure strategies on the Strategies page and run them.</p>
        </div>
      )}

      <div className="space-y-3">
        {signals.map((s) => {
          const g = graded[`${s.symbol}|${s.strategy}`]
          return (
          <div key={s.id} className="glass rounded-xl p-4 border border-dark-500">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`text-lg font-bold ${biasColor(s.bias)}`}>{s.bias}</span>
                <span className="text-xs bg-dark-600 text-text-secondary px-2 py-0.5 rounded">{s.tier}</span>
                <span className="text-sm text-white">{s.symbol}</span>
                <span className="text-xs text-text-secondary bg-dark-700 px-2 py-0.5 rounded">{s.strategy}</span>
                {g && (
                  <span className="text-[10px] px-2 py-0.5 rounded border border-dark-500 text-text-secondary font-mono"
                    title={`Historical grade of this strategy: ${g.target_hit} target · ${g.stop_hit} stop · ${g.open} open`}>
                    🎯 {g.target_hit}TP · {g.stop_hit}SL · {g.open}▶ <span className={Number(g.win_rate) >= 50 ? 'text-accent-green' : 'text-accent-red'}>{g.win_rate}%</span>
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {s.delivered_telegram && <span className="text-[10px] text-accent-blue">📱 Telegram</span>}
                <span className="text-xs text-text-secondary">{s.time ? new Date(s.time).toLocaleString() : ''}</span>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-3">
              <div className="bg-dark-700/50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-text-secondary">Entry</div>
                <div className="text-sm font-mono text-white">${s.entry?.toLocaleString()}</div>
              </div>
              <div className="bg-dark-700/50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-text-secondary">SL</div>
                <div className="text-sm font-mono text-accent-red">${s.sl?.toLocaleString()}</div>
              </div>
              <div className="bg-dark-700/50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-text-secondary">TP1</div>
                <div className="text-sm font-mono text-accent-green">${s.tp1?.toLocaleString()}</div>
              </div>
              <div className="bg-dark-700/50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-text-secondary">TP2</div>
                <div className="text-sm font-mono text-accent-blue">${s.tp2?.toLocaleString()}</div>
              </div>
            </div>
            {s.reasoning && <p className="text-xs text-text-secondary mt-2 italic">{s.reasoning}</p>}
          </div>
          )
        })}
      </div>
    </div>
  )
}
