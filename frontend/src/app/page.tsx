'use client'
import React from 'react'
import Link from 'next/link'

const features = [
  { icon: '🧠', title: 'AI Analysis', desc: '4-lane analysis engine: Technical, Flow, Narrative & Macro — synthesized by LLM' },
  { icon: '📊', title: '5 Trading Strategies', desc: 'Trend Following, RSI Mean Reversion, MACD Momentum, Breakout & Grid Levels — auto-generate signals' },
  { icon: '🌍', title: 'Global Intelligence', desc: 'Real-time globe visualization of crypto activity, news, and market events' },
  { icon: '🤖', title: 'AI Copilot', desc: 'Chat with live market context — get answers with current price data' },
  { icon: '📱', title: 'Telegram Alerts', desc: 'Connect your Telegram bot and receive trade signals directly to your phone' },
  { icon: '📈', title: 'Scenario Simulator', desc: 'Stress-test your portfolio with shock simulations across correlated assets' },
  { icon: '🔍', title: 'Live Dashboard', desc: 'Real-time verdict cards, lane breakdowns, signal history, and price streams' },
  { icon: '🛡️', title: 'Risk Management', desc: 'ATR-based stop-loss and take-profit levels calculated for every signal' },
]

const plans = [
  { name: 'Free', price: '$0', desc: 'Everything is free — no limits', features: ['All 5 trading strategies', 'BTC, ETH, SOL + all symbols', 'AI Copilot with live context', 'Telegram alerts', 'Unlimited signal history', 'Scenario simulator', 'Globe visualization', '4-lane AI analysis', 'Real-time WebSocket updates'] },
  { name: 'Free', price: '$0', desc: 'No credit card needed', features: ['Same features as everyone', 'No paid tiers', 'No hidden limits', 'Community support', 'All future updates included', 'API access', 'Priority in queue'] },
  { name: 'Free', price: '$0', desc: 'Forever free — always', features: ['All features unlocked', 'No subscription required', 'Open source friendly', 'Self-hostable', 'No data selling', 'Privacy first'] },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-dark-900">
      {/* Navbar */}
      <nav className="border-b border-dark-700 bg-dark-800/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white font-bold text-sm">CI</div>
            <span className="text-lg font-bold text-white">Crypto Intel</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-text-secondary hover:text-white text-sm transition">Sign In</Link>
            <Link href="/signup" className="bg-accent-blue/20 text-accent-blue px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-blue/30 transition">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="inline-block px-3 py-1 rounded-full bg-accent-blue/10 text-accent-blue text-xs mb-4 border border-accent-blue/20">🚀 AI-Powered Trading Intelligence</div>
        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
          Trade Smarter with<br />
          <span className="bg-gradient-to-r from-accent-blue via-accent-purple to-accent-green bg-clip-text text-transparent">Multi-Lane AI</span>
        </h1>
        <p className="text-text-secondary text-lg max-w-2xl mx-auto mb-10">
          The only platform that combines Technical, Flow, Narrative, and Macro analysis
          into a single AI-powered trading verdict — with real-time signals, Telegram alerts, and scenario simulation.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/signup" className="bg-accent-blue/20 text-accent-blue px-8 py-3 rounded-xl text-lg font-medium hover:bg-accent-blue/30 transition glow-blue">
            Start Free
          </Link>
          <a href="#features" className="bg-dark-700 text-white px-8 py-3 rounded-xl text-lg font-medium hover:bg-dark-600 transition border border-dark-500">
            See Features
          </a>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-5xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-6 mb-20">
        {[
          { n: '4', l: 'Analysis Lanes' },
          { n: '5', l: 'Trading Strategies' },
          { n: '3', l: 'Supported Assets' },
          { n: '∞', l: 'Free Data Sources' },
        ].map((s, i) => (
          <div key={i} className="glass rounded-xl p-6 text-center border border-dark-500">
            <div className="text-3xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">{s.n}</div>
            <div className="text-text-secondary text-sm mt-1">{s.l}</div>
          </div>
        ))}
      </section>

      {/* Features */}
      <section id="features" className="max-w-7xl mx-auto px-4 mb-20">
        <h2 className="text-3xl font-bold text-white text-center mb-12">Everything you need to trade better</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <div key={i} className="glass rounded-xl p-5 border border-dark-500 hover:border-dark-400 transition">
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2">{f.title}</h3>
              <p className="text-text-secondary text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it Works */}
      <section className="max-w-7xl mx-auto px-4 mb-20">
        <h2 className="text-3xl font-bold text-white text-center mb-12">How it works</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[
            { step: '01', title: 'Data Ingestion', desc: '10s price, 1m technical, 5m news, 10m macro — all free public APIs' },
            { step: '02', title: '4 Lanes Analyze', desc: 'Each lane generates independent bias with confidence tier' },
            { step: '03', title: 'LLM Synthesizer', desc: 'Your AI weights each lane by historical accuracy → final verdict' },
            { step: '04', title: 'Signal Generated', desc: 'Entry, SL, TP1, TP2 with ATR-based risk management' },
            { step: '05', title: 'Delivered', desc: 'Dashboard + Telegram push + WebSocket in real-time' },
          ].map((s, i) => (
            <div key={i} className="glass rounded-xl p-5 border border-dark-500 text-center">
              <div className="text-accent-blue text-2xl font-bold mb-2">{s.step}</div>
              <h3 className="text-white font-semibold mb-2">{s.title}</h3>
              <p className="text-text-secondary text-xs">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="max-w-5xl mx-auto px-4 mb-20">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Completely free</h2>
        <p className="text-text-secondary text-center mb-12">No paid tiers. No limits. Everything unlocked.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((p, i) => (
            <div key={i} className={`glass rounded-xl p-6 border ${i === 1 ? 'border-accent-blue/40 glow-blue' : 'border-dark-500'}`}>
              {i === 1 && <div className="text-accent-blue text-xs font-semibold mb-2">🔥 MOST POPULAR</div>}
              <h3 className="text-xl font-bold text-white">{p.name}</h3>
              <div className="text-3xl font-bold text-white mt-2">{p.price}<span className="text-text-secondary text-sm font-normal">/mo</span></div>
              <p className="text-text-secondary text-sm mt-1 mb-6">{p.desc}</p>
              <ul className="space-y-2 mb-8">
                {p.features.map((f, j) => (
                  <li key={j} className="text-text-secondary text-sm flex items-center gap-2">
                    <span className="text-accent-green">✓</span> {f}
                  </li>
                ))}
              </ul>
              <Link href="/signup"
                className="block text-center py-3 rounded-xl font-medium transition bg-accent-blue/20 text-accent-blue hover:bg-accent-blue/30 border border-accent-blue/30">
                Get Started Free
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-4 mb-20">
        <div className="glass rounded-2xl p-12 text-center border border-dark-500">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to trade smarter?</h2>
          <p className="text-text-secondary mb-8 max-w-lg mx-auto">Join traders using AI-powered multi-lane intelligence. No API keys needed — all data sources are free and public.</p>
          <Link href="/signup" className="bg-accent-blue/20 text-accent-blue px-8 py-3 rounded-xl text-lg font-medium hover:bg-accent-blue/30 transition glow-blue inline-block">
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-8 text-center">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white font-bold text-xs">CI</div>
            <span className="text-white font-semibold">Crypto Intel</span>
          </div>
          <p className="text-text-secondary text-xs">AI-powered trading intelligence platform. Not financial advice. Trade responsibly.</p>
          <p className="text-text-secondary text-xs mt-2">© 2026 Crypto Intel. All data from free public sources.</p>
        </div>
      </footer>
    </div>
  )
}
