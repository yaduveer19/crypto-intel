'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getOnchain } from '@/lib/api'

const fmtUsd = (n: any) => {
  const v = Number(n) || 0
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  return `$${v.toFixed(0)}`
}

export default function OnChainPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try { setData(await getOnchain()) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load(); const i = setInterval(load, 120000); return () => clearInterval(i) }, [load])

  const g = data?.global || {}
  const net = data?.network || {}
  const flow = data?.exchange_flow || {}
  const stables = data?.stablecoins || {}

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">🔗 On-Chain Intelligence</h3>
        <div className="flex items-center gap-2">
          {data?.regime && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              data.regime === 'ACCUMULATION' ? 'text-accent-green bg-accent-green/10 border-accent-green/30'
              : data.regime === 'DISTRIBUTION' ? 'text-accent-red bg-accent-red/10 border-accent-red/30'
              : 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/30'
            }`}>{data.regime}</span>
          )}
          <span className="text-[10px] text-text-secondary">score {data?.onchain_score ?? '—'}</span>
        </div>
      </div>

      {loading && <p className="text-text-secondary text-xs">Loading on-chain data...</p>}

      {data && (
        <>
          {/* Global market */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="bg-dark-700/50 rounded-lg p-2 text-center">
              <div className="text-[9px] text-text-secondary">Total MCap</div>
              <div className="text-sm font-bold text-white font-mono">{fmtUsd(g.total_mcap_usd)}</div>
              <div className={`text-[9px] font-semibold ${(g.mcap_change_24h || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                {(g.mcap_change_24h || 0) >= 0 ? '+' : ''}{g.mcap_change_24h}%
              </div>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-2 text-center">
              <div className="text-[9px] text-text-secondary">BTC Dominance</div>
              <div className="text-sm font-bold text-accent-yellow font-mono">{g.btc_dominance}%</div>
              <div className="text-[9px] text-text-secondary">ETH {g.eth_dominance}%</div>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-2 text-center">
              <div className="text-[9px] text-text-secondary">24h Volume</div>
              <div className="text-sm font-bold text-white font-mono">{fmtUsd(g.total_vol_usd)}</div>
              <div className="text-[9px] text-text-secondary">{g.active_cryptos} coins</div>
            </div>
          </div>

          {/* Whale flow */}
          <div className="bg-dark-700/50 rounded-lg p-3 mb-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] text-text-secondary">Whale Tape (spot ≥$30k)</span>
              <span className={`text-[10px] font-bold ${flow.flow_bias === 'ACCUMULATION' ? 'text-accent-green' : flow.flow_bias === 'DISTRIBUTION' ? 'text-accent-red' : 'text-accent-yellow'}`}>
                {flow.flow_bias}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-dark-600 rounded overflow-hidden flex">
                <div className="h-full bg-accent-green" style={{ width: `${(flow.whale_buy_usd / ((flow.whale_buy_usd || 0) + (flow.whale_sell_usd || 0) || 1)) * 100}%` }} />
                <div className="h-full bg-accent-red" style={{ width: `${(flow.whale_sell_usd / ((flow.whale_buy_usd || 0) + (flow.whale_sell_usd || 0) || 1)) * 100}%` }} />
              </div>
              <span className="text-[10px] font-mono text-text-secondary">{flow.whale_count} prints</span>
            </div>
            <div className="flex justify-between text-[10px] font-mono mt-1">
              <span className="text-accent-green">Buy {fmtUsd(flow.whale_buy_usd)}</span>
              <span className={(flow.net_flow_usd || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'}>
                Net {(flow.net_flow_usd || 0) >= 0 ? '+' : ''}{fmtUsd(flow.net_flow_usd)}
              </span>
              <span className="text-accent-red">Sell {fmtUsd(flow.whale_sell_usd)}</span>
            </div>
          </div>

          {/* Stablecoins + network */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-dark-700/50 rounded-lg p-2">
              <div className="text-[9px] text-text-secondary mb-1">Stablecoin Supply (dry powder)</div>
              <div className="text-sm font-bold text-accent-blue font-mono">{fmtUsd(stables.total_usd)}</div>
              {stables.top?.slice(0, 3).map((s: any, i: number) => (
                <div key={i} className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                  <span>{s.name}</span><span className="font-mono">{fmtUsd(s.supply)}</span>
                </div>
              ))}
            </div>
            <div className="bg-dark-700/50 rounded-lg p-2">
              <div className="text-[9px] text-text-secondary mb-1">BTC Network</div>
              <div className="flex justify-between text-[10px] text-text-secondary">
                <span>Hash rate</span><span className="font-mono text-white">{net.hash_rate_ths} TH/s</span>
              </div>
              <div className="flex justify-between text-[10px] text-text-secondary">
                <span>TX 24h</span><span className="font-mono text-white">{Number(net.tx_24h || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-[10px] text-text-secondary">
                <span>Mempool</span><span className="font-mono text-white">{Number(net.mempool_tx || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>

          <p className="text-[9px] text-text-secondary mt-2">Sources: blockchain.info · CoinGecko · DefiLlama · Binance</p>
        </>
      )}
    </div>
  )
}