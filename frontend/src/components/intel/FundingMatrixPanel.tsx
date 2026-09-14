'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getFundingMatrix } from '@/lib/api'

const EX_ORDER = ['binance', 'bybit', 'okx', 'hyperliquid']
const COIN_ORDER = ['BTC', 'ETH', 'SOL']

const rateColor = (r: number) =>
  r > 0.02 ? 'text-accent-green' : r < -0.02 ? 'text-accent-red' : 'text-text-secondary'

export default function FundingMatrixPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getFundingMatrix()) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i) }, [load])

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">⚡ Funding Matrix</h3>
        <div className="text-[10px] text-text-secondary">8h funding · cross-exchange</div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Loading funding matrix...</p>}

      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-text-secondary">
                <th className="text-left py-1.5 font-normal">Coin</th>
                {EX_ORDER.map(ex => <th key={ex} className="text-right py-1.5 font-normal capitalize">{ex}</th>)}
                <th className="text-right py-1.5 font-normal">Avg</th>
                <th className="text-right py-1.5 font-normal">Spread</th>
              </tr>
            </thead>
            <tbody>
              {COIN_ORDER.map(coin => {
                const m = data[coin]
                if (!m) return null
                return (
                  <tr key={coin} className="border-t border-dark-700">
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{coin}</span>
                        {m.arb_opportunity && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded bg-accent-purple/20 text-accent-purple font-bold">ARB</span>
                        )}
                      </div>
                      <div className="text-[9px] text-text-secondary">{m.bias} · {m.real_sources}/{m.total_sources} real</div>
                    </td>
                    {EX_ORDER.map(ex => {
                      const r = m.rates[ex]
                      if (!r) return <td key={ex} className="text-right text-dark-500">—</td>
                      return (
                        <td key={ex} className="text-right font-mono">
                          <span className={rateColor(r.rate)}>{r.rate >= 0 ? '+' : ''}{r.rate.toFixed(4)}%</span>
                          {!r.real && <span className="text-[8px] text-accent-yellow ml-0.5" title="estimated">~</span>}
                        </td>
                      )
                    })}
                    <td className={`text-right font-mono font-semibold ${rateColor(m.avg)}`}>{m.avg >= 0 ? '+' : ''}{m.avg.toFixed(4)}%</td>
                    <td className="text-right font-mono text-accent-purple">{m.spread.toFixed(4)}%</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="text-[9px] text-text-secondary mt-2">~ = estimated (geo-blocked exchange). Binance/Bybit real-time. Spread {'>'} 0.02% = funding arbitrage signal.</p>
        </div>
      )}
    </div>
  )
}