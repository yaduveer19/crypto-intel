"""Signal grading — replay a registered strategy bar-by-bar on REAL klines,
then check every historical call against the candles that came after:
TARGET_HIT / STOP_HIT / OPEN. Nothing is dropped — every call gets a grade."""
import time
from typing import List, Optional

from app.intel.fetcher import cached


def _grade_forward(klines: list, i: int, side: str, sl: float, tp: float,
                   max_bars: int = 96) -> dict:
    """Walk forward from bar i+1; same-bar ambiguity resolves to STOP (conservative)."""
    for j in range(i + 1, min(i + 1 + max_bars, len(klines))):
        bar = klines[j]
        if side == "BULL":
            if sl and bar["low"] <= sl:
                return {"grade": "STOP_HIT", "exit": sl, "bars": j - i,
                        "pnl_pct": round((sl / klines[i]["close"] - 1) * 100, 3)}
            if tp and bar["high"] >= tp:
                return {"grade": "TARGET_HIT", "exit": tp, "bars": j - i,
                        "pnl_pct": round((tp / klines[i]["close"] - 1) * 100, 3)}
        else:
            if sl and bar["high"] >= sl:
                return {"grade": "STOP_HIT", "exit": sl, "bars": j - i,
                        "pnl_pct": round((klines[i]["close"] / sl - 1) * 100, 3)}
            if tp and bar["low"] <= tp:
                return {"grade": "TARGET_HIT", "exit": tp, "bars": j - i,
                        "pnl_pct": round((klines[i]["close"] / tp - 1) * 100, 3)}
    last = klines[min(i + max_bars, len(klines) - 1)]
    px = last["close"]
    base = klines[i]["close"]
    pnl = (px / base - 1) * 100 if side == "BULL" else (base / px - 1) * 100
    return {"grade": "OPEN", "exit": px, "bars": min(max_bars, len(klines) - 1 - i),
            "pnl_pct": round(pnl, 3)}


def grade_signals(symbol: str, strategy_key: str = "trend_following",
                  timeframe: str = "15m", limit: int = 400) -> dict:
    def build():
        from app.exchange.aggregator import aggregator
        from app.strategies.engine import get_strategy

        strat = get_strategy(strategy_key)
        if not strat:
            return {"error": f"Unknown strategy '{strategy_key}'", "signals": []}
        klines = aggregator.get_klines(symbol, timeframe=timeframe, limit=limit)
        if not klines or len(klines) < 80:
            return {"error": "Not enough klines to grade", "signals": []}

        signals: List[dict] = []
        last_state = "NEUTRAL"
        next_allowed = 0
        warmup = 60
        for i in range(warmup, len(klines) - 1):
            if i < next_allowed:
                continue
            try:
                r = strat.analyze(symbol, klines[:i + 1], params=None)
            except Exception:
                continue
            state = r.bias if r else "NEUTRAL"
            if state in ("BULL", "BEAR") and last_state == "NEUTRAL":
                entry = klines[i]["close"]
                sl = r.stop_loss if r and r.stop_loss else (entry * 0.98 if state == "BULL" else entry * 1.02)
                tp = r.tp1 if r and r.tp1 else (entry * 1.03 if state == "BULL" else entry * 0.97)
                g = _grade_forward(klines, i, state, sl, tp)
                signals.append({
                    "time": klines[i]["time"], "bias": state, "tier": r.tier if r else "LOW",
                    "entry": round(entry, 6), "sl": round(sl, 6), "tp": round(tp, 6),
                    "strategy": strategy_key, "reasoning": (r.reasoning if r else "")[:160],
                    **g,
                })
                # cooldown = grade window so positions never overlap
                next_allowed = i + min(96, len(klines) - i - 1)
            last_state = state

        closed = [s for s in signals if s["grade"] != "OPEN"]
        targets = sum(1 for s in signals if s["grade"] == "TARGET_HIT")
        stops = sum(1 for s in signals if s["grade"] == "STOP_HIT")
        summary = {
            "total": len(signals),
            "target_hit": targets,
            "stop_hit": stops,
            "open": sum(1 for s in signals if s["grade"] == "OPEN"),
            "win_rate": round(targets / len(closed) * 100, 1) if closed else 0.0,
            "avg_pnl_pct": round(sum(s["pnl_pct"] for s in signals) / len(signals), 3) if signals else 0.0,
            "net_pnl_pct": round(sum(s["pnl_pct"] for s in signals), 2),
        }
        return {"symbol": symbol, "strategy": strategy_key, "timeframe": timeframe,
                "summary": summary, "signals": signals[-30:][::-1],
                "method": "strategy replayed bar-by-bar on real candles; grades from forward candles",
                "live": True, "updated": int(time.time())}

    return cached(f"grade_{symbol}_{strategy_key}_{timeframe}", 120, build,
                  default={"signals": [], "summary": {}, "error": "grading unavailable"})


def _tf_seconds(tf: str) -> int:
    return {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
            "4h": 14400, "1d": 86400}.get(tf, 900)
