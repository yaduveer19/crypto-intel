'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getIntelPatterns } from '@/lib/api'

const biasStyle = (bias: string) =>
  bias === 'BULL' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
  : bias === 'BEAR' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
  : 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/30'

export default function ChartPatternsPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getIntelPatterns(symbol)) } catch {}
    setLoading(false)
  }, [symbol])

  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i) }, [load])

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">📐 Chart Patterns</h3>
        <div className="flex items-center gap-2">
          {data?.signal && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${biasStyle(data.signal)}`}>
              {data.signal} ({data.bull_count}-{data.bear_count})
            </span>
          )}
          <span className="text-[10px] text-text-secondary">real klines · 1h</span>
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Scanning patterns...</p>}

      {data && data.patterns?.length === 0 && (
        <p className="text-text-secondary text-xs">No patterns detected — market structuring.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {data?.patterns?.map((p: any, i: number) => (
          <div key={i} className="bg-dark-700/50 rounded-lg p-3 border border-dark-600 hover:border-accent-blue/40 transition">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-semibold text-white">{p.pattern}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${biasStyle(p.bias)}`}>{p.bias}</span>
            </div>
            <div className="flex items-center gap-2 mb-1.5">
              <div className="flex-1 h-1.5 bg-dark-600 rounded overflow-hidden">
                <div className={`h-full rounded ${p.bias === 'BULL' ? 'bg-accent-green' : p.bias === 'BEAR' ? 'bg-accent-red' : 'bg-accent-yellow'}`}
                  style={{ width: `${(p.confidence || 0) * 100}%` }} />
              </div>
              <span className="text-[10px] font-mono text-text-secondary">{Math.round((p.confidence || 0) * 100)}%</span>
              {p.confirmed ? (
                <span className="text-[9px] text-accent-green font-bold">✓ CONFIRMED</span>
              ) : (
                <span className="text-[9px] text-accent-yellow">FORMING</span>
              )}
            </div>
            {p.key_level && (
              <div className="flex gap-3 text-[10px] font-mono">
                <span className="text-text-secondary">Level: <span className="text-white">{p.key_level.toLocaleString()}</span></span>
                {p.target && <span className="text-text-secondary">Target: <span className="text-accent-blue">{p.target.toLocaleString()}</span></span>}
              </div>
            )}
            {p.detail && <p className="text-[10px] text-text-secondary mt-1">{p.detail}</p>}
          </div>
        ))}
      </div>

      {data?.range && (
        <p className="text-[9px] text-text-secondary mt-2">
          Scan range: ${data.range[0]?.toLocaleString()} – ${data.range[1]?.toLocaleString()} · geometric detection on real OHLC
        </p>
      )}
    </div>
  )
}