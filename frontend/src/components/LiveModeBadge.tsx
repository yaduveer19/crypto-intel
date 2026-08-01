'use client'
import React, { useEffect, useState } from 'react'
import { getMode } from '@/lib/api'

export default function LiveModeBadge({ live: liveOverride }: { live?: boolean }) {
  const [mode, setMode] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const r = await getMode()
        if (!cancelled) setMode(r.mode)
      } catch {}
    }
    load()
    const i = setInterval(load, 15000)
    return () => { cancelled = true; clearInterval(i) }
  }, [])

  const live = liveOverride !== undefined ? liveOverride : mode === 'live'
  if (liveOverride === undefined && !mode) return null
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
      live ? 'bg-accent-green/10 text-accent-green border-accent-green/30' : 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${live ? 'bg-accent-green animate-pulse' : 'bg-accent-yellow'}`} />
      {live ? 'LIVE' : 'SIMULATED'}
    </span>
  )
}