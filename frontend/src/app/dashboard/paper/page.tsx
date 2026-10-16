'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { getPaperState, paperOpen, paperClose, paperReset, simulateScenario } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

const fmtUsd = (p?: number | null) =>
  p === null || p === undefined || isNaN(Number(p)) ? '—' : `$${Number(p).toLocaleString(undefined, { maximumFractionDigits: 2 })}`

const pnlCls = (p?: number | null) =>
  p === null || p === undefined ? 'text-text-secondary' : Number(p) >= 0 ? 'text-accent-green' : 'text-accent-red'

export default function PaperPage() {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [side, setSide] = useState<'long' | 'short'>('long')
  const [usd, setUsd] = useState('500')
  const [busy, setBusy] = useState(false)
  const [scenario, setScenario] = useState<any>(null)
  const [scenBusy, setScenBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const s = await getPaperState()
      setState(s)
      setErr('')
    } catch (e: any) {
      setErr('Cannot reach paper engine: ' + (e?.message || ''))
    }
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(''), 6000) }

  const open = async () => {
    const amt = parseFloat(usd)
    if (!amt || amt <= 0) { flash('❌ Enter a valid USD size'); return }
    if (amt > (state?.balance || 0)) { flash('❌ Amount exceeds balance'); return }
    setBusy(true)
    try {
      const r = await paperOpen(symbol, side, amt)
      if (r?.error) flash('❌ ' + r.error)
      else if (r?.position) flash(`✅ Opened ${side.toUpperCase()} ${symbol}: ${fmtUsd(amt)} @ ${fmtUsd(r.position.entry)}`)
      await refresh()
    } catch (e: any) { flash('❌ ' + (e?.message || 'failed')) }
    setBusy(false)
  }

  const close = async (id: string) => {
    setBusy(true)
    try {
      const r = await paperClose(id)
      if (r?.error) flash('❌ ' + r.error)
      else if (r?.pnl !== undefined) flash(`Closed @ ${fmtUsd(r.exit)} — PnL ${fmtUsd(r.pnl)} (${r.pnl_pct ?? 0}%)`)
      await refresh()
    } catch (e: any) { flash('❌ ' + (e?.message || 'failed')) }
    setBusy(false)
  }

  const reset = async () => {
    if (!confirm('Reset paper account to $10,000? All positions and history will be wiped.')) return
    setBusy(true)
    try { await paperReset(); await refresh(); flash('Account reset to $10,000') } catch {}
    setBusy(false)
  }

  const runScenario = async () => {
    setScenBusy(true)
    try { setScenario(await simulateScenario()) }
    catch (e: any) { flash('❌ Scenario failed: ' + (e?.message || '')) }
    setScenBusy(false)
  }

  if (loading && !state) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-56 bg-dark-600 rounded animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">{[0,1,2,3].map(i => <div key={i} className="h-24 bg-dark-700 rounded-xl animate-pulse" />)}</div>
        <div className="h-64 bg-dark-700 rounded-xl animate-pulse" />
      </div>
    )
  }

  const positions = Array.isArray(state?.positions) ? state.positions : []
  const history = Array.isArray(state?.history) ? state.history : []
  const wins = history.filter((h: any) => Number(h.pnl) > 0).length
  const winRate = history.length ? Math.round(wins / history.length * 100) : null
  const totalPnl = history.reduce((a: number, h: any) => a + (Number(h.pnl) || 0), 0)
  const openPnl = positions.reduce((a: number, p: any) => a + (Number(p.upnl) || 0), 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Paper Trading</h1>
          <p className="text-text-secondary text-sm">Virtual account — live prices, zero risk</p>
        </div>
        <div className="flex gap-2">
          <button onClick={runScenario} disabled={scenBusy}
            className="bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-40">
            {scenBusy ? 'Simulating…' : '⚡ Scenario shock sim'}
          </button>
          <button onClick={reset} disabled={busy}
            className="bg-accent-red/10 text-accent-red hover:bg-accent-red/20 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-40">
            Reset
          </button>
        </div>
      </div>

      {err && <div className="bg-accent-red/10 border border-accent-red/30 text-accent-red rounded-lg px-4 py-2 text-sm">{err}</div>}
      {msg && <div className="bg-dark-700/60 border border-dark-500 text-text-secondary rounded-lg px-4 py-2 text-sm">{msg}</div>}

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Balance', value: fmtUsd(state?.balance), cls: 'text-white' },
          { label: 'Equity (live)', value: fmtUsd(state?.equity), cls: 'text-accent-blue' },
          { label: 'Unrealized PnL', value: positions.length ? fmtUsd(openPnl) : fmtUsd(0), cls: pnlCls(openPnl) },
          { label: 'Realized / Win rate', value: `${fmtUsd(totalPnl)}${winRate !== null ? ` · ${winRate}%` : ''}`, cls: pnlCls(totalPnl) },
        ].map(k => (
          <div key={k.label} className="glass rounded-xl p-4 border border-dark-500">
            <div className="text-[10px] text-text-secondary uppercase tracking-wider">{k.label}</div>
            <div className={`text-xl font-bold font-mono ${k.cls}`}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Open form */}
      <div className="glass rounded-xl p-5 border border-dark-500">
        <h2 className="text-white font-semibold mb-4">Open position</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs text-text-secondary block mb-1">Symbol</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)}
              className="bg-dark-700 text-white rounded-lg px-3 py-2.5 border border-dark-500 text-sm focus:outline-none focus:border-accent-blue/50">
              {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Side</label>
            <div className="flex bg-dark-700 rounded-lg border border-dark-500 p-1">
              {(['long', 'short'] as const).map(sd => (
                <button key={sd} onClick={() => setSide(sd)}
                  className={`px-4 py-1.5 rounded text-sm font-medium transition ${side === sd ? (sd === 'long' ? 'bg-accent-green/25 text-accent-green' : 'bg-accent-red/25 text-accent-red') : 'text-text-secondary hover:text-white'}`}>
                  {sd.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Size (USD)</label>
            <input value={usd} onChange={e => setUsd(e.target.value)} inputMode="decimal"
              className="bg-dark-700 text-white rounded-lg px-3 py-2.5 border border-dark-500 text-sm font-mono w-28 focus:outline-none focus:border-accent-blue/50" />
          </div>
          <button onClick={open} disabled={busy}
            className="bg-accent-blue/20 text-accent-blue hover:bg-accent-blue/30 px-5 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-40">
            {busy ? 'Working…' : 'Open trade'}
          </button>
        </div>
      </div>

      {/* Open positions */}
      <div className="glass rounded-xl p-5 border border-dark-500">
        <h2 className="text-white font-semibold mb-4">Open positions ({positions.length})</h2>
        {positions.length === 0 ? (
          <p className="text-text-secondary text-sm">No open positions. Open one above or from the Analyze page.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs uppercase tracking-wider border-b border-dark-500">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Side</th>
                  <th className="text-right py-2">Size</th>
                  <th className="text-right py-2">Entry</th>
                  <th className="text-right py-2">Mark</th>
                  <th className="text-right py-2">PnL</th>
                  <th className="text-right py-2" />
                </tr>
              </thead>
              <tbody>
                {positions.map((p: any) => (
                  <tr key={p.id} className="border-b border-dark-600/50">
                    <td className="py-2.5 text-white font-medium">{p.symbol}</td>
                    <td className={`py-2.5 font-semibold ${p.side === 'long' ? 'text-accent-green' : 'text-accent-red'}`}>{String(p.side).toUpperCase()}</td>
                    <td className="py-2.5 text-right font-mono text-text-secondary">{fmtUsd(p.cost_usd)}</td>
                    <td className="py-2.5 text-right font-mono text-white">{fmtUsd(p.entry)}</td>
                    <td className="py-2.5 text-right font-mono text-accent-blue">{fmtUsd(p.mark)}</td>
                    <td className={`py-2.5 text-right font-mono ${pnlCls(p.upnl)}`}>{fmtUsd(p.upnl)}</td>
                    <td className="py-2.5 text-right">
                      <button onClick={() => close(p.id)} disabled={busy}
                        className="bg-accent-red/15 text-accent-red hover:bg-accent-red/25 px-3 py-1 rounded text-xs font-medium transition disabled:opacity-40">
                        Close
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Scenario results */}
      {scenario && (
        <div className="glass rounded-xl p-5 border border-dark-500">
          <h2 className="text-white font-semibold mb-1">⚡ Scenario shock simulation</h2>
          <p className="text-text-secondary text-xs mb-4">
            {scenario.open_positions ?? 0} open position(s) · reference price {scenario.reference_price ? `$${scenario.reference_price.toLocaleString()}` : '—'}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(scenario.grid || []).map((g: any) => (
              <div key={g.shock_pct} className={`rounded-lg p-3 border ${
                (g.sl_triggers && g.sl_triggers.length) ? 'bg-accent-red/10 border-accent-red/30'
                : g.equity_change_pct >= 0 ? 'bg-accent-green/5 border-dark-500' : 'bg-dark-700/60 border-dark-500'}`}>
                <div className={`text-lg font-bold font-mono ${g.equity_change_pct >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {g.shock_pct > 0 ? '+' : ''}{g.shock_pct}%
                </div>
                <div className="text-xs text-text-secondary mt-1">Equity {fmtUsd(g.equity_after)}</div>
                <div className="text-xs text-text-secondary">PnL {fmtUsd(g.positions_pnl)}</div>
                {!!(g.sl_triggers || []).length && (
                  <div className="text-[10px] text-accent-red mt-1">SL hit: {g.sl_triggers.map((t: any) => t?.symbol || t).join(', ')}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      <div className="glass rounded-xl p-5 border border-dark-500">
        <h2 className="text-white font-semibold mb-4">Trade history ({history.length})</h2>
        {history.length === 0 ? (
          <p className="text-text-secondary text-sm">No closed trades yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary text-xs uppercase tracking-wider border-b border-dark-500">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Side</th>
                  <th className="text-right py-2">Entry</th>
                  <th className="text-right py-2">Exit</th>
                  <th className="text-right py-2">PnL</th>
                  <th className="text-right py-2">Closed</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().slice(0, 25).map((h: any, i: number) => (
                  <tr key={i} className="border-b border-dark-600/50">
                    <td className="py-2.5 text-white">{h.symbol}</td>
                    <td className={`py-2.5 font-semibold ${h.side === 'long' ? 'text-accent-green' : 'text-accent-red'}`}>{String(h.side || '').toUpperCase()}</td>
                    <td className="py-2.5 text-right font-mono text-text-secondary">{fmtUsd(h.entry)}</td>
                    <td className="py-2.5 text-right font-mono text-white">{fmtUsd(h.close ?? h.exit)}</td>
                    <td className={`py-2.5 text-right font-mono font-semibold ${pnlCls(h.pnl)}`}>{fmtUsd(h.pnl)}</td>
                    <td className="py-2.5 text-right text-text-secondary text-xs">{h.closed_at ? new Date(Number(h.closed_at) * 1000).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
