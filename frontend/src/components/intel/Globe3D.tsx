'use client'
import React, { useEffect, useState, useRef, useCallback } from 'react'
import Globe from 'react-globe.gl'

const HUBS = [
  { lat: 40.7128, lng: -74.006, label: 'New York', exchange: 'NYSE / Coinbase', color: '#3b82f6' },
  { lat: 51.5074, lng: -0.1278, label: 'London', exchange: 'LSE / Kraken', color: '#8b5cf6' },
  { lat: 35.6762, lng: 139.6503, label: 'Tokyo', exchange: 'bitFlyer', color: '#22c55e' },
  { lat: 22.5431, lng: 114.0579, label: 'Hong Kong', exchange: 'HKEX / OKX', color: '#f59e0b' },
  { lat: 1.3521, lng: 103.8198, label: 'Singapore', exchange: 'Bybit', color: '#ef4444' },
  { lat: 25.2048, lng: 55.2708, label: 'Dubai', exchange: 'Bybit / HL', color: '#06b6d4' },
  { lat: 37.7749, lng: -122.4194, label: 'San Francisco', exchange: 'Coinbase', color: '#3b82f6' },
  { lat: 52.52, lng: 13.405, label: 'Berlin', exchange: 'BSDEX', color: '#8b5cf6' },
  { lat: -33.8688, lng: 151.2093, label: 'Sydney', exchange: 'Swyftx', color: '#22c55e' },
  { lat: 19.076, lng: 72.8777, label: 'Mumbai', exchange: 'Delta India', color: '#f59e0b' },
  { lat: 43.6532, lng: -79.3832, label: 'Toronto', exchange: 'Shakepay', color: '#06b6d4' },
  { lat: -23.5505, lng: -46.6333, label: 'Sao Paulo', exchange: 'Mercado Bitcoin', color: '#ef4444' },
]

// arcs between major liquidity hubs
const ARCS = [
  { startLat: 40.7128, startLng: -74.006, endLat: 51.5074, endLng: -0.1278 },
  { startLat: 51.5074, startLng: -0.1278, endLat: 35.6762, endLng: 139.6503 },
  { startLat: 35.6762, startLng: 139.6503, endLat: 22.5431, endLng: 114.0579 },
  { startLat: 22.5431, startLng: 114.0579, endLat: 1.3521, endLng: 103.8198 },
  { startLat: 1.3521, startLng: 103.8198, endLat: 25.2048, endLng: 55.2708 },
  { startLat: 25.2048, startLng: 55.2708, endLat: 19.076, endLng: 72.8777 },
  { startLat: 37.7749, startLng: -122.4194, endLat: 40.7128, endLng: -74.006 },
  { startLat: 37.7749, startLng: -122.4194, endLat: -23.5505, endLng: -46.6333 },
  { startLat: -33.8688, startLng: 151.2093, endLat: 1.3521, endLng: 103.8198 },
  { startLat: 19.076, startLng: 72.8777, endLat: 52.52, endLng: 13.405 },
]

export default function Globe3D({ prices, height = 420 }: { prices?: Record<string, number>; height?: number }) {
  const globeRef = useRef<any>(null)
  const [mounted, setMounted] = useState(false)
  const [dimensions, setDimensions] = useState({ width: 400, height })

  useEffect(() => { setMounted(true) }, [])

  useEffect(() => {
    const update = () => {
      const el = document.getElementById('globe3d-box')
      if (el) setDimensions({ width: el.clientWidth, height })
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [height])

  useEffect(() => {
    if (globeRef.current) {
      globeRef.current.controls().autoRotate = true
      globeRef.current.controls().autoRotateSpeed = 0.6
      globeRef.current.pointOfView({ lat: 20, lng: 20, altitude: 2.2 }, 0)
    }
  }, [mounted])

  const priceInfo = prices || {}

  if (!mounted) {
    return <div className="glass rounded-xl border border-dark-500" style={{ height }}><p className="text-text-secondary text-xs p-4">Loading 3D globe...</p></div>
  }

  return (
    <div className="glass rounded-xl p-4 border border-dark-500">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-white">🌐 3D Global Radar</h3>
        <div className="text-[10px] text-text-secondary">12 liquidity hubs · live routing</div>
      </div>
      <div id="globe3d-box">
        <Globe
          ref={globeRef}
          width={dimensions.width}
          height={height - 40}
          backgroundColor="rgba(0,0,0,0)"
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          // hub points
          pointsData={HUBS}
          pointLat={(d: any) => d.lat}
          pointLng={(d: any) => d.lng}
          pointColor={(d: any) => d.color}
          pointAltitude={0.02}
          pointRadius={0.35}
          pointLabel={(d: any) => `
            <div style="background:#111827;border:1px solid #374151;border-radius:8px;padding:8px 12px;font-family:monospace">
              <div style="color:#fff;font-weight:bold;font-size:12px">${d.label}</div>
              <div style="color:#9ca3af;font-size:10px">${d.exchange}</div>
              ${priceInfo.BTCUSDT ? `<div style="color:#22c55e;font-size:10px">BTC $${Math.round(priceInfo.BTCUSDT).toLocaleString()}</div>` : ''}
            </div>
          `}
          // liquidity arcs
          arcsData={ARCS}
          arcStartLat={(d: any) => d.startLat}
          arcStartLng={(d: any) => d.startLng}
          arcEndLat={(d: any) => d.endLat}
          arcEndLng={(d: any) => d.endLng}
          arcColor={() => ['#3b82f6', '#8b5cf6']}
          arcDashLength={0.4}
          arcDashGap={0.2}
          arcDashAnimateTime={2500}
          arcStroke={0.3}
          arcAltitudeAutoScale={0.4}
          // atmosphere
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.18}
        />
      </div>
      {/* Live price strip */}
      <div className="flex gap-2 mt-2">
        {['BTCUSDT', 'ETHUSDT', 'SOLUSDT'].map(sym => (
          <div key={sym} className="flex-1 bg-dark-700/50 rounded-lg px-2 py-1.5 text-center">
            <div className="text-[9px] text-text-secondary">{sym.replace('USDT', '')}</div>
            <div className="text-xs font-bold text-white font-mono">
              {priceInfo[sym] ? (priceInfo[sym] > 1000 ? `$${Math.round(priceInfo[sym]).toLocaleString()}` : `$${Number(priceInfo[sym]).toFixed(2)}`) : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}