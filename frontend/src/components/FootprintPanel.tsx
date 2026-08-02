'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getFootprint } from '@/lib/api'

export default function FootprintPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getFootprint(symbol)) } catch {}
    setLoading(false)
  }, [symbol])

  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i) }, [load])

  const footprint: any[] = (data?.footprint as any[]) || []
  const tpo: any[] = (data?.tpo as any[]) || []

  const maxTotal = Math.max(...footprint.map((f: any) => f.total), 1e-9)
  const timeBins: number[] = [...new Set(footprint.map((f: any) => f.time_bin))]
  const maxTpo = Math.max(...tpo.map((t: any) => t.tpo_count), 1)

  const fmt = (n: any) => {
    const v = Number(n)
    if (n == null || isNaN(v)) return '—'
    return v >= 1000 ? `${(v/1000).toFixed(1)}K` : v.toFixed(2)
  }

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <h3 className="text-sm font-semibold text-white mb-3">🔍 Footprint / TPO</h3>

      {loading && <p className="text-text-secondary text-xs">Loading footprint...</p>}

      {!loading && footprint.length > 0 && (
        <>
          <div className="text-[10px] text-text-secondary mb-2">Order flow by price × time (green = buy, red = sell, intensity = volume)</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr>
                  <th className="text-text-secondary text-left py-1 px-1 font-normal">Price</th>
                  {timeBins.slice(0, 12).map((tb) => <th key={tb} className="text-text-secondary font-normal py-1 px-1">T{tb}</th>)}
                </tr>
              </thead>
              <tbody>
                {[...footprint].sort((a, b) => b.price - a.price).filter((f: any) => f.time_bin < Math.min(timeBins.length, 12)).slice(0, 14).map((f: any, i: number) => (
                  <tr key={i} className="border-t border-dark-700">
                    <td className={`py-0.5 px-1 font-mono text-text-secondary ${f.poc ? 'text-accent-yellow font-bold' : ''}`}>{fmt(f.price)}</td>
                    {timeBins.slice(0, 12).map((tb) => {
                      const cell = footprint.find((x: any) => x.price === f.price && x.time_bin === tb)
                      if (!cell) return <td key={tb} className="py-0.5 px-1 text-dark-500">·</td>
                      const intensity = cell.total / maxTotal
                      return (
                        <td key={tb} className="py-0.5 px-1 text-center font-mono rounded"
                          style={{ backgroundColor: cell.delta >= 0 ? `rgba(34,197,94,${0.08 + intensity * 0.35})` : `rgba(239,68,68,${0.08 + intensity * 0.35})`, color: cell.delta >= 0 ? '#4ade80' : '#f87171' }}>
                          {fmt(cell.total)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 border-t border-dark-600 pt-3">
            <div className="text-[10px] text-text-secondary mb-1">Market Profile (TPO) — value zones</div>
            <div className="space-y-[2px] max-h-32 overflow-y-auto">
              {[...tpo].sort((a, b) => b.tpo_count - a.tpo_count).slice(0, 12).map((t: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className="w-16 text-right font-mono text-text-secondary">{fmt(t.price)}</span>
                  <div className="flex-1 h-2 bg-dark-700 rounded overflow-hidden">
                    <div className="h-full bg-accent-purple/70 rounded" style={{ width: `${(t.tpo_count / maxTpo) * 100}%` }} />
                  </div>
                  <span className="w-8 text-text-secondary">{t.tpo_count}</span>
                  <span className={`w-10 ${t.buy_pct >= 50 ? 'text-accent-green' : 'text-accent-red'}`}>{t.buy_pct}%B</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
