'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getMacro } from '@/lib/api'

const corrColor = (c: any) => {
  if (c === null || c === undefined || isNaN(Number(c))) return 'bg-dark-600'
  const v = Number(c)
  if (v >= 0.6) return 'bg-accent-green'
  if (v >= 0.3) return 'bg-accent-green/50'
  if (v <= -0.6) return 'bg-accent-red'
  if (v <= -0.3) return 'bg-accent-red/50'
  return 'bg-dark-500'
}

export default function MacroPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getMacro()) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load(); const i = setInterval(load, 300000); return () => clearInterval(i) }, [load])

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">📊 Macro Correlations</h3>
        <div className="flex items-center gap-2">
          {data?.macro_risk && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              data.macro_risk === 'RISK-ON' ? 'text-accent-green bg-accent-green/10 border-accent-green/30' : 'text-accent-red bg-accent-red/10 border-accent-red/30'
            }`}>{data.macro_risk}</span>
          )}
          <span className="text-[10px] text-text-secondary">vs BTC · 3mo daily</span>
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Computing correlations...</p>}

      {data && (
        <div className="space-y-1.5">
          {data.rows?.map((r: any, i: number) => {
            const c = r.correlation
            return (
              <div key={i} className="flex items-center gap-3 text-[11px] bg-dark-700/40 rounded-lg px-3 py-2">
                <div className="w-24">
                  <div className="font-semibold text-white">{r.asset}</div>
                  <div className="text-[9px] text-text-secondary">{r.relationship}</div>
                </div>
                <div className="flex-1 flex items-center gap-2">
                  <div className="flex-1 h-2 bg-dark-600 rounded overflow-hidden relative">
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-dark-400" />
                    {c != null && (
                      <div className={`absolute top-0 bottom-0 ${corrColor(c)}`}
                        style={Number(c) >= 0
                          ? { left: '50%', width: `${Math.abs(Number(c)) * 50}%` }
                          : { right: '50%', width: `${Math.abs(Number(c)) * 50}%` }} />
                    )}
                  </div>
                  <span className={`w-12 text-right font-mono font-semibold ${c != null && Math.abs(Number(c)) >= 0.6 ? 'text-white' : 'text-text-secondary'}`}>
                    {c != null ? (Number(c) >= 0 ? '+' : '') + Number(c).toFixed(2) : '—'}
                  </span>
                </div>
                <div className="w-20 text-right">
                  <div className="font-mono text-text-secondary">{r.price != null ? Number(r.price).toLocaleString(undefined, { maximumFractionDigits: r.price < 10 ? 2 : 0 }) : '—'}</div>
                  <div className={`text-[9px] font-semibold ${(r.change_pct || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {r.change_pct != null ? `${r.change_pct >= 0 ? '+' : ''}${r.change_pct}%` : '—'}
                  </div>
                </div>
                <span className={`w-14 text-right text-[9px] font-bold ${
                  r.strength === 'STRONG' ? 'text-accent-blue' : r.strength === 'MODERATE' ? 'text-accent-yellow' : 'text-text-secondary'
                }`}>{r.strength}</span>
              </div>
            )
          })}
          <p className="text-[9px] text-text-secondary mt-1">Real prices (Binance + Yahoo) · Pearson on daily returns · BTC ${data.btc_last?.toLocaleString()}</p>
        </div>
      )}
    </div>
  )
}