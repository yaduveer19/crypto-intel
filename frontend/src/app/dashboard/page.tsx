'use client'
import React, { useEffect, useState, useCallback } from 'react'
import VerdictCard from '@/components/VerdictCard'
import GlobeView from '@/components/GlobeView'
import LaneBreakdown from '@/components/LaneBreakdown'
import CopilotChat from '@/components/CopilotChat'
import SimulatorPanel from '@/components/SimulatorPanel'
import MarketScanner from '@/components/MarketScanner'
import LiveModeBadge from '@/components/LiveModeBadge'
import { createWebSocket, createBinanceWebSocket } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DashboardPage() {
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [verdicts, setVerdicts] = useState<Record<string, any>>({})
  const [lanes, setLanes] = useState<any[]>([])
  const [activeSymbol, setActiveSymbol] = useState('BTCUSDT')
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState<any[]>([])

  const fetchData = useCallback(async () => {
    try {
      const [v, l, h] = await Promise.all([
        fetch(`${API}/api/verdict/${activeSymbol}`).then(r => r.ok ? r.json() : {}),
        fetch(`${API}/api/lanes/${activeSymbol}`).then(r => r.ok ? r.json() : []),
        fetch(`${API}/api/signals/history?symbol=${activeSymbol}&limit=20`).then(r => r.ok ? r.json() : []),
      ])
      setVerdicts(prev => ({ ...prev, [activeSymbol]: v }))
      setLanes(Array.isArray(l) ? l : [])
      setHistory(Array.isArray(h) ? h : [])
    } catch {}
    setLoading(false)
  }, [activeSymbol])

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 30000); return () => clearInterval(i) }, [fetchData])

  useEffect(() => {
    const ws = createWebSocket((data) => {
      if (data.type === 'verdict' && data.symbol) setVerdicts(prev => ({ ...prev, [data.symbol]: data.data }))
    })
    return () => ws.close()
  }, [])

  useEffect(() => {
    const cleanups = SYMBOLS.map(sym => createBinanceWebSocket(sym, (price) => setPrices(prev => ({ ...prev, [sym]: price }))))
    return () => cleanups.forEach(c => c.close())
  }, [])

  const currentVerdict = verdicts[activeSymbol]
  const currentPrice = prices[activeSymbol]

  const formatPrice = (p?: number) => {
    if (!p) return '---'
    return p > 1000 ? `$${p.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : `$${p.toFixed(2)}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="flex items-center gap-3">
          <LiveModeBadge />
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

      {/* KPI Row */}
      <div className="grid grid-cols-3 gap-4">
        {SYMBOLS.map(sym => (
          <div key={sym} className="glass rounded-xl p-4 border border-dark-500">
            <div className="flex justify-between items-center">
              <div>
                <div className="text-xs text-text-secondary">{sym.replace('USDT', '')}/USDT</div>
                <div className="text-2xl font-bold text-white font-mono mt-1">{formatPrice(prices[sym])}</div>
              </div>
              {verdicts[sym] && (
                <div className={`text-lg font-bold ${
                  verdicts[sym].bias === 'BULL' ? 'text-accent-green' : verdicts[sym].bias === 'BEAR' ? 'text-accent-red' : 'text-accent-yellow'
                }`}>
                  {verdicts[sym].bias}
                  <div className="text-[10px] text-text-secondary font-normal">{verdicts[sym].tier}</div>
                </div>
              )}
            </div>
          </div>
        ))}
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
              {history.length === 0 && <p className="text-text-secondary text-xs">No signals yet</p>}
              {history.slice(0, 10).map((h, i) => (
                <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-dark-600 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${h.bias === 'BULL' ? 'bg-accent-green' : h.bias === 'BEAR' ? 'bg-accent-red' : 'bg-accent-yellow'}`} />
                    <span className="text-text-secondary">{h.time ? new Date(h.time).toLocaleTimeString() : ''}</span>
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
    </div>
  )
}
