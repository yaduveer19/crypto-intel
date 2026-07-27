'use client'
import React from 'react'

interface Props {
  lanes?: Array<{
    lane: string
    bias: string
    tier: string
    signals?: string[]
  }>
  loading?: boolean
}

const laneIcons: Record<string, string> = {
  technical: '📈',
  flow: '💧',
  narrative: '📰',
  macro: '🌍',
}

const biasColors: Record<string, string> = {
  BULL: 'text-accent-green bg-accent-green/10',
  BEAR: 'text-accent-red bg-accent-red/10',
  NEUTRAL: 'text-accent-yellow bg-accent-yellow/10',
}

export default function LaneBreakdown({ lanes, loading }: Props) {
  if (loading) {
    return (
      <div className="glass rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-dark-600 rounded w-24 mb-3" />
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-dark-600 rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (!lanes || lanes.length === 0) {
    return (
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-semibold text-white mb-3">🔍 Analysis Lanes</h3>
        <p className="text-text-secondary text-xs">Waiting for lane data...</p>
      </div>
    )
  }

  return (
    <div className="glass rounded-xl p-4">
      <h3 className="text-sm font-semibold text-white mb-3">🔍 Analysis Lanes</h3>
      <div className="space-y-2">
        {lanes.map((lane, i) => (
          <div key={i} className="bg-dark-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span>{laneIcons[lane.lane] || '📊'}</span>
                <span className="text-sm text-white capitalize">{lane.lane}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${biasColors[lane.bias] || 'text-text-secondary bg-dark-600'}`}>
                  {lane.bias}
                </span>
                <span className="text-[10px] text-text-secondary">{lane.tier}</span>
              </div>
            </div>
            {lane.signals && lane.signals.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {lane.signals.map((sig, j) => (
                  <span key={j} className="text-[10px] text-text-secondary bg-dark-600 px-1.5 py-0.5 rounded">
                    {sig}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
