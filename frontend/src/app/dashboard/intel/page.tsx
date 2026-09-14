'use client'
import React, { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import LiveModeBadge from '@/components/LiveModeBadge'
import FundingMatrixPanel from '@/components/intel/FundingMatrixPanel'
import LiquidationHeatmap from '@/components/intel/LiquidationHeatmap'
import ChartPatternsPanel from '@/components/intel/ChartPatternsPanel'
import OnChainPanel from '@/components/intel/OnChainPanel'
import MacroPanel from '@/components/intel/MacroPanel'
import NewsPanel from '@/components/intel/NewsPanel'
import WhaleWallsPanel from '@/components/intel/WhaleWallsPanel'
import FootprintPanel from '@/components/FootprintPanel'

const Globe3D = dynamic(() => import('@/components/intel/Globe3D'), { ssr: false })

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
const TABS = [
  { id: 'globe', label: '🌐 Global Radar' },
  { id: 'funding', label: '⚡ Funding Matrix' },
  { id: 'liq', label: '🧲 Liquidations' },
  { id: 'patterns', label: '📐 Patterns' },
  { id: 'footprint', label: '👣 Footprint' },
  { id: 'walls', label: '🧱 Whale Walls' },
  { id: 'onchain', label: '🔗 On-Chain' },
  { id: 'macro', label: '📊 Macro' },
  { id: 'news', label: '📰 News' },
]

export default function IntelPage() {
  const [tab, setTab] = useState('globe')
  const [activeSymbol, setActiveSymbol] = useState('BTCUSDT')

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Intelligence</h1>
          <p className="text-xs text-text-secondary mt-0.5">Real data — liquidations, patterns, funding matrix, on-chain, macro correlations, news</p>
        </div>
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

      {/* Tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition ${
              tab === t.id ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30' : 'text-text-secondary hover:text-white bg-dark-700/40 border border-transparent'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'globe' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-8">
            <Globe3D height={460} />
          </div>
          <div className="col-span-12 lg:col-span-4">
            <NewsPanel />
          </div>
        </div>
      )}

      {tab === 'funding' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <FundingMatrixPanel />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <NewsPanel />
          </div>
        </div>
      )}

      {tab === 'liq' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <LiquidationHeatmap symbol={activeSymbol} />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <WhaleWallsPanel symbol={activeSymbol} />
          </div>
        </div>
      )}

      {tab === 'patterns' && (
        <div className="space-y-4">
          <ChartPatternsPanel symbol={activeSymbol} />
          <OnChainPanel />
        </div>
      )}

      {tab === 'footprint' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12">
            <FootprintPanel symbol={activeSymbol} />
          </div>
        </div>
      )}

      {tab === 'walls' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <WhaleWallsPanel symbol={activeSymbol} />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <LiquidationHeatmap symbol={activeSymbol} />
          </div>
        </div>
      )}

      {tab === 'onchain' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <OnChainPanel />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <MacroPanel />
          </div>
        </div>
      )}

      {tab === 'macro' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <MacroPanel />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <NewsPanel />
          </div>
        </div>
      )}

      {tab === 'news' && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7">
            <NewsPanel />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <MacroPanel />
          </div>
        </div>
      )}
    </div>
  )
}