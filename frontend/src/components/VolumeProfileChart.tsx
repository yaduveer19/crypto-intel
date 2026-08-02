'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts'
import { getVolumeProfile } from '@/lib/api'

export default function VolumeProfileChart({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getVolumeProfile(symbol)) } catch {}
    setLoading(false)
  }, [symbol])

  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i) }, [load])

  const levels = data?.levels || []
  const poc = data?.poc
  const va = data?.value_area
  const vwap = data?.vwap
  const vwapLine = data?.vwap_line || []

  const maxVol = Math.max(...levels.map((l: any) => Number(l.volume) || 0), 1e-9)

  const fmt = (n: any) => {
    const v = Number(n)
    if (n == null || isNaN(v)) return '—'
    return v > 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toFixed(2)
  }

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">📊 Volume Profile & VWAP</h3>
        <div className="text-[10px] text-text-secondary">
          POC <span className="text-accent-yellow font-mono">{poc != null ? fmt(poc) : '—'}</span>
          {vwap != null && <span className="ml-2">VWAP <span className="text-accent-blue font-mono">{fmt(vwap)}</span></span>}
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Loading volume profile...</p>}

      {!loading && levels.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {/* Horizontal profile */}
          <div>
            {va?.high != null && (
              <div className="text-[10px] text-text-secondary mb-1">
                Value Area: {fmt(va.low)} – {fmt(va.high)}
              </div>
            )}
            <div className="space-y-[2px] max-h-64 overflow-y-auto pr-1">
              {levels.slice().reverse().map((l: any, i: number) => {
                const vol = Number(l.volume) || 0
                const buyPct = Number(l.buy_pct)
                const inVA = va?.high != null && l.price >= va.low && l.price <= va.high
                const isPOC = l.price === poc
                return (
                  <div key={i} className={`relative flex items-center gap-2 text-[10px] py-[1px] px-1 rounded ${isPOC ? 'bg-accent-yellow/10' : ''}`}>
                    <span className="w-16 text-text-secondary font-mono text-right">{fmt(l.price)}</span>
                    <div className="flex-1 h-2.5 bg-dark-700 rounded overflow-hidden">
                      <div
                        className={`h-full rounded ${inVA ? (buyPct >= 50 ? 'bg-accent-green/60' : 'bg-accent-red/60') : 'bg-dark-500'}`}
                        style={{ width: `${(vol / maxVol) * 100}%` }}
                      />
                    </div>
                    <span className="w-10 text-text-secondary font-mono">{vol >= 1000 ? `${(vol/1000).toFixed(1)}K` : vol.toFixed(1)}</span>
                    <span className={`w-8 text-[9px] ${buyPct >= 50 ? 'text-accent-green' : 'text-accent-red'}`}>{buyPct.toFixed(0)}%B</span>
                    {isPOC && <span className="text-[9px] text-accent-yellow font-bold">POC</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* VWAP line */}
          <div>
            <div className="text-[10px] text-text-secondary mb-1">Session VWAP</div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={vwapLine} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 8 }} tickFormatter={(t) => new Date(t * 1000).toLocaleTimeString()} minTickGap={30} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 8 }} width={50} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
                    labelFormatter={(t) => new Date(t * 1000).toLocaleTimeString()} />
                  <Line type="monotone" dataKey="vwap" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  {poc && <ReferenceLine y={poc} stroke="#f59e0b" strokeDasharray="4 4" />}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
