'use client'
import React from 'react'

interface Props {
  symbol: string
  bias?: string
  tier?: string
  entryPrice?: number
  stopLoss?: number
  tp1?: number
  tp2?: number
  reasoning?: string
  currentPrice?: number
  loading?: boolean
}

export default function VerdictCard({
  symbol, bias, tier, entryPrice, stopLoss, tp1, tp2, reasoning, currentPrice, loading
}: Props) {
  const biasColors: Record<string, string> = {
    BULL: 'text-accent-green glow-green border-accent-green/30',
    BEAR: 'text-accent-red glow-red border-accent-red/30',
    NEUTRAL: 'text-accent-yellow border-accent-yellow/30',
  }
  const tierDots: Record<string, string> = {
    HIGH: '🟢',
    MOD: '🟡',
    LOW: '🔴',
  }

  if (loading) {
    return (
      <div className="glass rounded-xl p-5 animate-pulse h-48">
        <div className="h-4 bg-dark-600 rounded w-24 mb-3" />
        <div className="h-8 bg-dark-600 rounded w-32 mb-3" />
        <div className="h-3 bg-dark-600 rounded w-full" />
      </div>
    )
  }

  return (
    <div className={`glass rounded-xl p-5 border ${bias ? biasColors[bias as string] || 'border-dark-500' : 'border-dark-500'}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs text-text-secondary uppercase tracking-wider">Signal</span>
          <h3 className="text-lg font-bold text-white">{symbol.replace('USDT', '')}/USDT</h3>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${biasColors[bias as string] || 'text-white'}`}>
            {bias || '--'}
          </div>
          <div className="text-xs text-text-secondary">{tier ? `${tierDots[tier] || ''} ${tier}` : ''}</div>
        </div>
      </div>

      {currentPrice && (
        <div className="text-sm text-text-secondary mb-3">
          Live: <span className="text-white font-mono">${currentPrice.toLocaleString()}</span>
        </div>
      )}

      <div className="grid grid-cols-4 gap-2 mb-3">
        <div className="bg-dark-700/50 rounded-lg p-2 text-center">
          <div className="text-xs text-text-secondary">Entry</div>
          <div className="text-sm font-mono font-bold text-white">
            {entryPrice ? `$${entryPrice.toLocaleString()}` : '--'}
          </div>
        </div>
        <div className="bg-dark-700/50 rounded-lg p-2 text-center">
          <div className="text-xs text-text-secondary">Stop</div>
          <div className="text-sm font-mono font-bold text-accent-red">
            {stopLoss ? `$${stopLoss.toLocaleString()}` : '--'}
          </div>
        </div>
        <div className="bg-dark-700/50 rounded-lg p-2 text-center">
          <div className="text-xs text-text-secondary">TP1</div>
          <div className="text-sm font-mono font-bold text-accent-green">
            {tp1 ? `$${tp1.toLocaleString()}` : '--'}
          </div>
        </div>
        <div className="bg-dark-700/50 rounded-lg p-2 text-center">
          <div className="text-xs text-text-secondary">TP2</div>
          <div className="text-sm font-mono font-bold text-accent-blue">
            {tp2 ? `$${tp2.toLocaleString()}` : '--'}
          </div>
        </div>
      </div>

      {reasoning && (
        <p className="text-sm text-text-secondary italic border-t border-dark-500 pt-2 mt-1">
          {reasoning}
        </p>
      )}
    </div>
  )
}
