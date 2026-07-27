const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'

async function fetchJSON(url: string) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getVerdict(symbol: string) {
  return fetchJSON(`${API}/api/verdict/${symbol}`)
}

export async function getLanes(symbol: string) {
  return fetchJSON(`${API}/api/lanes/${symbol}`)
}

export async function getPrice(symbol: string) {
  return fetchJSON(`${API}/api/price/${symbol}`)
}

export async function getSignalHistory(symbol: string, limit = 50) {
  return fetchJSON(`${API}/api/signals/history?symbol=${symbol}&limit=${limit}`)
}

export async function copilotChat(message: string, symbol = 'BTCUSDT') {
  const res = await fetch(`${API}/api/copilot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, symbol }),
  })
  return res.json()
}

export async function runSimulation(symbol: string, shockPct: number, portfolioValue = 10000) {
  const res = await fetch(`${API}/api/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, shock_pct: shockPct, portfolio_value: portfolioValue }),
  })
  return res.json()
}

export function createWebSocket(onMessage: (data: any) => void) {
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let isClosed = false

  function connect() {
    if (isClosed) return
    ws = new WebSocket(WS)

    ws.onopen = () => {
      console.log('[ws] connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {}
    }

    ws.onclose = () => {
      if (!isClosed) {
        reconnectTimer = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  connect()

  return {
    close: () => {
      isClosed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    },
    send: (data: any) => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data))
      }
    },
  }
}

// Server-side price streaming mock (Binance public WS for direct frontend use)
export function createBinanceWebSocket(symbol: string, onPrice: (price: number) => void) {
  const stream = symbol.toLowerCase().replace('usdt', 'usdt@trade')
  const url = `wss://stream.binance.com:9443/ws/${stream}`
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let isClosed = false

  function connect() {
    if (isClosed) return
    ws = new WebSocket(url)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.p) onPrice(parseFloat(data.p))
      } catch {}
    }

    ws.onclose = () => {
      if (!isClosed) {
        reconnectTimer = setTimeout(connect, 5000)
      }
    }

    ws.onerror = () => ws?.close()
  }

  connect()

  return {
    close: () => {
      isClosed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    },
  }
}
