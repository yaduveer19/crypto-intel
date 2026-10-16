'use client'
import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { LayoutDashboard, LineChart, Satellite, Crosshair, Brain, Radio, Wallet, Settings, LogOut } from 'lucide-react'

const navGroups = [
  {
    label: 'Markets',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/dashboard/market', label: 'Market Data', icon: LineChart },
      { href: '/dashboard/intel', label: 'Intel Pro', icon: Satellite },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { href: '/dashboard/analyze', label: 'Analyze', icon: Crosshair },
      { href: '/dashboard/strategies', label: 'Strategies', icon: Brain },
      { href: '/dashboard/signals', label: 'Signals', icon: Radio },
    ],
  },
  {
    label: 'Execution',
    items: [
      { href: '/dashboard/paper', label: 'Paper Trading', icon: Wallet },
    ],
  },
  {
    label: 'System',
    items: [
      { href: '/dashboard/settings', label: 'Settings', icon: Settings },
    ],
  },
]

const sectionTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/dashboard/analyze': 'Analyze',
  '/dashboard/market': 'Market Data',
  '/dashboard/intel': 'Intel Pro',
  '/dashboard/strategies': 'Strategies',
  '/dashboard/signals': 'Signals',
  '/dashboard/paper': 'Paper Trading',
  '/dashboard/settings': 'Settings',
}

function UtcClock() {
  const [now, setNow] = useState<string | null>(null)
  useEffect(() => {
    const tick = () => setNow(new Date().toISOString().slice(11, 19))
    tick()
    const i = setInterval(tick, 1000)
    return () => clearInterval(i)
  }, [])
  return (
    <div className="hidden md:flex items-center gap-2 font-mono text-xs text-text-secondary tabular-nums">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-60 animate-ping" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-green" />
      </span>
      <span className="text-accent-green/90 font-semibold text-[10px] tracking-[0.14em]">LIVE</span>
      <span className="text-text-muted">{now || '--:--:--'} UTC</span>
    </div>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const demoUser = user || { name: 'Demo User', email: 'demo@cryptointel.io' }
  const logout = () => { localStorage.removeItem('token'); window.location.href = '/login' }
  const sectionTitle = sectionTitles[pathname] || 'Crypto Intel'

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className={`fixed lg:sticky top-0 inset-y-0 left-0 z-40 w-60 h-screen bg-dark-950/95 backdrop-blur-xl border-r border-white/[0.055] transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 transition-transform duration-200 flex flex-col`}>
        <div className="px-5 pt-5 pb-4">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#e8c273] to-[#b8873a] flex items-center justify-center text-dark-950 font-display font-extrabold text-[13px] tracking-tight shadow-[0_0_20px_-4px_rgba(217,168,78,0.45)] group-hover:shadow-[0_0_26px_-2px_rgba(217,168,78,0.6)] transition-shadow">CI</div>
            <div>
              <div className="font-display font-bold text-[15px] text-white leading-none tracking-tight">Crypto Intel</div>
              <div className="label-micro mt-1.5 text-text-muted">Terminal v4.2</div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-3 pb-4 space-y-4 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="label-micro px-3 pb-1.5 text-text-muted">{group.label}</div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = pathname === item.href
                  const Icon = item.icon
                  return (
                    <Link key={item.href} href={item.href}
                      className={`group relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                        active
                          ? 'bg-white/[0.06] text-white'
                          : 'text-text-secondary hover:text-white hover:bg-white/[0.035]'
                      }`}>
                      {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-[2.5px] rounded-full bg-accent-gold shadow-[0_0_8px_rgba(217,168,78,0.8)]" />}
                      <Icon size={15} strokeWidth={1.9} className={active ? 'text-accent-gold' : 'text-text-muted group-hover:text-white transition-colors'} />
                      <span>{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-white/[0.055]">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-full bg-dark-700 border border-white/10 flex items-center justify-center text-[11px] font-bold text-accent-gold">
              {(demoUser.name || demoUser.email || 'U').slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-medium text-white truncate">{demoUser.name || demoUser.email}</div>
              <div className="text-[10px] text-text-muted">Free · all features unlocked</div>
            </div>
          </div>
          <button onClick={logout} className="flex items-center gap-2 text-[13px] text-text-muted hover:text-accent-red transition-colors">
            <LogOut size={14} strokeWidth={1.9} /> Sign out
          </button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        <header className="sticky top-0 z-20 bg-dark-950/70 backdrop-blur-xl border-b border-white/[0.055] px-4 lg:px-6 py-2.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden text-text-secondary hover:text-white text-lg leading-none">☰</button>
            <span className="font-display font-semibold text-sm text-text-secondary truncate">{sectionTitle}</span>
          </div>
          <UtcClock />
        </header>
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
