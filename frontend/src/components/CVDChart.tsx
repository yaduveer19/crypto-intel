'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { ResponsiveContainer, ComposedChart, Line, Bar, Cell, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts'
import { getCVD } from '@/lib/api'

export default function CVDChart({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getCVD(symbol)) } catch {}
    setLoading(false)
  }, [symbol])

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i) }, [load])

  const series = data?.cvd?.series || []
  const delta = data?.cvd?.delta_profile || []
  const signal = data?.cvd?.signal

  const num = (n: any) => { const v = Number(n); return isNaN(v) ? 0 : v }

  const chartData = series.slice(-100).map((p: any) => ({
    time: new Date(num(p.time) * 1000).toLocaleTimeString(),
    cvd: Number(num(p.cvd).toFixed(2)),
  }))

  const deltaData = delta.map((d: any) => ({
    name: `B${d.bin}`,
    delta: Number(num(d.net_delta).toFixed(2)),
    vol: Number(num(d.volume).toFixed(2)),
  }))

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">📈 CVD — Cumulative Volume Delta</h3>
        {signal && (
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
            signal.divergence === 'bullish' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
            : signal.divergence === 'bearish' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
            : 'text-text-secondary bg-dark-700 border-dark-600'
          }`}>
            {signal.divergence === 'none' ? 'ALIGNED' : signal.divergence.toUpperCase()}
          </span>
        )}
      </div>

      {loading && <p className="text-text-secondary text-xs">Loading CVD...</p>}

      {!loading && chartData.length > 0 && (
        <>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 9 }} minTickGap={40} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 9 }} width={60} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} />
                <ReferenceLine y={0} stroke="#374151" />
                <Line type="monotone" dataKey="cvd" stroke="#8b5cf6" strokeWidth={1.8} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {deltaData.length > 0 && (
            <>
              <div className="text-[10px] text-text-secondary mt-3 mb-1">Net delta per time bucket</div>
              <div className="h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={deltaData} margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 8 }} interval={3} />
                    <YAxis tick={{ fill: '#6b7280', fontSize: 8 }} width={45} />
                    <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} />
                    <ReferenceLine y={0} stroke="#374151" />
                    <Bar dataKey="delta" isAnimationActive={false}>
                      {deltaData.map((d: any, i: number) => (
                        <Cell key={i} fill={d.delta >= 0 ? '#22c55e' : '#ef4444'} />
                      ))}
                    </Bar>
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {signal && (
            <p className="text-[11px] text-text-secondary mt-2">
              <span className={signal.divergence === 'bullish' ? 'text-accent-green' : signal.divergence === 'bearish' ? 'text-accent-red' : 'text-text-secondary'}>
                {signal.message}
              </span>
              {signal.strength > 0 && <span className="ml-2">strength {(num(signal.strength) * 100).toFixed(0)}%</span>}
            </p>
          )}
        </>
      )}
    </div>
  )
}
