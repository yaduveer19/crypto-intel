'use client'
import React, { useState } from 'react'
import { copilotAnalyzeMarkets } from '@/lib/api'

export default function MarketScanner() {
  const [reply, setReply] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scan = async () => {
    setLoading(true); setError(null); setReply(null)
    try {
      const r = await copilotAnalyzeMarkets()
      setReply(r.reply || 'No reply')
      setSnapshot(r.snapshot || null)
    } catch (e: any) {
      setError(e.message || 'Scan failed')
    }
    setLoading(false)
  }

  const verdictChip = (sym: string) => {
    const s = snapshot?.[sym]
    if (!s) return null
    const lines = reply?.split('\n') || []
    const line = lines.find((l: string) => l.toUpperCase().includes(sym.replace('USDT', '')))
    const call = line?.toUpperCase().includes('LONG') ? 'LONG' : line?.toUpperCase().includes('SHORT') ? 'SHORT' : 'WAIT'
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
        call === 'LONG' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
        : call === 'SHORT' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
        : 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/30'
      }`}>{call}</span>
    )
  }

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-white">🔭 Market Scanner</h3>
        <button onClick={scan} disabled={loading}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent-blue hover:bg-accent-blue/80 text-white disabled:opacity-50 transition">
          {loading ? 'Scanning all markets...' : '⚡ Analyze All Markets'}
        </button>
      </div>

      {error && <p className="text-xs text-accent-red mb-2">{error}</p>}

      {snapshot && (
        <div className="flex gap-2 mb-3">
          {Object.entries(snapshot).map(([sym, s]: [string, any]) => (
            <div key={sym} className="flex-1 bg-dark-700/50 rounded-lg p-2 text-center">
              <div className="text-[10px] text-text-secondary">{sym.replace('USDT', '')}</div>
              <div className="text-xs font-bold text-white font-mono">{s.price > 1000 ? s.price.toLocaleString(undefined, { maximumFractionDigits: 0 }) : s.price.toFixed(2)}</div>
              <div className={`text-[9px] font-semibold ${s.change_24h_pct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>{s.change_24h_pct >= 0 ? '+' : ''}{s.change_24h_pct}%</div>
              <div className="mt-1">{verdictChip(sym)}</div>
            </div>
          ))}
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
