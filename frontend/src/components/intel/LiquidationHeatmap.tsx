'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getLiquidations } from '@/lib/api'

const fmtUsd = (n: number) => {
  const v = Number(n) || 0
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`
  return `$${v.toFixed(0)}`
}

export default function LiquidationHeatmap({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getLiquidations(symbol)) } catch {}
    setLoading(false)
  }, [symbol])

  useEffect(() => { load(); const i = setInterval(load, 8000); return () => clearInterval(i) }, [load])

  const bins = data?.bins || []
  const above = bins.filter((b: any) => b.offset_pct > 0).sort((a: any, b: any) => a.offset_pct - b.offset_pct)
  const below = bins.filter((b: any) => b.offset_pct < 0).sort((a: any, b: any) => b.offset_pct - a.offset_pct)
  const maxVol = Math.max(...bins.map((b: any) => Number(b.volume) || 0), 1e-9)

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">🧲 Liquidation Heatmap</h3>
        <div className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${data?.live ? 'bg-accent-green animate-pulse' : 'bg-accent-yellow'}`} />
          <span className="text-[10px] text-text-secondary">{data?.live ? 'LIVE forceOrder feed' : 'estimated'}</span>
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Loading liquidations...</p>}

      {data && (
        <>
          {/* Magnet score */}
          <div className="flex items-center justify-between bg-dark-700/50 rounded-lg px-3 py-2 mb-3">
            <div>
              <div className="text-[10px] text-text-secondary">Magnetic Pull Score</div>
              <div className="text-lg font-bold text-accent-purple font-mono">{data.magnet_score ?? '—'}</div>
            </div>
            <div className="text-right text-[10px]">
              <div className="text-accent-red">Shorts liq: {fmtUsd(data.total_short_usd)}</div>
              <div className="text-accent-green">Longs liq: {fmtUsd(data.total_long_usd)}</div>
            </div>
          </div>

          {/* Bins above mid (short liquidations) */}
          <div className="space-y-[3px] mb-2">
            {above.slice().reverse().map((b: any, i: number) => (
              <div key={`a${i}`} className="flex items-center gap-2 text-[10px]">
                <span className="w-14 text-right font-mono text-text-secondary">{b.price.toLocaleString()}</span>
                <span className="w-10 text-[9px] text-accent-red">+{b.offset_pct}%</span>
                <div className="flex-1 h-2.5 bg-dark-700 rounded overflow-hidden">
                  <div className="h-full bg-gradient-to-l from-accent-red/70 to-accent-red/20 rounded"
                    style={{ width: `${((Number(b.volume) || 0) / maxVol) * 100}%` }} />
                </div>
                <span className="w-12 text-right font-mono text-text-secondary">{(Number(b.volume) || 0).toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Mid */}
          <div className="flex items-center justify-between text-[11px] font-semibold border-y border-accent-purple/30 py-1.5 my-2">
            <span className="text-white font-mono">MID ${Number(data.mid).toLocaleString()}</span>
            <span className="text-accent-purple">{data.events} events 24h</span>
          </div>

          {/* Bins below mid (long liquidations) */}
          <div className="space-y-[3px] mb-3">
            {below.map((b: any, i: number) => (
              <div key={`b${i}`} className="flex items-center gap-2 text-[10px]">
                <span className="w-14 text-right font-mono text-text-secondary">{b.price.toLocaleString()}</span>
                <span className="w-10 text-[9px] text-accent-green">{b.offset_pct}%</span>
                <div className="flex-1 h-2.5 bg-dark-700 rounded overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-accent-green/70 to-accent-green/20 rounded"
                    style={{ width: `${((Number(b.volume) || 0) / maxVol) * 100}%` }} />
                </div>
                <span className="w-12 text-right font-mono text-text-secondary">{(Number(b.volume) || 0).toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Largest liquidations tape */}
          {data.largest?.length > 0 && (
            <div>
              <div className="text-[10px] text-text-secondary mb-1">Largest prints (live tape)</div>
              <div className="space-y-[2px] max-h-32 overflow-y-auto">
                {data.largest.map((l: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-[10px] py-0.5 px-1 rounded bg-dark-700/40">
                    <span className={`font-bold ${l.side === 'LONG' ? 'text-accent-red' : 'text-accent-green'}`}>{l.side}</span>
                    <span className="font-mono text-text-secondary">${l.price.toLocaleString()}</span>
                    <span className="font-mono text-text-secondary">{l.qty}</span>
                    <span className="font-mono text-accent-purple">{fmtUsd(l.notional_usd)}</span>
                    <span className="text-text-secondary">{l.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.note && <p className="text-[9px] text-text-secondary mt-2">{data.note}</p>}
        </>
      )}
    </div>
  )
}