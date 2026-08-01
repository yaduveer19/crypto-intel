# Standalone mock server — no Docker, no DB, no Redis needed
# python mock_server.py

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json, random, math, asyncio, uuid, sys, os, time
from datetime import datetime, timezone
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.exchange.aggregator import aggregator
from app.metrics.engine import build_all
from app.strategies.engine import get_all_strategies, get_strategy, StrategyResult
import app.strategies.scalping  # registers scalping strategies
import app.strategies  # registers classic strategies

app = FastAPI(title="Crypto Intel v4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
PRICES = {"BTCUSDT": 67500, "ETHUSDT": 3450, "SOLUSDT": 145}
EXCHANGES = ["binance", "bybit", "okx", "deribit", "hyperliquid"]

# ─── Mock Users ──────────────────────────────────────────────────────────────
mock_users = {}
mock_tokens = {}

def gen_price(base): return round(base * (1 + (random.random() - 0.5) * 0.004), 2)
def fake_token(): return "mock-jwt-" + str(uuid.uuid4())

STRATEGIES = [
    {"key": "trend_following", "name": "Trend Following", "description": "EMA crossover trend strategy — buy when fast EMA crosses above slow EMA", "default_params": {"fast_period": 9, "slow_period": 21, "atr_multiplier_sl": 2.0, "atr_multiplier_tp": 3.0}},
    {"key": "rsi_mean_reversion", "name": "RSI Mean Reversion", "description": "Buy oversold, sell overbought — RSI-based mean reversion", "default_params": {"rsi_period": 14, "oversold": 30, "overbought": 70}},
    {"key": "macd_momentum", "name": "MACD Momentum", "description": "MACD line vs signal line crossovers with histogram confirmation", "default_params": {"fast": 12, "slow": 26, "signal": 9}},
    {"key": "breakout", "name": "Breakout", "description": "Bollinger Band breakout — price breaking above/below bands with volume", "default_params": {"band_period": 20, "band_std": 2.0}},
    {"key": "grid_levels", "name": "Grid Levels", "description": "Support/resistance grid — identifies key levels for range trading", "default_params": {"lookback": 50, "grid_levels": 5}},
    {"key": "vwap_reversion", "name": "VWAP Reversion (Scalp)", "description": "Fade extremes back to VWAP with volume confirmation", "default_params": {"deviation": 0.0025, "atr_multiplier_sl": 1.2, "atr_multiplier_tp": 1.8}},
    {"key": "opening_range_breakout", "name": "Opening Range Breakout (Scalp)", "description": "Break of the session opening range with volume = momentum trade", "default_params": {"range_minutes": 15, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.5}},
    {"key": "cvd_divergence", "name": "CVD Divergence (Scalp)", "description": "Price vs cumulative volume delta divergence — smart money moves", "default_params": {"lookback": 30, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.5}},
    {"key": "order_flow_momentum", "name": "Order Flow Momentum (Scalp)", "description": "Tape aggression ratio and delta bars for momentum entries", "default_params": {"aggression_threshold": 0.55, "atr_multiplier_sl": 1.2, "atr_multiplier_tp": 2.0}},
]

def gen_verdict(sym):
    """Real verdict — runs ALL registered strategies on live klines, synthesizes consensus."""
    price = PRICES.get(sym, 50000)
    try:
        klines = aggregator.get_klines(sym, timeframe="1m", limit=100)
        if not klines or len(klines) < 20:
            return {"bias": "NEUTRAL", "tier": "LOW", "entry_price": price,
                    "stop_loss": round(price * 0.98, 2), "tp1": round(price * 1.02, 2), "tp2": round(price * 1.04, 2),
                    "reasoning": "Not enough kline data yet."}
        results = []
        for s in get_all_strategies():
            try:
                strat = get_strategy(s["key"])
                r = strat.analyze(sym, klines, params=None)
                if r and r.bias != "NEUTRAL":
                    results.append(r)
            except Exception:
                continue
        if not results:
            # market stats fallback — trend + flow read
            closes = [k["close"] for k in klines]
            ema_fast = sum(closes[-9:]) / 9
            ema_slow = sum(closes[-21:]) / 21
            bias = "BULL" if ema_fast > ema_slow else ("BEAR" if ema_fast < ema_slow else "NEUTRAL")
            atr = price * 0.02
            return {"bias": bias, "tier": "MOD", "entry_price": price,
                    "stop_loss": round(price - atr * 2 if bias == "BULL" else price + atr * 2, 2),
                    "tp1": round(price + atr * 3 if bias == "BULL" else price - atr * 3, 2),
                    "tp2": round(price + atr * 6 if bias == "BULL" else price - atr * 6, 2),
                    "reasoning": f"EMA trend read: {'uptrend' if bias=='BULL' else 'downtrend'} on 9/21. No strategy triggered — momentum baseline."}
        bulls = sum(1 for r in results if r.bias == "BULL")
        bears = sum(1 for r in results if r.bias == "BEAR")
        bias = "BULL" if bulls > bears else ("BEAR" if bears > bulls else "NEUTRAL")
        best = max(results, key=lambda r: 2 if r.tier == "HIGH" else 1 if r.tier == "MOD" else 0)
        tier = "HIGH" if best.tier == "HIGH" or len(results) >= 3 else ("MOD" if best.tier == "MOD" or len(results) >= 2 else "LOW")
        dirn = 1 if bias == "BULL" else -1
        entry = best.entry_price or price
        atr = abs(entry - (best.stop_loss or entry)) / (1.5 if best.tier in ("MOD", "HIGH") else 2.0) or price * 0.015
        return {
            "bias": bias, "tier": tier, "entry_price": round(entry, 2),
            "stop_loss": round(entry - atr * 2 * dirn if best.stop_loss is None else best.stop_loss, 2),
            "tp1": round(best.tp1 or entry + atr * 3 * dirn, 2),
            "tp2": round(best.tp2 or entry + atr * 6 * dirn, 2),
            "reasoning": f"{len(results)}/{len(get_all_strategies())} strategies triggered ({'BULL' if bulls else 'BEAR' if bears else 'NEUTRAL'} {bulls}-{bears}). Best: {best.tier} conviction. {best.reasoning[:80]}",
            "strategy_count": len(results),
        }
    except Exception as e:
        return {"bias": "NEUTRAL", "tier": "LOW", "entry_price": price,
                "stop_loss": round(price * 0.98, 2), "tp1": round(price * 1.02, 2), "tp2": round(price * 1.04, 2),
                "reasoning": f"Verdict engine error: {e}"}

# ─── Auth ────────────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(body: dict):
    email = body.get("email", "")
    if email in mock_users:
        raise HTTPException(400, "Email already registered")
    uid = len(mock_users) + 1
    user = {"id": uid, "email": email, "name": body.get("name", ""), "plan": "free"}
    mock_users[email] = user
    token = fake_token()
    mock_tokens[token] = user
    return {"token": token, "user": user}

@app.post("/api/auth/login")
async def login(body: dict):
    email = body.get("email", "")
    user = mock_users.get(email)
    if not user:
        user = {"id": len(mock_users) + 1, "email": email, "name": email.split("@")[0], "plan": "free"}
        mock_users[email] = user
    token = fake_token()
    mock_tokens[token] = user
    return {"token": token, "user": user}

@app.get("/api/auth/me")
async def get_me():
    return {"id": 1, "email": "demo@cryptointel.io", "name": "Demo User", "plan": "pro", "created_at": datetime.now(timezone.utc).isoformat()}

# ─── Strategies ──────────────────────────────────────────────────────────────

@app.get("/api/strategies/list")
async def list_strategies():
    return get_all_strategies()

@app.get("/api/strategies/my")
async def my_strategies():
    return [
        {"id": 1, "strategy_key": "trend_following", "name": "Trend Following", "description": "EMA crossover trend strategy", "symbol": "BTCUSDT", "is_enabled": True, "params": {"fast_period": 9, "slow_period": 21}},
        {"id": 2, "strategy_key": "rsi_mean_reversion", "name": "RSI Mean Reversion", "description": "Buy oversold, sell overbought", "symbol": "ETHUSDT", "is_enabled": True, "params": {"rsi_period": 14}},
        {"id": 3, "strategy_key": "macd_momentum", "name": "MACD Momentum", "description": "MACD crossover momentum", "symbol": "SOLUSDT", "is_enabled": False, "params": {"fast": 12}},
    ]

@app.post("/api/strategies/configure")
async def configure_strategy(body: dict):
    return {"status": "ok", "message": f"Strategy '{body.get('strategy_key')}' configured for {body.get('symbol','')}"}

@app.post("/api/strategies/run-all")
async def run_all():
    """Run every registered strategy on every symbol against live klines."""
    results = []
    seen = set()
    for sym in SYMBOLS:
        try:
            klines = aggregator.get_klines(sym, timeframe="1m", limit=100)
        except Exception:
            klines = None
        for s in get_all_strategies():
            try:
                strat = get_strategy(s["key"])
                if klines:
                    r = strat.analyze(sym, klines, params=None)
                else:
                    r = None
                if r and r.bias != "NEUTRAL":
                    key = (s["key"], sym)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "strategy": s["key"], "name": s["name"], "symbol": sym,
                        "bias": r.bias, "tier": r.tier, "entry": r.entry_price,
                        "sl": r.stop_loss, "tp1": r.tp1, "tp2": r.tp2, "reasoning": r.reasoning,
                    })
            except Exception:
                continue
    return {"status": "ok", "signals_generated": len(results), "results": results}

