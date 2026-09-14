'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getIntelNews } from '@/lib/api'

export default function NewsPanel() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'news' | 'calendar'>('news')

  const load = useCallback(async () => {
    try { setData(await getIntelNews()) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load(); const i = setInterval(load, 180000); return () => clearInterval(i) }, [load])

  const fng = data?.fear_greed
  const fngColor = fng && fng.value >= 60 ? 'text-accent-green' : fng && fng.value <= 40 ? 'text-accent-red' : 'text-accent-yellow'

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">📰 Macro & Whale News</h3>
        <div className="flex gap-1">
          <button onClick={() => setTab('news')}
            className={`text-[10px] px-2 py-1 rounded ${tab === 'news' ? 'bg-accent-blue/20 text-accent-blue' : 'text-text-secondary hover:text-white'}`}>News</button>
          <button onClick={() => setTab('calendar')}
            className={`text-[10px] px-2 py-1 rounded ${tab === 'calendar' ? 'bg-accent-blue/20 text-accent-blue' : 'text-text-secondary hover:text-white'}`}>
            Calendar {data?.high_impact_count ? `(${data.high_impact_count})` : ''}
          </button>
        </div>
      </div>

      {/* Fear & Greed strip */}
      {fng && (
        <div className="flex items-center justify-between bg-dark-700/50 rounded-lg px-3 py-2 mb-3">
          <div>
            <div className="text-[9px] text-text-secondary">Fear & Greed Index</div>
            <div className={`text-lg font-bold font-mono ${fngColor}`}>{fng.value}</div>
          </div>
          <div className="flex-1 mx-3 h-2 bg-dark-600 rounded-full overflow-hidden relative">
            <div className="absolute left-0 top-0 bottom-0 bg-gradient-to-r from-accent-red via-accent-yellow to-accent-green opacity-30" style={{ width: '100%' }} />
            <div className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-dark-800 ${fng.value >= 60 ? 'bg-accent-green' : fng.value <= 40 ? 'bg-accent-red' : 'bg-accent-yellow'}`}
              style={{ left: `calc(${fng.value}% - 6px)` }} />
          </div>
          <div className={`text-[10px] font-bold ${fngColor}`}>{fng.label}</div>
        </div>
      )}

      {loading && <p className="text-text-secondary text-xs">Loading news...</p>}

      {tab === 'news' && (
        <div className="space-y-1.5 max-h-96 overflow-y-auto">
          {data?.headlines?.length === 0 && <p className="text-text-secondary text-xs">No headlines loaded</p>}
          {data?.headlines?.map((h: any, i: number) => (
            <a key={i} href={h.link || '#'} target="_blank" rel="noopener"
              className="block bg-dark-700/40 hover:bg-dark-600/50 rounded-lg px-3 py-2 transition">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[9px] text-accent-blue font-semibold">{h.source}</span>
                <span className="text-[9px] text-text-secondary">{h.time ? h.time.slice(5, 16) : ''}</span>
              </div>
              <p className="text-[11px] text-white leading-snug">{h.title}</p>
            </a>
          ))}
        </div>
      )}

      {tab === 'calendar' && (
        <div className="space-y-1.5 max-h-96 overflow-y-auto">
          {data?.calendar?.length === 0 && <p className="text-text-secondary text-xs">No events this week</p>}
          {data?.calendar?.map((e: any, i: number) => (
            <div key={i} className="flex items-center gap-2 bg-dark-700/40 rounded-lg px-3 py-2">
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                e.impact === 'high' ? 'bg-accent-red/20 text-accent-red' : 'bg-accent-yellow/20 text-accent-yellow'
              }`}>{e.country}</span>
              <div className="flex-1">
                <p className={`text-[11px] ${e.high_impact ? 'text-white font-semibold' : 'text-text-secondary'}`}>{e.title}</p>
                <p className="text-[9px] text-text-secondary">
                  {e.date ? new Date(e.date).toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                  {e.forecast ? ` · F: ${e.forecast}` : ''}{e.previous ? ` · P: ${e.previous}` : ''}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-[9px] text-text-secondary mt-2">Sources: {data?.sources?.join(' · ')}</p>
    </div>
  )
}