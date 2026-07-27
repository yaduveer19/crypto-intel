'use client'
import React, { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const { login } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center px-4">
      <div className="glass rounded-2xl p-8 w-full max-w-md border border-dark-500">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white font-bold text-lg mx-auto mb-3">CI</div>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-text-secondary text-sm mt-1">Sign in to your Crypto Intel account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-text-secondary block mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
              className="w-full bg-dark-700 text-white rounded-lg px-4 py-3 border border-dark-500 focus:outline-none focus:border-accent-blue/50" placeholder="you@example.com" />
          </div>
          <div>
            <label className="text-sm text-text-secondary block mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full bg-dark-700 text-white rounded-lg px-4 py-3 border border-dark-500 focus:outline-none focus:border-accent-blue/50" placeholder="••••••••" />
          </div>

          {error && <p className="text-accent-red text-sm">{error}</p>}

          <button type="submit" disabled={loading}
            className="w-full bg-accent-blue/20 text-accent-blue py-3 rounded-lg font-medium hover:bg-accent-blue/30 transition disabled:opacity-40">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-sm text-text-secondary mt-6">
          Don&apos;t have an account? <a href="/signup" className="text-accent-blue hover:underline">Sign up</a>
        </p>
        <p className="text-center text-xs text-text-secondary mt-3">
          <a href="/" className="hover:text-white">← Back to home</a>
        </p>
      </div>
    </div>
  )
}