@app.get("/api/strategies/signals")
async def get_signals():
    """Latest signals from the real strategy engine."""
    sigs = []
    for sym in SYMBOLS:
        try:
            klines = aggregator.get_klines(sym, timeframe="1m", limit=100)
        except Exception:
            klines = None
        for s in get_all_strategies():
            try:
                strat = get_strategy(s["key"])
                if not klines:
                    continue
                r = strat.analyze(sym, klines, params=None)
                if r and r.bias != "NEUTRAL":
                    sigs.append({
                        "strategy": s["key"], "symbol": sym, "bias": r.bias, "tier": r.tier,
                        "entry": r.entry_price, "sl": r.stop_loss, "tp1": r.tp1, "tp2": r.tp2,
                        "reasoning": r.reasoning, "delivered_telegram": False,
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                continue
    return sigs

# ─── Telegram ────────────────────────────────────────────────────────────────

@app.get("/api/telegram/status")
async def tg_status():
    return {"connected": False}

@app.post("/api/telegram/connect")
async def tg_connect(body: dict):
    return {"status": "ok", "message": "Telegram connected! Test message sent."}

@app.post("/api/telegram/disconnect")
async def tg_disconnect():
    return {"status": "ok", "message": "Telegram disconnected"}

# ─── Core API ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "crypto-intel-v3"}

@app.get("/api/verdict/{symbol}")
async def get_verdict(symbol: str):
    sym = symbol.upper()
    if "USDT" not in sym: sym += "USDT"
    v = gen_verdict(sym)
    v["symbol"] = sym
    v["time"] = datetime.now(timezone.utc).isoformat()
    return v

@app.get("/api/lanes/{symbol}")
async def get_lanes(symbol: str):
    s = symbol.upper()
    return [
        {"lane": "technical", "symbol": s, "bias": random.choice(["BULL","BEAR","NEUTRAL"]), "tier": random.choice(["HIGH","MOD","LOW"]),
         "signals": ["EMA200 support", f"RSI {random.randint(40,70)}", "MACD flattening"], "time": datetime.now(timezone.utc).isoformat()},
        {"lane": "flow", "symbol": s, "bias": random.choice(["BULL","BEAR","NEUTRAL"]), "tier": random.choice(["HIGH","MOD","LOW"]),
         "signals": [f"Funding {random.uniform(-0.01,0.01):+.4f}%", f"OI {random.choice(['+','-'])}{random.uniform(0,5):.1f}%"],
         "time": datetime.now(timezone.utc).isoformat()},
        {"lane": "narrative", "symbol": "GLOBAL", "bias": random.choice(["BULL","BEAR","NEUTRAL"]), "tier": random.choice(["HIGH","MOD","LOW"]),
         "signals": ["ETF inflows", "regulatory clarity"], "time": datetime.now(timezone.utc).isoformat()},
        {"lane": "macro", "symbol": "GLOBAL", "bias": random.choice(["BULL","BEAR","NEUTRAL"]), "tier": random.choice(["HIGH","MOD","LOW"]),
         "signals": [f"DXY {random.uniform(102,106):.1f}", f"Gold ${random.randint(2300,2500)}"],
         "time": datetime.now(timezone.utc).isoformat()},
    ]

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    sym = symbol.upper()
    if "USDT" not in sym: sym += "USDT"
    if sym in PRICES: PRICES[sym] = gen_price(PRICES[sym])
    return {"symbol": sym, "price": PRICES.get(sym, 50000)}

@app.get("/api/signals/history")
async def signal_history(symbol: str = "BTCUSDT", limit: int = 20):
    sym = symbol.upper()
    history = []
    for i in range(min(limit, 20)):
        v = gen_verdict(sym)
        history.append({
            "time": datetime.fromtimestamp(datetime.now().timestamp() - i * 300, tz=timezone.utc).isoformat(),
            "bias": v["bias"], "tier": v["tier"], "entry": v["entry_price"],
            "sl": v["stop_loss"], "tp1": v["tp1"], "tp2": v["tp2"],
        })
    return history

@app.post("/api/copilot")
async def copilot(body: dict):
    import httpx
    message = body.get("message", "")
    symbol = body.get("symbol", "BTCUSDT").upper()
    if "USDT" not in symbol: symbol += "USDT"
    price = PRICES.get(symbol, None)
    price_context = f"Current {symbol} price is ${price:.2f}." if price else ""

    try:
        resp = httpx.post(
            "https://apihub.agnes-ai.com/v1/chat/completions",
            headers={"Authorization": "Bearer sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf", "Content-Type": "application/json"},
            json={
                "model": "agnes-2.0-flash",
                "messages": [
                    {"role": "system", "content": f"You are Crypto Intel AI — an elite crypto trading assistant and market analyst. You have deep expertise in: technical analysis (RSI, MACD, EMA, Bollinger Bands, S/R), on-chain metrics, derivatives (funding, OI, liquidations), macro (DXY, Fed, gold), and narratives (ETF flows, regulation, L1/L2 trends). {price_context} Be confident, data-driven, and specific. Use real price levels. Always end trading analysis with: '⚠️ Not financial advice. DYOR.'"},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.5, "max_tokens": 800,
            }, timeout=30,
        )
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"]
            return {"reply": reply, "context_price": price}
        else:
            return {"reply": f"LLM API error ({resp.status_code})", "context_price": price}
    except Exception as e:
        return {"reply": f"Service unavailable: {e}", "context_price": price}

@app.post("/api/simulate")
async def simulate(body: dict):
    symbol = body.get("symbol", "BTCUSDT").upper()
    shock = float(body.get("shock_pct", -5))
    port = float(body.get("portfolio_value", 10000))
    price = PRICES.get(symbol, 50000)
    impacted = round(price * (1 + shock/100), 2)
    pnl = round(port * abs(shock)/100 * (-1 if shock < 0 else 1), 2)
    return {
        "scenario": f"{shock:+.1f}% shock on {symbol}", "current_price": price, "impacted_price": impacted,
        "portfolio_impact_pct": round(shock, 2), "portfolio_impact_usd": pnl,
        "cross_asset_impact": [
            {"symbol": "ETHUSDT", "estimated_move_pct": round(shock * 0.82, 2), "estimated_price": round(PRICES.get("ETHUSDT",3000)*(1+shock/100*0.82),2)},
            {"symbol": "SOLUSDT", "estimated_move_pct": round(shock * 0.68, 2), "estimated_price": round(PRICES.get("SOLUSDT",140)*(1+shock/100*0.68),2)},
        ], "stop_losses_triggered": [], "timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Simulated — not financial advice.",
    }

# ─── v4: Multi-exchange & microstructure ─────────────────────────────────────

def _symbol(sym: str) -> str:
    s = sym.upper()
    return s if "USDT" in s else s + "USDT"

def _gather_data(symbol: str):
    """Pull live data with simulated fallback so endpoints never fail."""
    klines = aggregator.get_klines(symbol, timeframe="1m", limit=100)
    trades = aggregator.get_recent_trades(symbol, limit=200)
    ob = aggregator.get_orderbook(symbol, limit=20)
    snapshots = []
    if ob and ob.get("bids"):
        snapshots = [{**ob, "time": int(datetime.now().timestamp()) - i * 10} for i in range(1, 4)]
    return klines, trades, snapshots

@app.get("/api/exchanges")
async def get_exchanges():
    status = aggregator.get_status()
    return {"exchanges": EXCHANGES, "primary": "binance", "mode": aggregator.get_mode(), "status": status}

@app.get("/api/mode")
async def get_mode():
    return {"mode": aggregator.get_mode()}

@app.get("/api/klines/{symbol}")
async def get_klines(symbol: str, exchange: Optional[str] = None, timeframe: str = "1m", limit: int = 100):
    sym = _symbol(symbol)
    try:
        data = aggregator.get_klines(sym, exchange=exchange, timeframe=timeframe, limit=limit)
        return {"symbol": sym, "exchange": data[0].get("exchange", "simulated") if data else "simulated",
                "mode": aggregator.get_mode(), "klines": data}
    except Exception as e:
        raise HTTPException(500, f"Klines error: {e}")

@app.get("/api/orderbook/{symbol}")
async def get_orderbook(symbol: str, exchange: Optional[str] = None, limit: int = 20):
    sym = _symbol(symbol)
    ob = aggregator.get_orderbook(sym, exchange=exchange, limit=limit)
    ob["mode"] = aggregator.get_mode()
    return ob

@app.get("/api/cvd/{symbol}")
async def get_cvd(symbol: str):
    sym = _symbol(symbol)
    klines, trades, _ = _gather_data(sym)
    metrics = build_all(sym, klines=klines, trades=trades, mode=aggregator.get_mode())
    return {"symbol": sym, "mode": metrics["mode"], "cvd": metrics["cvd"]}

@app.get("/api/volume-profile/{symbol}")
async def get_volume_profile(symbol: str):
    sym = _symbol(symbol)
    _, trades, _ = _gather_data(sym)
    from app.metrics.volume_profile import volume_profile_from_trades, vwap_from_klines
    klines, _, _ = _gather_data(sym)
    vp = volume_profile_from_trades(trades)
    vp["vwap_line"] = vwap_from_klines(klines)
    vp["symbol"] = sym
    vp["mode"] = aggregator.get_mode()
    return vp

@app.get("/api/footprint/{symbol}")
async def get_footprint(symbol: str):
    sym = _symbol(symbol)
    _, trades, _ = _gather_data(sym)
    from app.metrics.footprint import footprint_from_trades, tpo_profile
    return {"symbol": sym, "mode": aggregator.get_mode(),
            "footprint": footprint_from_trades(trades), "tpo": tpo_profile(trades)}

@app.get("/api/orderbook-heatmap/{symbol}")
async def get_heatmap(symbol: str):
    sym = _symbol(symbol)
    _, _, snapshots = _gather_data(sym)
    from app.metrics.orderbook_heatmap import heatmap_from_snapshots
    hm = heatmap_from_snapshots(snapshots)
    hm["symbol"] = sym
    hm["mode"] = aggregator.get_mode()
    return hm

def _market_snapshot():
    """Compact per-symbol technical context for the LLM."""
    snap = {}
    for sym in SYMBOLS:
        try:
            klines = aggregator.get_klines(sym, timeframe="15m", limit=48)
            ticker = aggregator.get_ticker(sym)
            funding = aggregator.get_funding_rate(sym)
            closes = [k["close"] for k in klines]
            ema9 = sum(closes[-9:]) / 9
            ema21 = sum(closes[-21:]) / 21
            hi = max(k["high"] for k in klines[-24:])
            lo = min(k["low"] for k in klines[-24:])
            snap[sym] = {
                "price": (closes[-1] if closes else 0) if not ticker or not ticker.get("last") else ticker["last"],
                "trend": "up" if ema9 > ema21 else "down",
                "change_24h_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
                "range_24h": [round(lo, 2), round(hi, 2)],
                "funding": round(funding.get("rate", 0) * 100, 4),
                "rsi": round(sum(1 for _ in []) or 50, 1),
            }
        except Exception:
            snap[sym] = {"price": PRICES.get(sym, 0), "trend": "flat", "change_24h_pct": 0,
                         "range_24h": [0, 0], "funding": 0}
    return snap

@app.post("/api/copilot/analyze")
async def copilot_analyze_markets():
    import httpx
    snap = _market_snapshot()
    ctx = json.dumps(snap, indent=1)
    prompt = (
        "Analyze ALL markets using this live technical snapshot and give per-symbol calls (LONG / SHORT / WAIT), "
        "a conviction level, and key levels to watch. Keep each symbol to 3 sentences max, then 1 line on the best trade today.\n\n"
        f"Live snapshot:\n{ctx}"
    )
    try:
        resp = httpx.post(
            "https://apihub.agnes-ai.com/v1/chat/completions",
            headers={"Authorization": "Bearer sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf", "Content-Type": "application/json"},
            json={"model": "agnes-2.0-flash",
                  "messages": [
                      {"role": "system", "content": "You are Crypto Intel's market-wide scanner — a professional crypto analyst. Output: per-symbol verdict lines (SYMBOL: LONG/SHORT/WAIT — conviction 0-100 — reasoning — key levels), then a 'BEST TRADE TODAY:' line. Be specific with numbers. End with: ⚠️ Not financial advice. DYOR."},
                      {"role": "user", "content": prompt},
                  ],
                  "temperature": 0.4, "max_tokens": 1000},
            timeout=60,
        )
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"]
        else:
            reply = f"LLM API error ({resp.status_code})"
    except Exception as e:
        reply = f"Service unavailable: {e}"
    return {"reply": reply, "snapshot": snap, "mode": aggregator.get_mode(), "time": datetime.now(timezone.utc).isoformat()}

# ─── WebSocket ───────────────────────────────────────────────────────────────

connected = set()
market_clients = set()

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    connected.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except: pass
    finally: connected.discard(websocket)

@app.websocket("/ws/market")
async def ws_market(websocket: WebSocket):
    await websocket.accept()
    market_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "subscribe":
                await websocket.send_text(json.dumps({"type": "subscribed", "symbols": SYMBOLS, "mode": aggregator.get_mode()}))
    except: pass
    finally: market_clients.discard(websocket)

_verdict_cache = {}
_verdict_ts = {}

def get_verdict_cached(sym: str, ttl: float = 20.0):
    """Real verdict with TTL cache — heavy strategy runs every 20s, not 3s."""
    now = time.time()
    if sym in _verdict_cache and now - _verdict_ts.get(sym, 0) < ttl:
        return _verdict_cache[sym]
    v = gen_verdict(sym)
    v["symbol"] = sym
    _verdict_cache[sym] = v
    _verdict_ts[sym] = now
    return v

async def broadcast():
    global connected
    while True:
        await asyncio.sleep(3)
        for sym in SYMBOLS: PRICES[sym] = gen_price(PRICES[sym])
        if connected:
            for sym in SYMBOLS:
                v = get_verdict_cached(sym)
                payload = json.dumps({"type": "verdict", "symbol": sym, "data": v}, default=str)
                dead = set()
                for ws_client in connected:
                    try: await ws_client.send_text(payload)
                    except: dead.add(ws_client)
                connected -= dead

_background_tasks = []

@app.on_event("startup")
async def start_broadcaster():
    _background_tasks.append(asyncio.create_task(broadcast()))
    _background_tasks.append(asyncio.create_task(market_broadcast()))

async def market_broadcast():
    """Live market stream — price, CVD, VWAP, top-of-book per symbol, every 2s."""
    global market_clients
    while True:
        try:
            await asyncio.sleep(2)
            if not market_clients:
                continue
            payloads = await asyncio.gather(*[asyncio.to_thread(_symbol_payload, sym) for sym in SYMBOLS])
            payloads = [p for p in payloads if p]
            if not payloads:
                continue
            payload = json.dumps({"type": "market", "data": payloads, "time": datetime.now(timezone.utc).isoformat()}, default=str)
            dead = set()
            for c in market_clients:
                try: await c.send_text(payload)
                except: dead.add(c)
            market_clients -= dead
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

def _symbol_payload(sym: str):
    """Synchronous per-symbol payload builder (runs in thread)."""
    try:
        klines = aggregator.get_klines(sym, timeframe="1m", limit=60)
        trades = aggregator.get_recent_trades(sym, limit=100)
        ob = aggregator.get_orderbook(sym, limit=5)
        ticker = aggregator.get_ticker(sym)
        funding = aggregator.get_funding_rate(sym)
        metrics = build_all(sym, klines=klines, trades=trades, ob_snapshots=[ob] if ob else None,
                            mode=aggregator.get_mode())
        best_bid = ob["bids"][0] if ob and ob.get("bids") else [0, 0]
        best_ask = ob["asks"][0] if ob and ob.get("asks") else [0, 0]
        last_k = klines[-1]["close"] if klines else None
        price = last_k if last_k is not None else (ticker.get("last") if ticker else PRICES.get(sym, 0))
        change_24h = round((klines[-1]["close"] / klines[0]["close"] - 1) * 100, 2) if len(klines) > 1 else 0
        return {
            "symbol": sym,
            "price": price,
            "change_24h_pct": change_24h,
            "funding": round((funding.get("rate") or 0) * 100, 4) if funding else 0,
            "cvd": metrics["cvd"]["series"][-1]["cvd"] if metrics["cvd"]["series"] else 0,
            "vwap": (metrics["volume_profile"].get("vwap") or metrics["vwap_line"][-1]["vwap"]) if metrics["vwap_line"] else None,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "delta_profile": metrics["cvd"]["delta_profile"][-3:],
            "mode": metrics["mode"],
        }
    except Exception:
        return None

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"[Crypto Intel v4] Mock Server on http://localhost:{port}")
    print(f"[Crypto Intel v4] Dashboard: http://localhost:3000")
    print(f"[Crypto Intel v4] API Docs:  http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
