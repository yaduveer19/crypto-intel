'use client'
import React, { useState } from 'react'
import { runSimulation } from '@/lib/api'

export default function SimulatorPanel() {
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [shock, setShock] = useState('-5')
  const [portfolio, setPortfolio] = useState('10000')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleRun = async () => {
    setLoading(true)
    try {
      const res = await runSimulation(symbol, parseFloat(shock), parseFloat(portfolio))
      setResult(res)
    } catch {
      setResult({ error: 'Simulation failed' })
    }
    setLoading(false)
  }

  return (
    <div className="glass rounded-xl p-4">
      <h3 className="text-sm font-semibold text-white mb-3">📊 Scenario Simulator</h3>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-xs text-text-secondary">Asset</label>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full bg-dark-700 text-white text-xs rounded px-2 py-1.5 border border-dark-500"
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-text-secondary">Shock %</label>
          <input
            value={shock}
            onChange={(e) => setShock(e.target.value)}
            className="w-full bg-dark-700 text-white text-xs rounded px-2 py-1.5 border border-dark-500"
            placeholder="-5"
          />
        </div>
      </div>

      <button
        onClick={handleRun}
        disabled={loading}
        className="w-full bg-accent-purple/20 text-accent-purple text-sm py-2 rounded-lg hover:bg-accent-purple/30 disabled:opacity-40 transition mb-3"
      >
        {loading ? 'Running...' : 'Run Simulation'}
      </button>

      {result && !result.error && (
        <div className="space-y-2 text-xs">
          <div className="bg-dark-700/50 rounded-lg p-2 flex justify-between">
            <span className="text-text-secondary">Impact:</span>
            <span className={result.portfolio_impact_pct < 0 ? 'text-accent-red' : 'text-accent-green'}>
              {result.portfolio_impact_pct > 0 ? '+' : ''}{result.portfolio_impact_pct}% (${result.portfolio_impact_usd?.toLocaleString()})
            </span>
          </div>

          {result.cross_asset_impact?.length > 0 && (
            <div>
              <div className="text-text-secondary mb-1">Cross-asset impact:</div>
              {result.cross_asset_impact.map((c: any, i: number) => (
                <div key={i} className="bg-dark-700/50 rounded-lg p-2 flex justify-between mb-1">
                  <span>{c.symbol.replace('USDT', '')}</span>
                  <span className={c.estimated_move_pct < 0 ? 'text-accent-red' : 'text-accent-green'}>
                    {c.estimated_move_pct > 0 ? '+' : ''}{c.estimated_move_pct}% → ${c.estimated_price?.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result.stop_losses_triggered?.length > 0 && (
            <div>
              <div className="text-accent-red mb-1">⚠️ Stop losses triggered: {result.stop_losses_triggered.length}</div>
            </div>
          )}

          {result.stop_losses_triggered?.length === 0 && (
            <div className="text-accent-green">✓ No stop losses triggered</div>
          )}
        </div>
      )}

      {result?.error && (
        <div className="text-accent-red text-xs">{result.error}</div>
      )}
    </div>
  )
}
