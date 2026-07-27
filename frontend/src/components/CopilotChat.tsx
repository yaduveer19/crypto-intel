'use client'
import React, { useState, useRef, useEffect } from 'react'
import { copilotChat } from '@/lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function CopilotChat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Ask me anything about the market. I have live price context.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [symbol, setSymbol] = useState('BTCUSDT')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const res = await copilotChat(userMsg, symbol)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply || 'No response' }])
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: 'Service unavailable. Check backend.' }])
    }
    setLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="glass rounded-xl flex flex-col h-full" style={{ maxHeight: '500px' }}>
      <div className="flex items-center justify-between p-3 border-b border-dark-500">
        <h3 className="text-sm font-semibold text-white">🤖 AI Copilot</h3>
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="bg-dark-700 text-white text-xs rounded px-2 py-1 border border-dark-500"
        >
          <option value="BTCUSDT">BTC/USDT</option>
          <option value="ETHUSDT">ETH/USDT</option>
          <option value="SOLUSDT">SOL/USDT</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ minHeight: '200px' }}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-accent-blue/20 text-accent-blue'
                  : 'bg-dark-700 text-text-primary'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-700 rounded-lg px-3 py-2 text-sm text-text-secondary">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-3 border-t border-dark-500 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the market..."
          className="flex-1 bg-dark-700 text-white text-sm rounded-lg px-3 py-2 border border-dark-500 focus:outline-none focus:border-accent-blue/50"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-accent-blue/20 text-accent-blue px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-blue/30 disabled:opacity-40 transition"
        >
          Send
        </button>
      </div>
    </div>
  )
}
