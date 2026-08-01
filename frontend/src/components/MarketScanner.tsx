'use client'
import React, { useState, useEffect, useCallback } from 'react'
import { copilotAnalyzeMarkets, getVerdict, getPrice } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

export default function MarketScanner() {
  const [reply, setReply] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [instant, setInstant] = useState<any>(null)

  // Instant rule-based verdicts on mount — no LLM needed, info hamesha visible
  const loadInstant = useCallback(async () => {
    const out: Record<string, any> = {}
    await Promise.all(SYMBOLS.map(async (sym) => {
      try {
        const [v, p] = await Promise.all([getVerdict(sym), getPrice(sym)])
        out[sym] = { ...v, price: p.price ?? v.entry_price }
      } catch {}
    }))
    setInstant(out)
  }, [])

  useEffect(() => { loadInstant() }, [loadInstant])

  const scan = async () => {
    setLoading(true); setError(null); setReply(null)
    try {
      const r = await copilotAnalyzeMarkets()
      setReply(r.reply || 'No reply')
      setSnapshot(r.snapshot || null)
      if (r.snapshot) setInstant(r.snapshot)
    } catch (e: any) {
      setError('LLM scan failed — showing instant rule-based verdicts below')
    }
    setLoading(false)
    loadInstant()
  }

  const chip = (sym: string, s: any) => {
    const bias = s?.bias
    const call = bias === 'BULL' ? 'LONG' : bias === 'BEAR' ? 'SHORT' : 'WAIT'
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
        call === 'LONG' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
        : call === 'SHORT' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
        : 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/30'
      }`}>{call}</span>
    )
  }

  const data = instant || snapshot || {}
  const hasData = Object.keys(data).length > 0

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-white">🔭 Market Scanner</h3>
        <button onClick={scan} disabled={loading}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent-blue hover:bg-accent-blue/80 text-white disabled:opacity-50 transition">
          {loading ? 'Scanning...' : '⚡ Analyze All Markets'}
        </button>
      </div>

      {error && <p className="text-xs text-accent-yellow mb-2">{error}</p>}

      {!hasData && !loading && <p className="text-xs text-text-secondary">Loading market verdicts...</p>}

      {hasData && (
        <div className="flex gap-2 mb-3">
          {SYMBOLS.map(sym => {
            const s = data[sym]
            if (!s) return null
            const price = s.price
            return (
              <div key={sym} className="flex-1 bg-dark-700/50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-text-secondary">{sym.replace('USDT', '')}</div>
                <div className="text-xs font-bold text-white font-mono">{price ? (price > 1000 ? price.toLocaleString(undefined, { maximumFractionDigits: 0 }) : price.toFixed(2)) : '—'}</div>
                <div className={`text-[9px] font-semibold ${s.change_24h_pct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {s.change_24h_pct !== undefined ? `${s.change_24h_pct >= 0 ? '+' : ''}${s.change_24h_pct}%` : '—'}
                </div>
                <div className="mt-1">{chip(sym, s)}</div>
                {s.tier && <div className="text-[8px] text-text-secondary mt-0.5">{s.tier}</div>}
              </div>
            )
          })}
        </div>
      )}

      {reply && (
        <div className="text-xs text-text-secondary whitespace-pre-wrap max-h-64 overflow-y-auto bg-dark-700/40 rounded-lg p-3 border border-dark-600">
          {reply}
        </div>
      )}
    </div>
  )
}