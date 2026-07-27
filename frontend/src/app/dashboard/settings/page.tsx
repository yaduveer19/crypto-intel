'use client'
import React, { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SettingsPage() {
  const { token, user } = useAuth()
  const [botToken, setBotToken] = useState('')
  const [chatId, setChatId] = useState('')
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  useEffect(() => {
    if (!token) return
    fetch(`${API}/api/telegram/status`, { headers })
      .then(r => r.json()).then(d => {
        setConnected(d.connected || false)
        if (d.chat_id) setChatId(d.chat_id)
      }).catch(() => {}).finally(() => setLoading(false))
  }, [token])

  const connectTelegram = async () => {
    if (!botToken || !chatId) { setMsg('Enter both Bot Token and Chat ID'); return }
    setSaving(true)
    setMsg('')
    try {
      const r = await fetch(`${API}/api/telegram/connect`, {
        method: 'POST', headers,
        body: JSON.stringify({ bot_token: botToken, chat_id: chatId }),
      })
      const d = await r.json()
      if (r.ok) { setConnected(true); setMsg('✅ Telegram connected! Check your Telegram for test message.') }
      else { setMsg('❌ ' + (d.detail || 'Failed')) }
    } catch (e: any) { setMsg('❌ ' + e.message) }
    setSaving(false)
  }

  const disconnectTelegram = async () => {
    try {
      await fetch(`${API}/api/telegram/disconnect`, { method: 'POST', headers })
      setConnected(false)
      setMsg('Telegram disconnected')
    } catch {}
  }

  if (loading) return <div className="text-text-secondary animate-pulse">Loading settings...</div>

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
        <p className="text-text-secondary text-sm">Manage your account and alert connections</p>
      </div>

      {/* Profile */}
      <div className="glass rounded-xl p-6 border border-dark-500">
        <h2 className="text-lg font-semibold text-white mb-4">Profile</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between"><span className="text-text-secondary">Name</span><span className="text-white">{user?.name || '—'}</span></div>
          <div className="flex justify-between"><span className="text-text-secondary">Email</span><span className="text-white">{user?.email}</span></div>
          <div className="flex justify-between"><span className="text-text-secondary">Plan</span><span className="text-accent-blue uppercase">{user?.plan || 'free'}</span></div>
        </div>
      </div>

      {/* Telegram */}
      <div className="glass rounded-xl p-6 border border-dark-500">
        <h2 className="text-lg font-semibold text-white mb-4">📱 Telegram Alerts</h2>
        <p className="text-text-secondary text-sm mb-4">
          Connect your Telegram bot to receive trade signals directly to your phone.
          Create a bot via <a href="https://t.me/BotFather" target="_blank" className="text-accent-blue hover:underline">@BotFather</a>,
          get your Chat ID from <a href="https://t.me/userinfobot" target="_blank" className="text-accent-blue hover:underline">@userinfobot</a>.
        </p>

        {connected ? (
          <div className="space-y-3">
            <div className="bg-accent-green/10 text-accent-green px-4 py-3 rounded-lg text-sm border border-accent-green/20">
              ✅ Telegram connected — alerts are active
            </div>
            <button onClick={disconnectTelegram} className="text-accent-red text-sm hover:underline">Disconnect</button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-text-secondary block mb-1">Bot Token</label>
              <input value={botToken} onChange={e => setBotToken(e.target.value)}
                className="w-full bg-dark-700 text-white rounded-lg px-4 py-3 border border-dark-500 focus:outline-none focus:border-accent-blue/50 text-sm font-mono"
                placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" />
            </div>
            <div>
              <label className="text-sm text-text-secondary block mb-1">Chat ID</label>
              <input value={chatId} onChange={e => setChatId(e.target.value)}
                className="w-full bg-dark-700 text-white rounded-lg px-4 py-3 border border-dark-500 focus:outline-none focus:border-accent-blue/50 text-sm font-mono"
                placeholder="-1001234567890" />
            </div>
            {msg && <div className="text-sm text-text-secondary">{msg}</div>}
            <button onClick={connectTelegram} disabled={saving}
              className="bg-accent-blue/20 text-accent-blue px-6 py-3 rounded-lg font-medium hover:bg-accent-blue/30 transition disabled:opacity-40">
              {saving ? 'Connecting...' : 'Connect Telegram'}
            </button>
          </div>
        )}
      </div>

      {/* How to get Telegram Bot Token */}
      <div className="glass rounded-xl p-6 border border-dark-500">
        <h2 className="text-lg font-semibold text-white mb-3">How to set up Telegram</h2>
        <ol className="space-y-2 text-sm text-text-secondary list-decimal list-inside">
          <li>Open Telegram and search for <span className="text-white font-mono">@BotFather</span></li>
          <li>Send <span className="text-white font-mono">/newbot</span> and follow instructions to create a bot</li>
          <li>Copy the bot token (looks like <span className="text-white font-mono">123456:ABCdef...</span>)</li>
          <li>Search for <span className="text-white font-mono">@userinfobot</span> and send <span className="text-white font-mono">/start</span></li>
          <li>Copy your Chat ID (looks like <span className="text-white font-mono">-1001234567890</span> or <span className="text-white font-mono">123456789</span>)</li>
          <li>Paste both above and click Connect — test message will be sent instantly</li>
        </ol>
      </div>
    </div>
  )
}
