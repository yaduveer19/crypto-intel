'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getAnalyze, paperOpen } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
const TIMEFRAMES = ['15m', '1h', '4h', '1d']

const dirStyle: Record<string, { badge: string; text: string; ring: string }> = {
  LONG: { badge: 'bg-accent-green/15 text-accent-green border-accent-green/40', text: 'text-accent-green', ring: 'border-accent-green/30' },
  SHORT: { badge: 'bg-accent-red/15 text-accent-red border-accent-red/40', text: 'text-accent-red', ring: 'border-accent-red/30' },
  WAIT: { badge: 'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/40', text: 'text-accent-yellow', ring: 'border-accent-yellow/30' },
}

const stateStyle: Record<string, string> = {
  Bullish: 'bg-accent-green/15 text-accent-green',
  Bearish: 'bg-accent-red/15 text-accent-red',
  Neutral: 'bg-accent-yellow/15 text-accent-yellow',
}

const laneColors: Record<string, string> = {
  T: 'bg-accent-blue/20 text-accent-blue',
  F: 'bg-accent-purple/20 text-accent-purple',
  N: 'bg-accent-yellow/20 text-accent-yellow',
  M: 'bg-accent-green/20 text-accent-green',
}

const fmt = (p?: number | null, dp = 2) =>
  p === null || p === undefined || isNaN(p) ? '—' : `$${Number(p).toLocaleString(undefined, { maximumFractionDigits: dp })}`

