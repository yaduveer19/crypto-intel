'use client'
import React, { useEffect, useRef, useState } from 'react'

// Simple 2D globe visualization using Canvas (no three.js dependency issues)
export default function GlobeView({ news }: { news?: any[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [rotation, setRotation] = useState(0)
  const [hoveredPoint, setHoveredPoint] = useState<any>(null)

  // Sample geo-tagged news points
  const points = [
    { lat: 40.7128, lng: -74.0060, label: 'NYSE', severity: 'high' },
    { lat: 51.5074, lng: -0.1278, label: 'London', severity: 'mod' },
    { lat: 35.6762, lng: 139.6503, label: 'Tokyo', severity: 'low' },
    { lat: 22.5431, lng: 114.0579, label: 'Hong Kong', severity: 'high' },
    { lat: 1.3521, lng: 103.8198, label: 'Singapore', severity: 'mod' },
    { lat: 25.2048, lng: 55.2708, label: 'Dubai', severity: 'low' },
    { lat: 37.7749, lng: -122.4194, label: 'Silicon Valley', severity: 'high' },
    { lat: 55.7558, lng: 37.6173, label: 'Moscow', severity: 'mod' },
    { lat: 39.9042, lng: 116.4074, label: 'Beijing', severity: 'mod' },
  ]

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width = canvas.clientWidth * window.devicePixelRatio
    const H = canvas.height = canvas.clientHeight * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    const w = canvas.clientWidth
    const h = canvas.clientHeight

    let animId: number
    let angle = rotation

    const draw = () => {
      angle += 0.003
      ctx.clearRect(0, 0, w, h)

      // Draw globe
      const cx = w / 2
      const cy = h / 2
      const r = Math.min(w, h) * 0.38

      // Outer glow
      const gradient = ctx.createRadialGradient(cx, cy, r * 0.9, cx, cy, r * 1.3)
      gradient.addColorStop(0, 'rgba(51, 153, 255, 0.08)')
      gradient.addColorStop(1, 'rgba(51, 153, 255, 0)')
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(cx, cy, r * 1.3, 0, Math.PI * 2)
      ctx.fill()

      // Globe circle
      ctx.strokeStyle = 'rgba(51, 153, 255, 0.25)'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.stroke()

      // Grid lines (lat/lng)
      ctx.strokeStyle = 'rgba(51, 153, 255, 0.08)'
      ctx.lineWidth = 0.5
      for (let i = 0; i < 6; i++) {
        const latAngle = (i / 6) * Math.PI
        ctx.beginPath()
        ctx.ellipse(cx, cy, r, r * 0.3, 0, 0, Math.PI * 2)
        ctx.stroke()
      }
      for (let i = 0; i < 4; i++) {
        const lngAngle = (i / 4) * Math.PI * 2 + angle
        ctx.beginPath()
        const ex = Math.cos(lngAngle) * r * 0.3
        const ey = Math.sin(lngAngle) * r * 0.3
        ctx.ellipse(cx + ex, cy + ey, r, r * 0.3, lngAngle, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Plot points
      points.forEach((p) => {
        const lngRad = (p.lng / 180) * Math.PI
        const latRad = (p.lat / 180) * Math.PI
        const x = cx + r * Math.cos(latRad) * Math.sin(lngRad + angle)
        const y = cy + r * Math.sin(latRad)

        // Check if on visible side
        const onFront = Math.cos(lngRad + angle) > -0.2
        if (!onFront) return

        const size = p.severity === 'high' ? 4 : p.severity === 'mod' ? 3 : 2
        const colors: Record<string, string> = {
          high: '#ff3366',
          mod: '#ffcc00',
          low: '#3399ff',
        }

        ctx.beginPath()
        ctx.arc(x, y, size, 0, Math.PI * 2)
        ctx.fillStyle = colors[p.severity] || '#3399ff'
        ctx.fill()
        ctx.shadowColor = colors[p.severity] || '#3399ff'
        ctx.shadowBlur = 10
        ctx.fill()
        ctx.shadowBlur = 0

        if (p.severity === 'high') {
          ctx.fillStyle = 'rgba(255, 51, 102, 0.15)'
          ctx.beginPath()
          ctx.arc(x, y, size + 6, 0, Math.PI * 2)
          ctx.fill()
        }
      })

      animId = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animId)
  }, [])

  return (
    <div className="glass rounded-xl p-4 h-full relative overflow-hidden">
      <h3 className="text-sm font-semibold text-white mb-2 relative z-10">🌍 Global Activity</h3>
      <canvas
        ref={canvasRef}
        className="w-full h-[calc(100%-2rem)]"
        style={{ minHeight: '250px' }}
      />
      <div className="absolute bottom-3 left-4 flex gap-3 text-[10px] text-text-secondary">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent-red inline-block" /> High</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent-yellow inline-block" /> Medium</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent-blue inline-block" /> Low</span>
      </div>
    </div>
  )
}
