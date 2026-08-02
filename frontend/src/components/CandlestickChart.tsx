'use client'
import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { getKlines, getVolumeProfile } from '@/lib/api'

const W = 780
const H = 340
const PAD = { top: 10, right: 12, bottom: 24, left: 62 }

export default function CandlestickChart({ symbol, exchange }: { symbol: string; exchange?: string }) {
  const [mounted, setMounted] = useState(false)
  const [klines, setKlines] = useState<any[]>([])
  const [vwapLine, setVwapLine] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { setMounted(true) }, [])
  const [hover, setHover] = useState<any>(null)

  const load = useCallback(async () => {
    try {
      const k = await getKlines(symbol, exchange, '5m', 120)
      setKlines(k.klines || [])
    } catch {}
    try {
      const vp = await getVolumeProfile(symbol)
      setVwapLine(vp.vwap_line || [])
    } catch {}
    setLoading(false)
  }, [symbol, exchange])

  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i) }, [load])

  const view = useMemo(() => {
    const bars = klines.slice(-80)
    if (!bars.length) return null
    let min = Infinity, max = -Infinity
    for (const k of bars) {
      if (k == null || k.high == null || k.low == null) continue
      min = Math.min(min, k.low); max = Math.max(max, k.high)
    }
    if (!isFinite(min) || !isFinite(max)) return null
    const range = max - min || 1
    const yMin = min - range * 0.06
    const yMax = max + range * 0.06
    const plotW = W - PAD.left - PAD.right
    const plotH = H - PAD.top - PAD.bottom
    const step = plotW / bars.length
    const y = (v: number) => PAD.top + (yMax - v) / (yMax - yMin) * plotH
    const candles = bars.map((k: any, i: number) => {
      const up = k.close >= k.open
      const x = PAD.left + i * step + step / 2
      return {
        x, up,
        oy: y(k.open), cy: y(k.close), hy: y(k.high), ly: y(k.low),
        bodyTop: y(Math.max(k.open, k.close)),
        bodyH: Math.max(Math.abs(y(k.open) - y(k.close)), 1),
        candleW: Math.max(step * 0.62, 2),
        open: k.open, close: k.close, high: k.high, low: k.low,
        time: new Date(k.time * 1000).toLocaleTimeString(),
      }
    })
    const vwap = vwapLine.map((v: any) => ({ x: PAD.left + 0, y: y(v.vwap) }))
    const gridLines = []
    const ticks = 5
    for (let i = 0; i <= ticks; i++) {
      const val = yMax - (yMax - yMin) * i / ticks
      gridLines.push({ y: y(val), label: val > 1000 ? val.toLocaleString(undefined, { maximumFractionDigits: 0 }) : val.toFixed(2) })
    }
    return { candles, vwap, gridLines, yMin, yMax, step }
  }, [klines, vwapLine])

  if (!mounted || loading) return <div className="glass rounded-xl p-4 border border-dark-500"><p className="text-text-secondary text-xs">Loading chart...</p></div>

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">🕯️ Candlestick — {symbol.replace('USDT', '')}/USDT</h3>
        <div className="text-[10px] text-text-secondary">{exchange || 'binance'} · 5m · VWAP overlay</div>
      </div>

      {!view ? (
        <p className="text-text-secondary text-xs">No data</p>
      ) : (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full"
            onMouseLeave={() => setHover(null)}>
            {view.gridLines.map((g, i) => (
              <g key={i}>
                <line x1={PAD.left} x2={W - PAD.right} y1={g.y} y2={g.y} stroke="#1f2937" strokeDasharray="3 3" />
                <text x={PAD.left - 6} y={g.y + 3} textAnchor="end" fill="#6b7280" fontSize={9}>{g.label}</text>
              </g>
            ))}

            {view.candles.map((c, i) => (
              <g key={i}>
                <line x1={c.x} x2={c.x} y1={c.hy} y2={c.ly} stroke={c.up ? '#22c55e' : '#ef4444'} strokeWidth={1} />
                <rect x={c.x - c.candleW / 2} y={c.bodyTop} width={c.candleW} height={c.bodyH}
                  fill={c.up ? '#22c55e' : '#ef4444'} rx={1} />
                <rect x={c.x - c.candleW / 2} y={c.bodyTop} width={c.candleW} height={c.bodyH}
                  fill="transparent" onMouseEnter={() => setHover(c)} />
              </g>
            ))}

            {view.vwap.length > 1 && (
              <polyline
                points={view.candles.map((c, i) => `${c.x},${view.vwap[i]?.y ?? c.cy}`).join(' ')}
                fill="none" stroke="#3b82f6" strokeWidth={1.5} />
            )}

            {hover && (
              <g>
                <line x1={hover.x} x2={hover.x} y1={PAD.top} y2={H - PAD.bottom} stroke="#374151" strokeDasharray="2 2" />
                <rect x={hover.x + 6} y={PAD.top} width={120} height={66} rx={6} fill="#111827" stroke="#374151" />
                <text x={hover.x + 12} y={PAD.top + 14} fill="#e5e7eb" fontSize={9}>{hover.time}</text>
                <text x={hover.x + 12} y={PAD.top + 26} fill="#9ca3af" fontSize={9}>O {hover.open}</text>
                <text x={hover.x + 12} y={PAD.top + 38} fill={hover.up ? '#22c55e' : '#ef4444'} fontSize={9}>C {hover.close}</text>
                <text x={hover.x + 12} y={PAD.top + 50} fill="#9ca3af" fontSize={9}>H {hover.high}</text>
                <text x={hover.x + 12} y={PAD.top + 62} fill="#9ca3af" fontSize={9}>L {hover.low}</text>
              </g>
            )}
          </svg>

          <div className="flex gap-4 text-[10px] text-text-secondary mt-2">
            <span><span className="inline-block w-2 h-2 rounded-sm bg-accent-green mr-1" />Bullish</span>
            <span><span className="inline-block w-2 h-2 rounded-sm bg-accent-red mr-1" />Bearish</span>
            <span><span className="inline-block w-3 h-0.5 bg-accent-blue mr-1 align-middle" />VWAP</span>
          </div>
        </>
      )}
    </div>
  )
}
