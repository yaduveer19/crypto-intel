# Standalone mock server — no Docker, no DB, no Redis needed
# python mock_server.py

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json, random, math, asyncio, uuid
from datetime import datetime, timezone
import uvicorn

app = FastAPI(title="Crypto Intel v3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
PRICES = {"BTCUSDT": 67500, "ETHUSDT": 3450, "SOLUSDT": 145}

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
]

def gen_verdict(sym):
    price = PRICES.get(sym, 50000)
    bias = random.choices(["BULL", "BEAR", "NEUTRAL"], weights=[0.4, 0.3, 0.3])[0]
    tier = random.choices(["HIGH", "MOD", "LOW"], weights=[0.3, 0.4, 0.3])[0]
    atr = price * 0.02
    if bias == "BULL":
        return {"bias": bias, "tier": tier, "entry_price": price, "stop_loss": round(price - atr * 2, 2), "tp1": round(price + atr * 3, 2), "tp2": round(price + atr * 6, 2),
                "reasoning": f"{bias} signal from 4-lane synthesis. Technical + Flow align. ATR-based risk levels set."}
    elif bias == "BEAR":
        return {"bias": bias, "tier": tier, "entry_price": price, "stop_loss": round(price + atr * 2, 2), "tp1": round(price - atr * 3, 2), "tp2": round(price - atr * 6, 2),
                "reasoning": f"{bias} signal. Macro + Narrative driving bearish bias. Tight stops recommended."}
    return {"bias": bias, "tier": tier, "entry_price": price, "stop_loss": round(price - atr * 1.5, 2), "tp1": round(price + atr * 2, 2), "tp2": round(price + atr * 4, 2),
            "reasoning": "Mixed signals across lanes. Waiting for clearer confirmation."}

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
    return STRATEGIES

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
    count = random.randint(1, 4)
    results = []
    for i in range(count):
        sym = random.choice(SYMBOLS)
        v = gen_verdict(sym)
        results.append({"strategy": random.choice([s["key"] for s in STRATEGIES]), "symbol": sym, "bias": v["bias"], "tier": v["tier"]})
    return {"status": "ok", "signals_generated": count, "results": results}

@app.get("/api/strategies/signals")
async def get_signals():
    sigs = []
    for i in range(10):
        sym = random.choice(SYMBOLS)
        v = gen_verdict(sym)
        sigs.append({
            "id": i + 1, "strategy": random.choice([s["key"] for s in STRATEGIES]),
            "symbol": sym, "bias": v["bias"], "tier": v["tier"],
            "entry": v["entry_price"], "sl": v["stop_loss"], "tp1": v["tp1"], "tp2": v["tp2"],
            "reasoning": v["reasoning"], "delivered_telegram": random.choice([True, False]),
            "time": datetime.fromtimestamp(datetime.now().timestamp() - i * 1800, tz=timezone.utc).isoformat(),
        })
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

# ─── WebSocket ───────────────────────────────────────────────────────────────

connected = set()

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

async def broadcast():
    while True:
        await asyncio.sleep(3)
        for sym in SYMBOLS: PRICES[sym] = gen_price(PRICES[sym])
        if connected:
            for sym in SYMBOLS:
                v = gen_verdict(sym); v["symbol"] = sym
                payload = json.dumps({"type": "verdict", "symbol": sym, "data": v}, default=str)
                dead = set()
                for ws_client in connected:
                    try: await ws_client.send_text(payload)
                    except: dead.add(ws_client)
                connected -= dead

@app.on_event("startup")
async def start_broadcaster():
    asyncio.create_task(broadcast())

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"🚀 Crypto Intel v3 Mock Server on http://localhost:{port}")
    print(f"📊 Dashboard: http://localhost:3000")
    print(f"📋 API Docs:  http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
