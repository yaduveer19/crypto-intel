"""Liquidation tracker — REAL data from Binance force-order WebSocket.

Runs a background thread subscribing to wss://fstream.binance.com/ws/!forceOrder@arr
(the all-market liquidation stream). Aggregates prints into 10 price bins and a
rolling tape of the largest liquidations.

If the socket is unreachable, a clearly-labelled synthetic fallback is produced so
the UI is never empty (marked live=false).
"""
import json
import threading
import time
from collections import deque
from typing import Optional

try:
    import websockets  # noqa: F401  (kept for docs; sync client below)
except ImportError:
    pass

import random

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BIN_OFFSETS = [-0.02, -0.015, -0.01, -0.005, -0.002, 0.002, 0.005, 0.01, 0.015, 0.02]

_lock = threading.Lock()
# per symbol: deque of (ts, price, qty, side, notional)
_prints: dict = {s: deque(maxlen=500) for s in SYMBOLS}
_last_price: dict = {s: 0.0 for s in SYMBOLS}
_started = False
_ws_ok = False
_stats = {"events": 0, "started_at": None, "last_event": None}


def _ws_loop():
    """Blocking websocket consumer with reconnect. Uses the `websockets` sync client."""
    global _ws_ok
    import asyncio
    try:
        from websockets.sync.client import connect
    except Exception:
        return

    url = "wss://fstream.binance.com/ws/!forceOrder@arr"
    while True:
        try:
            with connect(url, open_timeout=15, close_timeout=5) as ws:
                _ws_ok = True
                while True:
                    raw = ws.recv(timeout=60)
                    if not raw:
                        continue
                    msg = json.loads(raw)
                    o = msg.get("o") or {}
                    sym = (o.get("s") or "").upper()
                    if sym not in _prints:
                        continue
                    price = float(o.get("ap") or o.get("p") or 0)
                    qty = float(o.get("q") or 0)
                    # Binance side is the LIQUIDATED side: SELL = long liquidated, BUY = short liquidated
                    side = (o.get("S") or "").upper()
                    liq_side = "LONG" if side == "SELL" else "SHORT"
                    notional = price * qty
                    with _lock:
                        _prints[sym].append((time.time(), price, qty, liq_side, notional))
                        _last_price[sym] = price
                        _stats["events"] += 1
                        _stats["last_event"] = time.time()
        except Exception:
            _ws_ok = False
            time.sleep(5)


def start():
    """Start the background liquidation feed once."""
    global _started
    if _started:
        return
    _started = True
    _stats["started_at"] = time.time()
    t = threading.Thread(target=_ws_loop, name="liq-feed", daemon=True)
    t.start()


def record_local(price: float, liq_side: str = "LONG", qty: float = 0.0, symbol: str = "BTCUSDT"):
    """Optional manual injection (e.g. from simulated feed)."""
    if symbol in _prints and price:
        with _lock:
            _prints[symbol].append((time.time(), price, qty or 0.01, liq_side, price * (qty or 0.01)))
            _last_price[symbol] = price


def _synthetic(symbol: str) -> dict:
    mid = _last_price.get(symbol) or 60000.0
    bins = []
    total_long = total_short = 0.0
    for i, off in enumerate(BIN_OFFSETS):
        px = round(mid * (1 + off), 2)
        est = round(2.8 + abs(off) * 260 + (i % 3) * 1.9, 2)
        side = "LONG" if off < 0 else "SHORT"
        if side == "LONG":
            total_long += est
        else:
            total_short += est
        bins.append({"price": px, "offset_pct": round(off * 100, 2), "volume": est,
                     "side": side, "notional_usd": round(est * px, 0)})
    return {
        "symbol": symbol, "mid": mid, "bins": bins, "live": False,
        "total_long_usd": round(total_long * mid, 0), "total_short_usd": round(total_short * mid, 0),
        "largest": [], "events": 0,
        "magnet_score": round(min(99.0, 55 + total_long / 40), 1),
        "note": "synthetic fallback — Binance forceOrder WS unreachable",
    }


def get_liquidations(symbol: str) -> dict:
    sym = symbol.upper()
    if "USDT" not in sym:
        sym += "USDT"
    if sym not in _prints:
        sym = "BTCUSDT"

    now = time.time()
    with _lock:
        prints = list(_prints[sym])
        mid = _last_price.get(sym) or 0.0

    if not prints:
        return _synthetic(sym)

    # use prints from last 24h
    recent = [p for p in prints if now - p[0] <= 86400] or prints
    mid = mid or recent[-1][1]
    # 10 bins built symmetrically around mid
    bins = []
    total_long = total_short = 0.0
    for i, off in enumerate(BIN_OFFSETS):
        px = mid * (1 + off)
        lo, hi = px * 0.9975, px * 1.0025
        vol = sum(p[2] for p in recent if lo <= p[1] <= hi)
        side = "LONG" if off < 0 else "SHORT"
        if vol > 0:
            if side == "LONG":
                total_long += vol
            else:
                total_short += vol
        bins.append({
            "price": round(px, 2), "offset_pct": round(off * 100, 2),
            "volume": round(vol, 4), "side": side, "notional_usd": round(vol * px, 0),
        })

    largest = sorted(recent, key=lambda p: p[4], reverse=True)[:12]
    largest_list = [{
        "time": time.strftime("%H:%M:%S", time.localtime(p[0])),
        "price": p[1], "qty": round(p[2], 4), "side": p[3], "notional_usd": round(p[4], 0),
    } for p in largest]

    # magnet score — how much liquidation fuel is stacked below/above
    imbalance = 0.0
    if total_long + total_short > 0:
        imbalance = (total_short - total_long) / (total_short + total_long)
    magnet = round(min(99.0, 50 + abs(imbalance) * 100), 1)

    return {
        "symbol": sym,
        "mid": round(mid, 2),
        "bins": sorted(bins, key=lambda b: b["price"]),
        "live": _ws_ok,
        "total_long_usd": round(total_long * mid, 0),
        "total_short_usd": round(total_short * mid, 0),
        "largest": largest_list,
        "events": len(recent),
        "magnet_score": magnet,
        "note": "live Binance forceOrder stream" if _ws_ok else "feed reconnecting",
    }


def status() -> dict:
    return {"ws_ok": _ws_ok, "events": _stats["events"], "started": _started,
            "started_at": _stats["started_at"], "last_event": _stats["last_event"]}