'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getWhaleWalls } from '@/lib/api'

const fmtUsd = (n: any) => {
  const v = Number(n) || 0
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`
  return `$${v.toFixed(0)}`
}

export default function WhaleWallsPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [minUsd, setMinUsd] = useState(250000)

  const load = useCallback(async () => {
    try { setData(await getWhaleWalls(symbol, minUsd)) } catch {}
    setLoading(false)
  }, [symbol, minUsd])

  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i) }, [load])

  const walls = data?.walls || []
  const maxUsd = Math.max(...walls.map((w: any) => Number(w.notional_usd) || 0), 1)
  const bids = walls.filter((w: any) => w.side === 'BID')
  const asks = walls.filter((w: any) => w.side === 'ASK')

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">🧱 Whale Walls</h3>
        <div className="flex items-center gap-2">
          {data?.bias && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              data.bias === 'BID_HEAVY' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
              : data.bias === 'ASK_HEAVY' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
              : 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/30'
            }`}>{data.bias}</span>
          )}
          <select value={minUsd} onChange={(e) => setMinUsd(Number(e.target.value))}
            className="bg-dark-700 text-white text-[10px] rounded px-1.5 py-1 border border-dark-500">
            <option value={100000}>$100K+</option>
            <option value={250000}>$250K+</option>
            <option value={500000}>$500K+</option>
            <option value={1000000}>$1M+</option>
          </select>
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Scanning orderbook walls...</p>}

      {data && (
        <>
          <div className="flex justify-between text-[10px] font-mono mb-2">
            <span className="text-accent-green">Buy walls {fmtUsd(data.buy_wall_usd)}</span>
            <span className="text-accent-purple">MID {data.mid ? `$${Number(data.mid).toLocaleString()}` : '—'}</span>
            <span className="text-accent-red">Sell walls {fmtUsd(data.sell_wall_usd)}</span>
          </div>

          {walls.length === 0 && <p className="text-text-secondary text-xs">No walls ≥ threshold — thin book.</p>}

          <div className="space-y-[3px] max-h-80 overflow-y-auto">
            {walls.map((w: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className={`w-9 font-bold ${w.side === 'BID' ? 'text-accent-green' : 'text-accent-red'}`}>{w.side}</span>
                <span className="w-16 text-right font-mono text-text-secondary">{Number(w.price).toLocaleString()}</span>
                <div className="flex-1 h-2.5 bg-dark-700 rounded overflow-hidden">
                  <div className={`h-full rounded ${w.side === 'BID' ? 'bg-accent-green/60' : 'bg-accent-red/60'}`}
                    style={{ width: `${(Number(w.notional_usd) / maxUsd) * 100}%` }} />
                </div>
                <span className="w-14 text-right font-mono text-accent-purple">{fmtUsd(w.notional_usd)}</span>
                <span className="w-14 text-right font-mono text-text-secondary">
                  {w.dist_pct != null ? `${w.dist_pct >= 0 ? '+' : ''}${w.dist_pct.toFixed(2)}%` : '—'}
                </span>
              </div>
            ))}
          </div>

          <p className="text-[9px] text-text-secondary mt-2">{data.count} walls · real L2 depth · distance from mid</p>
        </>
      )}
    </div>
  )
}