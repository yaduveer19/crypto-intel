"""Paper trading — virtual USDT account on real prices. State persisted to JSON,
loaded fresh on every call (idempotent, refresh-script safe)."""
import json
import os
import time
import uuid
from typing import Optional

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "paper_state.json")
START_BALANCE = 10000.0


def _load() -> dict:
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict) and "balance" in st:
                return st
    except Exception:
        pass
    return {"balance": START_BALANCE, "start_balance": START_BALANCE,
            "positions": [], "history": [], "created": int(time.time())}


def _save(st: dict) -> None:
    try:
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass


def _price(symbol: str) -> Optional[float]:
    try:
        from app.exchange.aggregator import aggregator
        k = aggregator.get_klines(symbol, timeframe="1m", limit=2)
        if k:
            return float(k[-1]["close"])
        t = aggregator.get_ticker(symbol)
        if t and t.get("last"):
            return float(t["last"])
    except Exception:
        pass
    return None


def get_state() -> dict:
    st = _load()
    positions = []
    equity = st["balance"]
    for p in st["positions"]:
        price = _price(p["symbol"]) or p["entry"]
        if p["side"] == "long":
            upnl = (price / p["entry"] - 1) * p["qty"]
        else:
            upnl = (p["entry"] / price - 1) * p["qty"]
        notional = price * p["qty"]
        equity += notional + upnl
        positions.append({**p, "mark": round(price, 8 if price < 10 else 2),
                          "upnl": round(upnl, 2), "notional": round(notional, 2),
                          "pnl_pct": round((upnl / (p["entry"] * p["qty"])) * 100, 2)})
    return {"balance": round(st["balance"], 2), "equity": round(equity, 2),
            "start_balance": st.get("start_balance", START_BALANCE),
            "positions": positions, "history": st["history"][-40:][::-1],
            "open_count": len(positions),
            "total_pnl": round(equity - st.get("start_balance", START_BALANCE), 2),
            "total_pnl_pct": round((equity / st.get("start_balance", START_BALANCE) - 1) * 100, 2)}


def open_position(symbol: str, side: str, usd: float, sl: Optional[float] = None,
                  tp: Optional[float] = None) -> dict:
    st = _load()
    symbol = symbol.upper()
    if "USDT" not in symbol:
        symbol += "USDT"
    side = "long" if side.lower().startswith("l") else "short"
    usd = float(usd)
    if usd <= 0:
        return {"error": "usd must be positive"}
    price = _price(symbol)
    if not price:
        return {"error": f"No price for {symbol}"}
    if usd > st["balance"]:
        return {"error": f"Insufficient balance ({st['balance']:.2f} USDT available)"}
    qty = usd / price
    pos = {"id": uuid.uuid4().hex[:10], "symbol": symbol, "side": side,
           "qty": qty, "entry": price, "sl": sl, "tp": tp,
           "opened_at": int(time.time()), "cost_usd": round(usd, 2)}
    st["balance"] -= usd
    st["positions"].append(pos)
    _save(st)
    return {"status": "opened", "position": pos, "balance": round(st["balance"], 2)}


def close_position(position_id: str, reason: str = "manual") -> dict:
    st = _load()
    pos = next((p for p in st["positions"] if p["id"] == position_id), None)
    if not pos:
        return {"error": "Position not found"}
    price = _price(pos["symbol"]) or pos["entry"]
    if pos["side"] == "long":
        upnl = (price / pos["entry"] - 1) * pos["qty"]
    else:
        upnl = (pos["entry"] / price - 1) * pos["qty"]
    proceeds = pos["qty"] * price
    st["balance"] += proceeds
    st["positions"] = [p for p in st["positions"] if p["id"] != position_id]
    rec = {**pos, "closed_at": int(time.time()), "exit": price,
           "pnl": round(upnl, 2), "pnl_pct": round(upnl / (pos["entry"] * pos["qty"]) * 100, 2),
           "reason": reason}
    st.setdefault("history", []).append(rec)
    st["history"] = st["history"][-100:]
    _save(st)
    return {"status": "closed", "pnl": rec["pnl"], "pnl_pct": rec["pnl_pct"],
            "exit": price, "balance": round(st["balance"], 2)}


def reset() -> dict:
    st = {"balance": START_BALANCE, "start_balance": START_BALANCE,
          "positions": [], "history": [], "created": int(time.time())}
    _save(st)
    return {"status": "reset", "balance": START_BALANCE}
