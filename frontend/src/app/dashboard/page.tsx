'use client'
import React, { useEffect, useState, useCallback, useRef } from 'react'
import VerdictCard from '@/components/VerdictCard'
import GlobeView from '@/components/GlobeView'
import LaneBreakdown from '@/components/LaneBreakdown'
import CopilotChat from '@/components/CopilotChat'
import SimulatorPanel from '@/components/SimulatorPanel'
import MarketScanner from '@/components/MarketScanner'
import LiveModeBadge from '@/components/LiveModeBadge'
import { createMarketWebSocket, getVerdict, getLanes, getSignalHistory, getBrief, getMarketSessions } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type MarketInfo = {
  symbol: string
  price?: number
  change_24h_pct?: number
  funding?: number
  cvd?: number
  vwap?: number
  best_bid?: number[]
  best_ask?: number[]
  delta_profile?: any[]
  mode?: string
}

const fmtPrice = (p?: number) => {
  if (!p || isNaN(p)) return '---'
  return p > 1000 ? `$${p.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : `$${p.toFixed(2)}`
}

const boldify = (t: string) =>
  t.split(/\*\*(.+?)\*\*/g).map((part, i) => i % 2 === 1
    ? <strong key={i} className="text-white font-semibold">{part}</strong>
    : <span key={i}>{part}</span>)

const BriefBody = ({ text }: { text: string }) => (
  <>
    {text.split('\n').filter(l => l.trim()).map((line, i) => {
      const l = line.trim()
      if (l.startsWith('# ')) return <h4 key={i} className="text-white font-semibold text-sm mt-2">{boldify(l.slice(2))}</h4>
      if (l.startsWith('## ')) return <h5 key={i} className="text-accent-blue font-semibold text-xs uppercase tracking-wider mt-2">{boldify(l.slice(3))}</h5>
      if (/^[-*•]\s/.test(l)) return <div key={i} className="text-text-secondary text-xs flex gap-2"><span className="text-accent-purple">•</span><span>{boldify(l.replace(/^[-*•]\s/, ''))}</span></div>
      return <p key={i} className="text-text-secondary text-xs leading-relaxed">{boldify(l)}</p>
    })}
  </>
)

export default function DashboardPage() {
  const [markets, setMarkets] = useState<Record<string, MarketInfo>>({})
  const [verdicts, setVerdicts] = useState<Record<string, any>>({})
  const [lanes, setLanes] = useState<any[]>([])
  const [activeSymbol, setActiveSymbol] = useState('BTCUSDT')
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState<any[]>([])
  const [wsLive, setWsLive] = useState(false)
  const [brief, setBrief] = useState<{ brief?: string; source?: string } | null>(null)
  const [sessions, setSessions] = useState<any>(null)
  const lastUpdate = useRef<Record<string, number>>({})

  const fetchData = useCallback(async () => {
    try {
      const [v, l, h] = await Promise.all([
        getVerdict(activeSymbol).catch(() => ({})),
        getLanes(activeSymbol).catch(() => []),
        getSignalHistory(activeSymbol, 20).catch(() => []),
      ])
      setVerdicts(prev => ({ ...prev, [activeSymbol]: v }))
      setLanes(Array.isArray(l) ? l : [])
      setHistory(Array.isArray(h) ? h : [])
    } catch {}
    setLoading(false)
  }, [activeSymbol])

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 30000); return () => clearInterval(i) }, [fetchData])

  // Daily brief (LLM, slow) + trading sessions (fast)
  useEffect(() => {
    let alive = true
    const loadBrief = () => getBrief().then(b => { if (alive) setBrief(b || {}) }).catch(() => {})
    const loadSessions = () => getMarketSessions().then(s => { if (alive && s && !s.error) setSessions(s) }).catch(() => {})
    loadBrief(); loadSessions()
    const bi = setInterval(loadBrief, 30 * 60 * 1000)
    const si = setInterval(loadSessions, 5 * 60 * 1000)
    return () => { alive = false; clearInterval(bi); clearInterval(si) }
  }, [])

  // Live market stream: price + 24h change + funding + CVD + VWAP, har 2s
  useEffect(() => {
    const ws = createMarketWebSocket((data) => {
      if (data.type === 'subscribed') setWsLive(true)
      if (data.type === 'market' && Array.isArray(data.data)) {
        const next: Record<string, MarketInfo> = {}
        data.data.forEach((m: MarketInfo) => {
          if (!m || !m.symbol) return
          next[m.symbol] = m
          lastUpdate.current[m.symbol] = Date.now()
        })
        setMarkets(prev => ({ ...prev, ...next }))
      }
    })
    return () => ws.close()
  }, [])

  // Fallback: agar WS se data na aaye, REST polling
  useEffect(() => {
    const poll = setInterval(async () => {
      if (Object.keys(lastUpdate.current).length === SYMBOLS.length) return
      for (const sym of SYMBOLS) {
        if (Date.now() - (lastUpdate.current[sym] || 0) > 60000) {
          try {
            const r = await fetch(`${API}/api/price/${sym}`).then(res => res.ok ? res.json() : null)
            if (r?.price) setMarkets(prev => ({ ...prev, [sym]: { symbol: sym, price: r.price } }))
          } catch {}
        }
      }
    }, 15000)
    return () => clearInterval(poll)
  }, [])

  const currentVerdict = verdicts[activeSymbol]
  const currentPrice = markets[activeSymbol]?.price

  const changeColor = (v?: number) => !v || isNaN(v) ? 'text-text-secondary' : v >= 0 ? 'text-accent-green' : 'text-accent-red'
  const changeArrow = (v?: number) => !v || isNaN(v) ? '' : v >= 0 ? '▲' : '▼'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-xs text-text-secondary mt-0.5">Live market intelligence — tick-level data, streaming every 2s</p>
        </div>
        <div className="flex items-center gap-3">
          <LiveModeBadge live={wsLive} />
          <div className="flex gap-2">
            {SYMBOLS.map(sym => (
              <button key={sym} onClick={() => setActiveSymbol(sym)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  activeSymbol === sym ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30' : 'text-text-secondary hover:text-white border border-transparent'
                }`}>
                {sym.replace('USDT', '')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Row — price, 24h change, funding, CVD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {SYMBOLS.map(sym => {
          const m = markets[sym]
          const chg = m?.change_24h_pct
          return (
            <div key={sym} className="glass rounded-xl p-4 border border-dark-500 hover:border-accent-blue/40 transition">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs text-text-secondary font-medium">{sym.replace('USDT', '')}/USDT <span className="text-[10px] uppercase ml-1 px-1.5 py-0.5 rounded bg-dark-600/60 text-accent-blue">{m?.mode || 'live'}</span></div>
                  <div className="text-2xl font-bold text-white font-mono mt-1">{fmtPrice(m?.price)}</div>
                  <div className={`text-xs font-semibold mt-1 ${changeColor(chg)}`}>{changeArrow(chg)} {chg !== undefined && !isNaN(chg) ? `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}% 24h` : '— 24h'}</div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold ${
                    verdicts[sym]?.bias === 'BULL' ? 'text-accent-green' : verdicts[sym]?.bias === 'BEAR' ? 'text-accent-red' : 'text-accent-yellow'
                  }`}>
                    {verdicts[sym]?.bias || '—'}
                    {verdicts[sym]?.tier && <div className="text-[10px] text-text-secondary font-normal">{verdicts[sym].tier}</div>}
                  </div>
                </div>
              </div>
              <div className="flex gap-4 mt-3 pt-3 border-t border-dark-600 text-xs">
                <div>
                  <div className="text-text-secondary">Funding</div>
                  <div className={`font-mono font-semibold ${m?.funding && m.funding > 0 ? 'text-accent-green' : m?.funding && m.funding < 0 ? 'text-accent-red' : 'text-white'}`}>
                    {m?.funding !== undefined ? `${m.funding >= 0 ? '+' : ''}${m.funding.toFixed(4)}%` : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-text-secondary">CVD</div>
                  <div className={`font-mono font-semibold ${m?.cvd && m.cvd > 0 ? 'text-accent-green' : m?.cvd && m.cvd < 0 ? 'text-accent-red' : 'text-white'}`}>
                    {m?.cvd !== undefined ? `${m.cvd >= 0 ? '+' : ''}${Math.round(m.cvd)}` : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-text-secondary">VWAP</div>
                  <div className="font-mono font-semibold text-white">{m?.vwap ? `$${Math.round(m.vwap).toLocaleString()}` : '—'}</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-5 space-y-4">
          <VerdictCard symbol={activeSymbol} bias={currentVerdict?.bias} tier={currentVerdict?.tier}
            entryPrice={currentVerdict?.entry_price} stopLoss={currentVerdict?.stop_loss}
            tp1={currentVerdict?.tp1} tp2={currentVerdict?.tp2} reasoning={currentVerdict?.reasoning}
            currentPrice={currentPrice} loading={loading} />
          <LaneBreakdown lanes={lanes} loading={loading} />
        </div>
        <div className="col-span-12 lg:col-span-4 space-y-4">
          <GlobeView />
          <div className="glass rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">📜 Signal History</h3>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {history.length === 0 && <p className="text-text-secondary text-xs">No signals yet — run strategies</p>}
              {history.slice(0, 10).map((h, i) => (
                <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-dark-600 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${h.bias === 'BULL' ? 'bg-accent-green' : h.bias === 'BEAR' ? 'bg-accent-red' : 'bg-accent-yellow'}`} />
                    <span className="text-text-secondary">{h.time ? new Date(h.time).toLocaleTimeString() : ''}</span>
                    {h.strategy && <span className="text-[10px] px-1.5 py-0.5 rounded bg-dark-600/60 text-accent-blue">{h.strategy}</span>}
                  </div>
                  <span className={h.bias === 'BULL' ? 'text-accent-green' : 'text-accent-red'}>{h.bias}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <MarketScanner />
          <CopilotChat />
          <SimulatorPanel />
        </div>
      </div>

      {/* Daily Brief + Sessions */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8">
          <div className="glass rounded-xl p-5 border border-dark-500 h-full">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">🗞️ Daily Market Brief</h3>
              <span className="text-[10px] text-text-secondary">{brief?.source === 'llm' ? 'AI desk' : brief?.source === 'template' ? 'template' : 'loading…'}</span>
            </div>
            {!brief?.brief && <p className="text-text-secondary text-xs animate-pulse">Writing today's brief…</p>}
            {brief?.brief && (
              <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
                <BriefBody text={brief.brief} />
              </div>
            )}
          </div>
        </div>
        <div className="col-span-12 lg:col-span-4">
          <div className="glass rounded-xl p-5 border border-dark-500 h-full">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">🕒 Trading Sessions</h3>
              <span className="text-[10px] text-text-secondary">{sessions?.is_weekend ? 'weekend' : `${sessions?.time_utc || ''} UTC`}</span>
            </div>
            {!sessions && <p className="text-text-secondary text-xs animate-pulse">Loading sessions…</p>}
            {sessions && (
              <div className="space-y-2">
                {(sessions.sessions || []).map((s: any) => (
                  <div key={s.key} className={`rounded-lg p-2.5 border ${s.open ? 'bg-accent-green/10 border-accent-green/30' : 'bg-dark-700/50 border-dark-500'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-white font-medium">{s.emoji} {s.label} <span className="text-text-secondary font-normal">· {s.start_utc}:00–{s.end_utc}:00</span></span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.open ? 'bg-accent-green/20 text-accent-green' : 'bg-dark-600 text-text-secondary'}`}>
                        {s.open ? 'OPEN' : s.opens_in_h != null ? `opens ${s.opens_in_h}h` : 'closed'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-[10px] text-text-secondary">{s.centers}</span>
                      <span className="text-[10px] text-accent-purple font-mono">vol {s.avg_vol_pct_7d}%</span>
                    </div>
                  </div>
                ))}
                {sessions.best_window_utc && (
                  <div className="text-[11px] text-accent-blue bg-accent-blue/10 border border-accent-blue/20 rounded-lg px-3 py-2">
                    ★ Best window: {sessions.best_window_utc}
                  </div>
                )}
                {(sessions.overlaps || []).length > 0 && (
                  <div className="text-[11px] text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-lg px-3 py-2">
                    ⚡ {sessions.overlaps.map((o: any) => o.label || o.name || String(o)).join(' · ')}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}