'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getOrderbook } from '@/lib/api'

export default function OrderbookPanel({ symbol, exchange }: { symbol: string; exchange?: string }) {
  const [mounted, setMounted] = useState(false)
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { setMounted(true) }, [])

  const load = useCallback(async () => {
    try { setData(await getOrderbook(symbol, exchange)) } catch {}
    setLoading(false)
  }, [symbol, exchange])

  useEffect(() => { load(); const i = setInterval(load, 4000); return () => clearInterval(i) }, [load])

  const bids: any[] = data?.bids || []
  const asks: any[] = data?.asks || []
  const maxDepth = Math.max(...bids.map((b) => b[1]), ...asks.map((a) => a[1]), 1e-9)
  const spread = bids[0] && asks[0] ? asks[0][0] - bids[0][0] : 0
  const mid = bids[0] && asks[0] ? (bids[0][0] + asks[0][0]) / 2 : 0
  const fmt = (n: any) => {
    const v = Number(n)
    if (n == null || isNaN(v)) return 'â€”'
    return v > 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : v.toFixed(2)
  }
  const sizeFmt = (n: any) => {
    const v = Number(n)
    if (n == null || isNaN(v)) return 'â€”'
    return v >= 1000 ? `${(v/1000).toFixed(1)}K` : v.toFixed(2)
  }

  if (!mounted || loading) {
    return <div className="glass rounded-xl p-4 border border-dark-500"><h3 className="text-sm font-semibold text-white mb-3">ðŸ“— Orderbook</h3><p className="text-text-secondary text-xs">Loading...</p></div>
  }

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">ðŸ“— Orderbook</h3>
        <div className="text-[10px] text-text-secondary">
          {data?.exchange || '...'} Â· {data?.mode || ''}{mid > 0 && <span className="ml-2">spread {fmt(spread)}</span>}
        </div>
      </div>
      {asks.length > 0 && <>
        <div className="space-y-[2px] mb-2">
          {[...asks].reverse().slice(-12).map((a: number[], i: number) => (
            <div key={`a${i}`} className="relative flex items-center justify-between text-xs py-[3px] px-2 rounded">
              <div className="absolute inset-y-0 right-0 bg-accent-red/15 rounded" style={{ width: `${(a[1] / maxDepth) * 100}%` }} />
              <span className="relative text-accent-red font-mono">{fmt(a[0])}</span>
              <span className="relative text-text-secondary font-mono">{sizeFmt(a[1])}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between text-[11px] font-semibold border-y border-dark-600 py-1.5 mb-2">
          <span className="text-white font-mono">{fmt(mid)}</span>
          <span className="text-text-secondary">spread {fmt(spread)} ({asks.length + bids.length} lvls)</span>
        </div>
        <div className="space-y-[2px]">
          {bids.slice(0, 12).map((b: number[], i: number) => (
            <div key={`b${i}`} className="relative flex items-center justify-between text-xs py-[3px] px-2 rounded">
              <div className="absolute inset-y-0 left-0 bg-accent-green/15 rounded" style={{ width: `${(b[1] / maxDepth) * 100}%` }} />
              <span className="relative text-accent-green font-mono">{fmt(b[0])}</span>
              <span className="relative text-text-secondary font-mono">{sizeFmt(b[1])}</span>
            </div>
          ))}
        </div>
      </>}
    </div>
  )
}
