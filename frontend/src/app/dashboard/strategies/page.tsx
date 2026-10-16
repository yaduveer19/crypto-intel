'use client'
import React, { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { compileStrategy, getStrategyTemplates, runBacktest } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
const LAB_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT']
const LAB_TFS = ['15m', '1h', '4h', '1d']

const opLabel: Record<string, string> = {
  gt: '>', lt: '<', gt_eq: '≥', lt_eq: '≤', cross_above: 'crosses above',
  cross_below: 'crosses below', gt_ema: '> EMA', lt_ema: '< EMA',
}

const ruleText = (r: any) => {
  const ind = `${r.ind}${r.period ? `(${r.period})` : ''}`
  if (r.op === 'gt_ema' || r.op === 'lt_ema') return `${ind} ${opLabel[r.op]} EMA${r.val}`
  return `${ind} ${opLabel[r.op] || r.op} ${r.val}`
}

interface Strategy {
  key: string
  name: string
  description: string
  default_params: Record<string, any>
}

interface UserStrat {
  id: number
  strategy_key: string
  name: string
  description: string
  symbol: string
  is_enabled: boolean
  params: Record<string, any>
}

export default function StrategiesPage() {
  const { token } = useAuth()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [userStrats, setUserStrats] = useState<UserStrat[]>([])
  const [loading, setLoading] = useState(true)
  const [configuring, setConfiguring] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  // Strategy Lab
  const [labText, setLabText] = useState('')
  const [labRules, setLabRules] = useState<any>(null)
  const [labMeta, setLabMeta] = useState<{ source?: string; name?: string }>({})
  const [labSymbol, setLabSymbol] = useState('BTCUSDT')
  const [labTf, setLabTf] = useState('1h')
  const [templates, setTemplates] = useState<any[]>([])
  const [bt, setBt] = useState<any>(null)
  const [labBusy, setLabBusy] = useState(false)
  const [labMsg, setLabMsg] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchData = async () => {
    try {
      const [s, u] = await Promise.all([
        fetch(`${API}/api/strategies/list`, { headers }).then(r => r.json()),
        fetch(`${API}/api/strategies/my`, { headers }).then(r => r.json()),
      ])
      setStrategies(Array.isArray(s) ? s : [])
      setUserStrats(Array.isArray(u) ? u : [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { if (token) fetchData() }, [token])

  const configure = async (strategyKey: string, symbol: string, isEnabled: boolean) => {
    setConfiguring(strategyKey)
    setMsg('')
    try {
      const r = await fetch(`${API}/api/strategies/configure`, {
        method: 'POST', headers,
        body: JSON.stringify({ strategy_key: strategyKey, symbol, is_enabled: isEnabled }),
      })
      const d = await r.json()
      setMsg(d.message || 'Configured')
      fetchData()
    } catch (e: any) {
      setMsg('Failed: ' + e.message)
    }
    setConfiguring(null)
  }

  const runAll = async () => {
    setMsg('Running all strategies...')
    try {
      const r = await fetch(`${API}/api/strategies/run-all`, { method: 'POST', headers })
      const d = await r.json()
      setMsg(`${d.signals_generated || 0} signals generated!`)
      fetchData()
    } catch (e: any) {
      setMsg('Error: ' + e.message)
    }
  }

  const isEnabled = (key: string, sym: string) => userStrats.some(u => u.strategy_key === key && u.symbol === sym && u.is_enabled)

  useEffect(() => {
    getStrategyTemplates().then(d => setTemplates(Array.isArray(d?.templates) ? d.templates : [])).catch(() => {})
  }, [])

  const doBacktest = async (rules: any, meta: { source?: string; name?: string }) => {
    setLabBusy(true)
    setLabMsg('')
    setBt(null)
    try {
      const merged = { ...rules, tf: labTf }
      const r = await runBacktest(labSymbol, merged, 400)
      if (r?.error) { setLabMsg('❌ ' + r.error); setLabRules(merged); setLabMeta(meta); return }
      setLabRules(merged)
      setLabMeta(meta)
      setBt(r)
      const s = r?.stats || {}
      setLabMsg(`Backtest done: ${s.trades ?? 0} trades · ${s.win_rate ?? 0}% win · net ${s.net_pnl_pct ?? 0}%`)
    } catch (e: any) {
      setLabMsg('❌ Backtest failed: ' + (e?.message || ''))
    }
    setLabBusy(false)
  }

  const doCompile = async () => {
    if (!labText.trim()) { setLabMsg('❌ Describe your strategy first'); return }
    setLabBusy(true)
    setLabMsg('Compiling…')
    try {
      const r = await compileStrategy(labText)
      if (!r?.rules?.entry?.length) { setLabMsg('❌ Could not extract entry rules — try being more specific (e.g. "RSI below 30")'); setLabBusy(false); return }
      await doBacktest(r.rules, { source: r.source })
    } catch (e: any) {
      setLabMsg('❌ Compile failed: ' + (e?.message || ''))
      setLabBusy(false)
    }
  }

  const useTemplate = async (t: any) => {
    setLabText(t.description || t.name || '')
    if (t.rules) await doBacktest(t.rules, { source: 'template', name: t.name })
  }

  const eq = Array.isArray(bt?.equity_curve) ? bt.equity_curve : []
  const eqVals = eq.map((p: any) => Number(p.equity)).filter((n: number) => !isNaN(n))
  const eqMin = eqVals.length ? Math.min(...eqVals) : 0
  const eqMax = eqVals.length ? Math.max(...eqVals) : 1
  const eqSpan = eqMax - eqMin || 1
  const netCls = (n: number) => n >= 0 ? 'text-accent-green' : 'text-accent-red'

  if (loading) return <div className="text-text-secondary animate-pulse">Loading strategies...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Trading Strategies</h1>
        <button onClick={runAll} className="bg-accent-purple/20 text-accent-purple px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-purple/30 transition">
          Run All Strategies
        </button>
      </div>

      {msg && <div className="bg-dark-700/50 border border-dark-500 rounded-lg px-4 py-2 text-sm text-text-secondary">{msg}</div>}

      <div className="grid gap-4">
        {strategies.map((strat) => (
          <div key={strat.key} className="glass rounded-xl p-5 border border-dark-500">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-white font-semibold text-lg">{strat.name}</h3>
                <p className="text-text-secondary text-sm">{strat.description}</p>
              </div>
            </div>

            <div className="text-xs text-text-secondary mb-3">Default params: {JSON.stringify(strat.default_params)}</div>

            <div className="grid grid-cols-3 gap-3">
              {SYMBOLS.map(sym => {
                const enabled = isEnabled(strat.key, sym)
                return (
                  <button key={sym}
                    onClick={() => configure(strat.key, sym, !enabled)}
                    disabled={configuring === strat.key}
                    className={`p-3 rounded-lg border text-sm font-medium transition ${
                      enabled
                        ? 'bg-accent-green/10 text-accent-green border-accent-green/30'
                        : 'bg-dark-700 text-text-secondary border-dark-500 hover:text-white'
                    }`}>
                    <div>{sym.replace('USDT', '')}/USDT</div>
                    <div className="text-[10px] mt-1">{enabled ? '✅ Active' : 'Click to enable'}</div>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Strategy Lab */}
      <div className="glass rounded-xl p-6 border border-dark-500">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-white font-semibold text-lg">Strategy Lab</h2>
            <p className="text-text-secondary text-sm">Describe a strategy in plain English → compiled rules → backtest on real candles</p>
          </div>
          <div className="flex gap-2">
            <select value={labSymbol} onChange={e => setLabSymbol(e.target.value)}
              className="bg-dark-700 text-white rounded-lg px-3 py-2 border border-dark-500 text-sm focus:outline-none focus:border-accent-blue/50">
              {LAB_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={labTf} onChange={e => setLabTf(e.target.value)}
              className="bg-dark-700 text-white rounded-lg px-3 py-2 border border-dark-500 text-sm focus:outline-none focus:border-accent-blue/50">
              {LAB_TFS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        {/* Templates */}
        <div className="flex flex-wrap gap-2 mb-3">
          {templates.map(t => (
            <button key={t.key} onClick={() => useTemplate(t)} disabled={labBusy}
              className="bg-dark-700 hover:bg-dark-600 text-text-secondary hover:text-white px-3 py-1.5 rounded-lg text-xs border border-dark-500 transition disabled:opacity-40">
              {t.name}
            </button>
          ))}
        </div>

        <textarea value={labText} onChange={e => setLabText(e.target.value)} rows={3}
          placeholder='e.g. "Buy BTC on the 4h when RSI drops below 30 and price holds the 200 EMA, target 3%, stop 2%"'
          className="w-full bg-dark-700 text-white rounded-lg px-4 py-3 border border-dark-500 text-sm focus:outline-none focus:border-accent-blue/50 placeholder:text-text-secondary/50 resize-y" />

        <div className="flex flex-wrap items-center gap-3 mt-3">
          <button onClick={doCompile} disabled={labBusy}
            className="bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30 px-5 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-40">
            {labBusy ? 'Working…' : 'Compile & Backtest'}
          </button>
          {labRules && !labBusy && (
            <button onClick={() => doBacktest(labRules, labMeta)}
              className="bg-dark-700 text-text-secondary hover:text-white px-4 py-2.5 rounded-lg text-sm border border-dark-500 transition">
              ↻ Re-run backtest
            </button>
          )}
          {labMsg && <span className="text-xs text-text-secondary">{labMsg}</span>}
        </div>

        {/* Compiled rules */}
        {labRules && (
          <div className="mt-4 bg-dark-700/50 rounded-lg p-4 border border-dark-500">
            <div className="flex items-center gap-2 mb-2 text-xs">
              <span className={`px-2 py-0.5 rounded ${labMeta.source === 'llm' ? 'bg-accent-green/15 text-accent-green' : labMeta.source === 'template' ? 'bg-accent-blue/15 text-accent-blue' : 'bg-accent-yellow/15 text-accent-yellow'}`}>
                {labMeta.source === 'llm' ? 'LLM compiled' : labMeta.source === 'template' ? `Template: ${labMeta.name}` : 'Keyword fallback'}
              </span>
              <span className="text-text-secondary">{labRules.tf} · {String(labRules.side || 'long').toUpperCase()} · SL {labRules.sl_pct}% · TP {labRules.tp_pct}% · max {labRules.max_bars} bars</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {(labRules.entry || []).map((r: any, i: number) => (
                <span key={'e' + i} className="bg-accent-green/10 text-accent-green text-xs font-mono px-2 py-1 rounded">IF {ruleText(r)}</span>
              ))}
              {(labRules.exit || []).map((r: any, i: number) => (
                <span key={'x' + i} className="bg-accent-red/10 text-accent-red text-xs font-mono px-2 py-1 rounded">EXIT {ruleText(r)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Backtest results */}
        {bt?.stats && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              {[
                { label: 'Trades', value: String(bt.stats.trades ?? 0), cls: 'text-white' },
                { label: 'Win rate', value: `${bt.stats.win_rate ?? 0}%`, cls: 'text-white' },
                { label: 'Net PnL', value: `${bt.stats.net_pnl_pct ?? 0}%`, cls: netCls(Number(bt.stats.net_pnl_pct) || 0) },
                { label: 'Profit factor', value: bt.stats.profit_factor != null ? String(bt.stats.profit_factor) : '—', cls: 'text-white' },
                { label: 'Max DD', value: `-${bt.stats.max_drawdown_pct ?? 0}%`, cls: 'text-accent-red' },
                { label: 'Buy & hold', value: `${bt.stats.buy_hold_pct ?? 0}%`, cls: netCls(Number(bt.stats.buy_hold_pct) || 0) },
                { label: 'Final equity', value: `$${Number(bt.stats.final_equity ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, cls: 'text-accent-blue' },
              ].map(k => (
                <div key={k.label} className="bg-dark-700/60 rounded-lg p-3 text-center">
                  <div className="text-[10px] text-text-secondary uppercase tracking-wider">{k.label}</div>
                  <div className={`text-sm font-bold font-mono ${k.cls}`}>{k.value}</div>
                </div>
              ))}
            </div>

            {eqVals.length > 1 && (
              <div className="bg-dark-700/40 rounded-lg p-4 border border-dark-500">
                <div className="text-xs text-text-secondary mb-2">Equity curve ({eqVals.length} bars, 10k start)</div>
                <svg viewBox="0 0 600 140" className="w-full h-36" preserveAspectRatio="none">
                  <polyline fill="none"
                    stroke={(Number(bt.stats.net_pnl_pct) || 0) >= 0 ? '#22c55e' : '#ef4444'}
                    strokeWidth="1.5"
                    points={eqVals.map((v: number, i: number) =>
                      `${(i / (eqVals.length - 1)) * 598 + 1},${136 - ((v - eqMin) / eqSpan) * 130}`).join(' ')} />
                  <line x1="0" y1={136 - ((10000 - eqMin) / eqSpan) * 130} x2="600" y2={136 - ((10000 - eqMin) / eqSpan) * 130}
                    stroke="#4b5563" strokeDasharray="4 4" strokeWidth="1" />
                </svg>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-text-secondary text-xs uppercase tracking-wider border-b border-dark-500">
                    <th className="text-left py-2">Entry</th>
                    <th className="text-right py-2">Entry px</th>
                    <th className="text-right py-2">Exit px</th>
                    <th className="text-right py-2">PnL</th>
                    <th className="text-right py-2">Bars</th>
                    <th className="text-right py-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(bt.trades || []).slice(-15).map((t: any, i: number) => (
                    <tr key={i} className="border-b border-dark-600/50">
                      <td className="py-2 text-text-secondary">{new Date(Number(t.entry_time) * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' })}</td>
                      <td className="py-2 text-right font-mono text-white">${Number(t.entry_price).toLocaleString()}</td>
                      <td className="py-2 text-right font-mono text-white">${Number(t.exit_price).toLocaleString()}</td>
                      <td className={`py-2 text-right font-mono font-semibold ${netCls(Number(t.pnl_pct) || 0)}`}>{Number(t.pnl_pct) >= 0 ? '+' : ''}{t.pnl_pct}%</td>
                      <td className="py-2 text-right text-text-secondary">{t.bars}</td>
                      <td className={`py-2 text-right text-xs ${t.reason === 'TARGET' ? 'text-accent-green' : t.reason === 'STOP' ? 'text-accent-red' : 'text-accent-yellow'}`}>{t.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(bt.trades || []).length === 0 && <p className="text-text-secondary text-sm mt-3">No trades fired — entry rules never triggered in this window. Loosen the conditions or widen the timeframe.</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
