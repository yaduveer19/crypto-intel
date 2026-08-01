'use client'
import React, { useEffect, useState } from 'react'
import LiveModeBadge from '@/components/LiveModeBadge'
import CandlestickChart from '@/components/CandlestickChart'
import OrderbookPanel from '@/components/OrderbookPanel'
import CVDChart from '@/components/CVDChart'
import VolumeProfileChart from '@/components/VolumeProfileChart'
import FootprintPanel from '@/components/FootprintPanel'
import { getExchanges } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

export default function MarketDataPage() {
  const [activeSymbol, setActiveSymbol] = useState('BTCUSDT')
  const [exchange, setExchange] = useState('binance')
  const [exchanges, setExchanges] = useState<string[]>([])

  useEffect(() => {
    getExchanges().then(r => { setExchanges(r.exchanges || []) }).catch(() => {})
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Market Data</h1>
          <LiveModeBadge />
        </div>
        <div className="flex items-center gap-3">
          <select value={exchange} onChange={(e) => setExchange(e.target.value)}
            className="bg-dark-800 border border-dark-600 rounded-lg text-sm text-white px-3 py-2 focus:outline-none focus:border-accent-blue">
            {exchanges.map((ex) => <option key={ex} value={ex}>{ex}</option>)}
          </select>
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

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-7 space-y-4">
          <CandlestickChart symbol={activeSymbol} exchange={exchange} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CVDChart symbol={activeSymbol} />
            <VolumeProfileChart symbol={activeSymbol} />
          </div>
        </div>
        <div className="col-span-12 lg:col-span-5 space-y-4">
          <OrderbookPanel symbol={activeSymbol} exchange={exchange} />
          <FootprintPanel symbol={activeSymbol} />
        </div>
      </div>
    </div>
  )
}
