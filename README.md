# Crypto Intel — Multi-Exchange Trading Intelligence Platform

AI-powered crypto market intelligence: live multi-exchange data, microstructure metrics (CVD, VWAP, order-flow), 9 trading strategies, real-time signals, AI Copilot, market scanner, and shock simulation.

## Features

- **Live Market Data** — BTC/ETH/SOL from 5 exchanges (Binance, ByBit, OKX, Deribit, Hyperliquid) via ccxt, with Hyperliquid WebSocket bridge
- **Microstructure Metrics** — CVD (Cumulative Volume Delta), VWAP, volume profile, order-flow footprint, order-book heatmap, top-of-book
- **9 Real Strategies** — Trend Following, RSI Mean Reversion, MACD Momentum, Breakout, Grid Levels + 4 scalping strategies (VWAP Reversion, Opening Range Breakout, CVD Divergence, Order Flow Momentum)
- **Live Signals** — every signal runs the real strategy engine against live klines
- **AI Copilot** — LLM-powered chat with live price context + "Analyze All Markets" scanner
- **Live Dashboard** — 2-second streaming market feed (price, 24h change, funding, CVD, VWAP) with real-time verdicts
- **Shock Simulator** — portfolio impact scenarios
- **No login required** — dashboard opens directly (login bypass for local dev)

## Quick Start (Windows)

### One command:

```bat
start_services.bat
```

This starts 3 windows:
| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend (mock server, no Docker needed) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| HL Bridge (optional) | ws://localhost:8765 |
| Market WebSocket | ws://localhost:8000/ws/market |

### Manual start:

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements-mock.txt     # light setup, no Docker needed
python mock_server.py                    # port 8000

# Terminal 2 — optional HL bridge
python hl_bridge.py 8765

# Terminal 3 — frontend
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

## Requirements

- Python 3.11+ (`pip install -r backend/requirements-mock.txt` — light, no Docker needed)
- Node.js 18+ / 20+ (`npm install` in frontend)
- Docker NOT required — the mock server runs standalone. `docker-compose.yml` exists for the full-stack (Postgres/Redis) deployment.
- No `.env` needed — everything works out of the box (LLM key is bundled for the Copilot).

## API Endpoints

- `GET /api/verdict/{symbol}` — real strategy-engine verdict (bias, tier, entry/SL/TP, reasoning)
- `GET /api/lanes/{symbol}` — multi-lane analysis
- `GET /api/price/{symbol}` — live price
- `GET /api/klines/{symbol}`, `/api/orderbook/{symbol}`, `/api/cvd/{symbol}`, `/api/volume-profile/{symbol}`, `/api/footprint/{symbol}`, `/api/orderbook-heatmap/{symbol}`
- `GET /api/strategies/list` — 9 registered strategies
- `POST /api/strategies/run-all` — run every strategy on every symbol (real klines)
- `GET /api/strategies/signals` — latest real signals
- `POST /api/copilot` — AI chat with price context
- `POST /api/copilot/analyze` — analyze all markets (LLM + snapshot)
- `POST /api/simulate` — portfolio shock simulation
- `WS /ws/market` — live stream every 2s: `{type:"market", data:[{symbol, price, change_24h_pct, funding, cvd, vwap, best_bid, best_ask}]}`
- `WS /ws` — live verdict stream

## Project Structure

```
backend/
  mock_server.py            # standalone server (no Docker)
  hl_bridge.py              # Hyperliquid WS bridge (:8765)
  app/exchange/             # ccxt REST + live WS + aggregator with live→simulated failover
  app/metrics/              # CVD, volume profile, footprint, heatmap
  app/strategies/           # strategy engine + 9 strategies
  app/strategies/scalping/  # 4 scalping strategies
frontend/
  src/app/                  # Next.js pages (dashboard, market, signals, strategies, settings)
  src/components/           # CandlestickChart, OrderbookPanel, CVDChart, VolumeProfile, Footprint, Copilot, Scanner...
  src/lib/api.ts            # API + WebSocket client
```

## Environment

`.env` (root) holds LLM key and API URLs. Defaults work out of the box:
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` — AI Copilot
- `NEXT_PUBLIC_API_URL=http://localhost:8000` — frontend → backend

## Tech Stack

Next.js 14 (App Router) · FastAPI · ccxt · Hyperliquid WS · Plotly/D3 charts · TailwindCSS

---

⚠️ For educational purposes. Not financial advice. DYOR.