export default function AnalyzePage() {
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [tf, setTf] = useState('1h')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [paperMsg, setPaperMsg] = useState('')
  const [openBusy, setOpenBusy] = useState(false)

  const fetchAnalyze = useCallback(async () => {
    try {
      const d = await getAnalyze(symbol, tf)
      setData(d)
      setErr('')
    } catch (e: any) {
      setErr('Analyze failed: ' + (e?.message || 'backend unreachable'))
    }
    setLoading(false)
  }, [symbol, tf])

  useEffect(() => {
    setLoading(true)
    fetchAnalyze()
    const i = setInterval(fetchAnalyze, 60000)
    return () => clearInterval(i)
  }, [fetchAnalyze])

  const openPaper = async () => {
    if (!v || v.direction === 'WAIT') return
    setOpenBusy(true)
    setPaperMsg('')
    try {
      const side = v.direction === 'LONG' ? 'long' : 'short'
      const r = await paperOpen(symbol, side, 500)
      if (r?.error) setPaperMsg('❌ ' + r.error)
      else if (r?.position) setPaperMsg(`✅ Paper ${side.toUpperCase()} opened: ${symbol} @ ${fmt(r.position.entry)}`)
      else setPaperMsg('❌ Unexpected response')
    } catch (e: any) {
      setPaperMsg('❌ ' + (e?.message || 'failed'))
    }
    setOpenBusy(false)
    setTimeout(() => setPaperMsg(''), 6000)
  }

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 bg-dark-600 rounded animate-pulse" />
        <div className="h-40 bg-dark-700 rounded-xl animate-pulse" />
        <div className="grid grid-cols-2 gap-4">
          {[0, 1, 2, 3].map(i => <div key={i} className="h-44 bg-dark-700 rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  const v = data?.verdict
  const lanes = Array.isArray(data?.lanes) ? data.lanes : []
  const dir = v?.direction || 'WAIT'
  const st = dirStyle[dir] || dirStyle.WAIT
  const targets: (number | null)[] = Array.isArray(v?.targets) ? v.targets : [null, null]

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Analyze</h1>
          <p className="text-text-secondary text-sm">4-lane verdict — technical · flow · narrative · macro</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-dark-700 rounded-lg border border-dark-500 p-1">
            {SYMBOLS.map(s => (
              <button key={s} onClick={() => setSymbol(s)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition ${symbol === s ? 'bg-accent-purple/25 text-white' : 'text-text-secondary hover:text-white'}`}>
                {s.replace('USDT', '')}
              </button>
            ))}
          </div>
          <div className="flex bg-dark-700 rounded-lg border border-dark-500 p-1">
            {TIMEFRAMES.map(t => (
              <button key={t} onClick={() => setTf(t)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition ${tf === t ? 'bg-accent-blue/25 text-white' : 'text-text-secondary hover:text-white'}`}>
                {t}
              </button>
            ))}
          </div>
          <button onClick={() => { setLoading(true); fetchAnalyze() }}
            className="bg-dark-700 border border-dark-500 text-text-secondary hover:text-white px-3 py-2 rounded-lg text-sm transition">
            ↻
          </button>
        </div>
      </div>

      {err && <div className="bg-accent-red/10 border border-accent-red/30 text-accent-red rounded-lg px-4 py-2 text-sm">{err}</div>}
      {paperMsg && <div className="bg-dark-700/60 border border-dark-500 text-text-secondary rounded-lg px-4 py-2 text-sm">{paperMsg}</div>}

      {/* Verdict hero */}
      {v && (
        <div className={`glass rounded-xl p-6 border ${st.ring}`}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`text-3xl font-black px-5 py-3 rounded-xl border ${st.badge}`}>{dir}</div>
              <div>
                <div className="text-text-secondary text-xs uppercase tracking-wider">Conviction</div>
                <div className={`text-2xl font-bold ${st.text}`}>{v.conviction ?? 0}%</div>
                <div className="text-text-secondary text-xs mt-1">{v.agreement} · {v.bulls}🟢 / {v.bears}🔴</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-text-secondary text-xs uppercase tracking-wider">Price</div>
              <div className="text-xl font-bold text-white font-mono">{fmt(data.price)}</div>
              <div className="text-text-secondary text-xs mt-1">ATR {fmt(data.atr)} · {data.mode || ''}</div>
            </div>
          </div>

          {/* Conviction bar */}
          <div className="mt-4 h-2 bg-dark-600 rounded-full overflow-hidden">
            <div className={`h-full transition-all ${dir === 'LONG' ? 'bg-accent-green' : dir === 'SHORT' ? 'bg-accent-red' : 'bg-accent-yellow'}`}
              style={{ width: `${Math.max(2, Math.min(100, v.conviction || 0))}%` }} />
          </div>

          {/* Levels */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
            {[
              { label: 'Entry', value: v.entry, cls: 'text-white' },
              { label: 'Stop', value: v.stop, cls: 'text-accent-red' },
              { label: 'Target 1', value: targets[0], cls: 'text-accent-green' },
              { label: 'Target 2', value: targets[1], cls: 'text-accent-blue' },
              { label: 'ATR', value: data.atr, cls: 'text-accent-purple' },
            ].map(x => (
              <div key={x.label} className="bg-dark-700/60 rounded-lg p-3 text-center">
                <div className="text-[10px] text-text-secondary uppercase tracking-wider">{x.label}</div>
                <div className={`text-sm font-mono font-semibold ${x.cls}`}>{fmt(x.value)}</div>
              </div>
            ))}
          </div>

          <p className="text-text-secondary text-sm mt-4 italic">{v.reasoning}</p>

          <div className="mt-4 flex items-center gap-3">
            <button onClick={openPaper} disabled={dir === 'WAIT' || openBusy}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${
                dir === 'SHORT' ? 'bg-accent-red/20 text-accent-red hover:bg-accent-red/30'
                : dir === 'LONG' ? 'bg-accent-green/20 text-accent-green hover:bg-accent-green/30'
                : 'bg-dark-700 text-text-secondary'}`}>
              {openBusy ? 'Opening…' : dir === 'WAIT' ? 'WAIT — no entry' : `📝 Paper trade ${dir} $500`}
            </button>
            <span className="text-[11px] text-text-secondary">auto-refresh 60s · updated {data?.updated ? new Date(data.updated * 1000).toLocaleTimeString() : '—'}</span>
          </div>
        </div>
      )}

      {/* 4 lanes */}
      <div className="grid md:grid-cols-2 gap-4">
        {lanes.map((l: any, i: number) => (
          <div key={l.key || i} className="glass rounded-xl p-5 border border-dark-500">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-black ${laneColors[l.letter] || 'bg-dark-600 text-white'}`}>
                  {l.letter || '?'}
                </div>
                <div>
                  <div className="text-white font-semibold">{l.label || l.key}</div>
                  <div className="text-text-secondary text-xs">{l.symbol}</div>
                </div>
              </div>
              <span className={`text-xs px-2 py-1 rounded font-medium ${stateStyle[l.state] || 'bg-dark-600 text-text-secondary'}`}>
                {l.state || '—'}
              </span>
            </div>

            {/* score bar: -1..1 */}
            <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden mb-3">
              <div className={`h-full ${l.state === 'Bullish' ? 'bg-accent-green' : l.state === 'Bearish' ? 'bg-accent-red' : 'bg-accent-yellow'}`}
                style={{ width: `${Math.max(4, Math.min(100, ((Number(l.score) || 0) + 1) / 2 * 100))}%` }} />
            </div>

            <ul className="space-y-1.5">
              {(l.signals || []).map((s: string, j: number) => (
                <li key={j} className="text-sm text-text-secondary flex items-start gap-2">
                  <span className="text-text-secondary/50 mt-0.5">›</span>{s}
                </li>
              ))}
              {(l.signals || []).length === 0 && <li className="text-sm text-text-secondary">No signals</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
