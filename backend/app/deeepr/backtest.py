"""Backtest engine + plain-English strategy compiler.

Rules JSON (deeepr-style):
{
  "tf": "1h", "side": "long",
  "entry": [{"ind": "rsi", "period": 14, "op": "lt", "val": 30},
            {"ind": "close", "op": "gt_ema", "val": 200}],
  "exit":   [{"ind": "rsi", "period": 14, "op": "gt", "val": 70}],
  "sl_pct": 2.0, "tp_pct": 3.0, "max_bars": 48
}

Supported indicators: close, open, high, low, volume, rsi, ema, macd_hist,
bb_pos, atr_pct, change_pct, vol_ratio, sma
Ops: gt, lt, gt_eq, lt_eq, cross_above, cross_below, gt_ema, lt_ema
(close/open/high/low vs an EMA value)
"""
import json
import re
import time
from typing import List, Optional

from app.intel.fetcher import cached

LLM_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
LLM_KEY = "sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf"
LLM_MODEL = "agnes-3.0-flash"


# ─── indicator math ───────────────────────────────────────────────────────────

def _ema_series(vals: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(vals)
    if len(vals) < period:
        return out
    k = 2 / (period + 1)
    e = sum(vals[:period]) / period
    out[period - 1] = e
    for i in range(period, len(vals)):
        e = vals[i] * k + e * (1 - k)
        out[i] = e
    return out


def _rsi_series(closes: List[float], period: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / period, losses / period
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def _macd_hist(closes: List[float]) -> List[Optional[float]]:
    e12 = _ema_series(closes, 12)
    e26 = _ema_series(closes, 26)
    macd = [(a - b) if a is not None and b is not None else None for a, b in zip(e12, e26)]
    valid = [m for m in macd if m is not None]
    sig_valid = _ema_series(valid, 9)
    sig = [None] * (len(macd) - len(valid)) + sig_valid
    return [(m - s) if m is not None and s is not None else None for m, s in zip(macd, sig)]


def _bb_pos(closes: List[float], period: int = 20) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        w = closes[i - period + 1: i + 1]
        m = sum(w) / period
        var = sum((x - m) ** 2 for x in w) / period
        sd = var ** 0.5
        if sd == 0:
            out[i] = 0.5
        else:
            out[i] = (closes[i] - (m - 2 * sd)) / (4 * sd)
    return out


def _atr_series(klines: list, period: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(klines)
    trs = []
    for i in range(1, len(klines)):
        h, l, pc = klines[i]["high"], klines[i]["low"], klines[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    for i in range(period - 1, len(trs)):
        out[i + 1] = sum(trs[i - period + 1: i + 1]) / period
    return out


def _build_context(klines: list) -> dict:
    closes = [k["close"] for k in klines]
    vols = [k["volume"] for k in klines]
    ema_cache: dict = {}
    return {
        "klines": klines,
        "closes": closes,
        "rsi": _rsi_series(closes, 14),
        "macd_hist": _macd_hist(closes),
        "bb_pos": _bb_pos(closes),
        "atr": _atr_series(klines),
        "sma20": _ema_series(closes, 20),
        "vol_ratio": [(v / (sum(vols[max(0, i - 20):i]) / max(1, min(i, 20))))
                      if i >= 5 and sum(vols[max(0, i - 20):i]) else None
                      for i, v in enumerate(vols)],
        "_ema_cache": ema_cache,
    }


def _ema_at(ctx: dict, period: int, i: int) -> Optional[float]:
    key = period
    if key not in ctx["_ema_cache"]:
        ctx["_ema_cache"][key] = _ema_series(ctx["closes"], period)
    series = ctx["_ema_cache"][key]
    return series[i] if i < len(series) else None


def _ind_at(ctx: dict, ind: str, i: int, period: int = 14) -> Optional[float]:
    if ind == "close":
        return ctx["closes"][i]
    if ind == "rsi":
        series = ctx["rsi"] if period == 14 else _rsi_series(ctx["closes"], period)
        return series[i]
    if ind == "macd_hist":
        return ctx["macd_hist"][i]
    if ind == "bb_pos":
        return ctx["bb_pos"][i]
    if ind == "atr_pct":
        a = ctx["atr"][i]
        return (a / ctx["closes"][i] * 100) if a else None
    if ind == "sma":
        s = ctx["sma20"] if period == 20 else _ema_series(ctx["closes"], period)
        return s[i]
    if ind == "change_pct":
        look = period or 24
        if i < look or not ctx["closes"][i - look]:
            return None
        return (ctx["closes"][i] / ctx["closes"][i - look] - 1) * 100
    if ind == "vol_ratio":
        return ctx["vol_ratio"][i]
    return None


def _cond_true(ctx: dict, cond: dict, i: int) -> bool:
    """Evaluate one condition at bar i (vs i-1 for crosses)."""
    try:
        ind = (cond.get("ind") or "close").lower()
        op = (cond.get("op") or "gt").lower()
        period = int(cond.get("period") or 14)
        val = cond.get("val")
        if i < 1:
            return False

        if op in ("cross_above", "cross_below"):
            # left is price/ind vs right EMA (or both ind): compare i-1 and i
            left_now = _ind_at(ctx, ind, i, period)
            left_prev = _ind_at(ctx, ind, i - 1, period)
            right_period = int(val) if val is not None else 200
            right_now = _ema_at(ctx, right_period, i)
            right_prev = _ema_at(ctx, right_period, i - 1)
            if None in (left_now, left_prev, right_now, right_prev):
                return False
            if op == "cross_above":
                return left_prev <= right_prev and left_now > right_now
            return left_prev >= right_prev and left_now < right_now

        if op in ("gt_ema", "lt_ema"):
            left = _ind_at(ctx, ind, i, period)
            right = _ema_at(ctx, int(val or 200), i)
            if left is None or right is None:
                return False
            return left > right if op == "gt_ema" else left < right

        left = _ind_at(ctx, ind, i, period)
        if left is None:
            return False
        right = float(val) if not isinstance(val, dict) else (_ind_at(ctx, val.get("ind", "close"), i, int(val.get("period") or 14)) or 0)
        if op == "gt":
            return left > right
        if op == "lt":
            return left < right
        if op == "gt_eq":
            return left >= right
        if op == "lt_eq":
            return left <= right
        return False
    except Exception:
        return False


def _all_true(ctx: dict, conds: Optional[list], i: int) -> bool:
    conds = conds or []
    if not conds:
        return False
    return all(_cond_true(ctx, c, i) for c in conds)


# ─── backtest runner ─────────────────────────────────────────────────────────

def run_backtest(rules: dict, klines: list, capital: float = 10000.0) -> dict:
    """Walk the candle history, fire entries when ALL entry rules pass,
    exit on stop/target/exit-rules/max-bars. Returns stats + trades + equity curve."""
    if not klines or len(klines) < 30:
        return {"error": "Not enough candles for backtest", "trades": [], "stats": {}}

    side = (rules.get("side") or "long").lower()
    sl_pct = float(rules.get("sl_pct") or 2.0)
    tp_pct = float(rules.get("tp_pct") or 3.0)
    max_bars = int(rules.get("max_bars") or 48)
    entry_conds = rules.get("entry") or []
    exit_conds = rules.get("exit")

    ctx = _build_context(klines)
    warmup = 30
    trades = []
    equity = capital
    curve = []
    pos = None  # {entry_i, entry_price, entry_time, stop, tp}

    for i in range(warmup, len(klines)):
        bar = klines[i]
        if pos is not None:
            # conservative same-bar check: stop first for longs
            exit_price, reason = None, None
            if side == "long":
                if bar["low"] <= pos["stop"]:
                    exit_price, reason = pos["stop"], "STOP"
                elif bar["high"] >= pos["tp"]:
                    exit_price, reason = pos["tp"], "TARGET"
            else:
                if bar["high"] >= pos["stop"]:
                    exit_price, reason = pos["stop"], "STOP"
                elif bar["low"] <= pos["tp"]:
                    exit_price, reason = pos["tp"], "TARGET"
            if exit_price is None and _all_true(ctx, exit_conds, i):
                exit_price, reason = bar["close"], "RULE"
            if exit_price is None and (i - pos["entry_i"]) >= max_bars:
                exit_price, reason = bar["close"], "TIMEOUT"
            if exit_price is not None:
                if side == "long":
                    pnl_pct = (exit_price / pos["entry_price"] - 1) * 100
                else:
                    pnl_pct = (pos["entry_price"] / exit_price - 1) * 100
                equity *= (1 + pnl_pct / 100)
                trades.append({
                    "entry_time": pos["entry_time"], "exit_time": bar["time"],
                    "entry_price": round(pos["entry_price"], 6), "exit_price": round(exit_price, 6),
                    "side": side, "reason": reason, "pnl_pct": round(pnl_pct, 3),
                    "bars": i - pos["entry_i"], "equity_after": round(equity, 2),
                })
                pos = None
        if pos is None and _all_true(ctx, entry_conds, i):
            pos = {"entry_i": i, "entry_price": bar["close"], "entry_time": bar["time"],
                   "stop": bar["close"] * (1 - sl_pct / 100) if side == "long" else bar["close"] * (1 + sl_pct / 100),
                   "tp": bar["close"] * (1 + tp_pct / 100) if side == "long" else bar["close"] * (1 - tp_pct / 100)}
        curve.append({"t": bar["time"], "equity": round(equity, 2)})

    # close open position at last close for honest stats
    if pos is not None:
        last = klines[-1]
        pnl_pct = ((last["close"] / pos["entry_price"] - 1) * 100) if side == "long" else \
                  ((pos["entry_price"] / last["close"] - 1) * 100)
        equity *= (1 + pnl_pct / 100)
        trades.append({"entry_time": pos["entry_time"], "exit_time": last["time"],
                       "entry_price": round(pos["entry_price"], 6), "exit_price": round(last["close"], 6),
                       "side": side, "reason": "OPEN", "pnl_pct": round(pnl_pct, 3),
                       "bars": len(klines) - 1 - pos["entry_i"], "equity_after": round(equity, 2)})
        curve.append({"t": last["time"], "equity": round(equity, 2)})

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    gross_win = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    peak, max_dd = capital, 0.0
    for pt in curve:
        peak = max(peak, pt["equity"])
        if peak:
            max_dd = max(max_dd, (peak - pt["equity"]) / peak * 100)
    bh_first, bh_last = klines[warmup]["close"], klines[-1]["close"]
    buy_hold = (bh_last / bh_first - 1) * 100 if side == "long" else (bh_first / bh_last - 1) * 100

    stats = {
        "trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "net_pnl_pct": round((equity / capital - 1) * 100, 2),
        "final_equity": round(equity, 2),
        "avg_trade_pct": round(sum(t["pnl_pct"] for t in trades) / len(trades), 3) if trades else 0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else (999.0 if gross_win else 0),
        "max_drawdown_pct": round(max_dd, 2),
        "buy_hold_pct": round(buy_hold, 2),
        "bars": len(klines),
    }
    # thin the curve for transport (max ~200 points)
    step = max(1, len(curve) // 200)
    return {"stats": stats, "trades": trades[-50:], "equity_curve": curve[::step],
            "rules": rules, "capital": capital, "bars": len(klines)}


# ─── templates (deeepr-style ready-made rules) ───────────────────────────────

TEMPLATES = [
    {"key": "rsi_oversold_ema200", "name": "RSI Oversold above EMA200",
     "description": "Buy BTC on the 4h when RSI(14) drops under 30 and price holds the 200 EMA",
     "rules": {"tf": "4h", "side": "long",
               "entry": [{"ind": "rsi", "period": 14, "op": "lt", "val": 30},
                         {"ind": "close", "op": "gt_ema", "val": 200}],
               "exit": [{"ind": "rsi", "period": 14, "op": "gt", "val": 65}],
               "sl_pct": 2.0, "tp_pct": 3.0, "max_bars": 72}},
    {"key": "ema_cross_trend", "name": "EMA 9/21 Trend Crossover",
     "description": "Long when EMA9 crosses above EMA21 with price above EMA200",
     "rules": {"tf": "1h", "side": "long",
               "entry": [{"ind": "close", "op": "cross_above", "val": 21},
                         {"ind": "close", "op": "gt_ema", "val": 200}],
               "sl_pct": 2.5, "tp_pct": 4.5, "max_bars": 96}},
    {"key": "rsi_overbought_short", "name": "RSI Overbought Fade (Short)",
     "description": "Short when RSI(14) spikes above 75 into resistance",
     "rules": {"tf": "1h", "side": "short",
               "entry": [{"ind": "rsi", "period": 14, "op": "gt", "val": 75}],
               "exit": [{"ind": "rsi", "period": 14, "op": "lt", "val": 50}],
               "sl_pct": 2.0, "tp_pct": 3.0, "max_bars": 48}},
    {"key": "bb_squeeze_breakout", "name": "Bollinger Squeeze Breakout",
     "description": "Long on close breaking above the upper band with volume spike",
     "rules": {"tf": "1h", "side": "long",
               "entry": [{"ind": "bb_pos", "op": "gt", "val": 1.0},
                         {"ind": "vol_ratio", "op": "gt", "val": 1.5}],
               "sl_pct": 2.5, "tp_pct": 5.0, "max_bars": 48}},
    {"key": "momentum_bull", "name": "Momentum Continuation",
     "description": "Long when MACD histogram turns positive and RSI above 55",
     "rules": {"tf": "15m", "side": "long",
               "entry": [{"ind": "macd_hist", "op": "gt", "val": 0},
                         {"ind": "rsi", "period": 14, "op": "gt", "val": 55}],
               "sl_pct": 1.5, "tp_pct": 2.5, "max_bars": 32}},
    {"key": "mean_revert_ema50", "name": "EMA50 Mean Reversion",
     "description": "Buy the dip: price 3%+ below EMA50 snaps back to it",
     "rules": {"tf": "4h", "side": "long",
               "entry": [{"ind": "close", "op": "lt_ema", "val": 50},
                         {"ind": "change_pct", "period": 6, "op": "lt", "val": -3}],
               "exit": [{"ind": "close", "op": "gt_ema", "val": 50}],
               "sl_pct": 3.0, "tp_pct": 4.0, "max_bars": 60}},
]


# ─── plain-English → rules compiler (LLM + keyword fallback) ─────────────────

COMPILER_SYSTEM = """You convert a plain-English trading strategy into EXACT JSON rules.
Output ONLY JSON, no prose, no markdown fence. Schema:
{"tf":"1h|4h|15m|1d","side":"long|short","entry":[{"ind":"rsi|close|macd_hist|bb_pos|vol_ratio|change_pct|sma","period":14,"op":"gt|lt|gt_eq|lt_eq|cross_above|cross_below|gt_ema|lt_ema","val":NUMBER}],"exit":[...same...],"sl_pct":NUMBER,"tp_pct":NUMBER,"max_bars":NUMBER}
Rules: "RSI under 30" -> {"ind":"rsi","period":14,"op":"lt","val":30}. "price holds the 200 EMA" -> {"ind":"close","op":"gt_ema","val":200}. "EMA9 crosses above EMA21" -> {"ind":"close","op":"cross_above","val":21}. "take profit at +3%" -> tp_pct 3. "stop loss at -2%" -> sl_pct 2. "on the 4h" -> tf 4h. Defaults: sl_pct 2, tp_pct 3, max_bars 48, side long, tf 1h."""


def _fallback_compile(text: str) -> dict:
    """Deterministic keyword parser when the LLM is unreachable."""
    t = text.lower()
    rules = {"tf": "1h", "side": "long", "entry": [], "exit": [], "sl_pct": 2.0, "tp_pct": 3.0, "max_bars": 48}
    for tf in ("15m", "5m", "1h", "4h", "1d", "1w"):
        if tf in t:
            rules["tf"] = tf
            break
    if "short" in t or "sell" in t and "buy" not in t:
        rules["side"] = "short"
    m = re.search(r"rsi(?:\(\d+\))?.{0,30}?(?:under|below|<|drops?\s+(?:under|below)|is\s+under)\s*(\d+)", t)
    if m:
        rules["entry"].append({"ind": "rsi", "period": 14, "op": "lt", "val": int(m.group(1))})
    m = re.search(r"rsi(?:\(\d+\))?.{0,30}?(?:above|over|>|rises?\s+above|crosses?\s+above|spikes?\s+above)\s*(\d+)", t)
    if m and not any(e.get("ind") == "rsi" for e in rules["entry"]):
        rules["entry"].append({"ind": "rsi", "period": 14, "op": "gt", "val": int(m.group(1))})
    m = re.search(r"(?:above|over|holds?|above)\s+(?:the\s+)?(\d{2,3})\s*(?:ema|sma|e\.m\.a)", t)
    if m:
        rules["entry"].append({"ind": "close", "op": "gt_ema", "val": int(m.group(1))})
    elif re.search(r"(\d{2,3})\s*(?:ema|sma)", t) and "hold" in t:
        num = re.search(r"(\d{2,3})\s*(?:ema|sma)", t)
        rules["entry"].append({"ind": "close", "op": "gt_ema", "val": int(num.group(1))})
    if re.search(r"ema\s*(\d+)\s*(?:crosses? (?:above|over)|cross above)", t):
        n = re.search(r"ema\s*(\d+)\s*(?:crosses? (?:above|over)|cross above)", t)
        rules["entry"].append({"ind": "close", "op": "cross_above", "val": int(n.group(1))})
    if "macd" in t and ("positive" in t or "above zero" in t):
        rules["entry"].append({"ind": "macd_hist", "op": "gt", "val": 0})
    if "volume" in t and ("spike" in t or "surge" in t or "above average" in t):
        rules["entry"].append({"ind": "vol_ratio", "op": "gt", "val": 1.5})
    m = re.search(r"(?:take profit|target|tp)[^0-9]{0,15}\+?(\d+(?:\.\d+)?)\s*%", t)
    if m:
        rules["tp_pct"] = float(m.group(1))
    m = re.search(r"(?:stop loss|stop|sl)[^0-9]{0,15}-?(\d+(?:\.\d+)?)\s*%", t)
    if m:
        rules["sl_pct"] = float(m.group(1))
    if not rules["entry"]:
        rules["entry"].append({"ind": "rsi", "period": 14, "op": "lt", "val": 40})
    return rules


def compile_text(text: str) -> dict:
    """Plain English → rules JSON. LLM first (with strict prompt), keyword fallback."""
    try:
        from app.deeepr.llm import chat
        raw = chat([{"role": "system", "content": COMPILER_SYSTEM},
                    {"role": "user", "content": text}],
                   temperature=0.0, max_tokens=700, timeout=35)
        if raw:
            m = re.search(r"\{.*\}", raw.strip(), re.S)
            if m:
                rules = json.loads(m.group(0))
                # sanity
                rules.setdefault("tf", "1h")
                rules.setdefault("side", "long")
                rules.setdefault("entry", [])
                rules.setdefault("sl_pct", 2.0)
                rules.setdefault("tp_pct", 3.0)
                rules.setdefault("max_bars", 48)
                if rules["entry"]:
                    return {"rules": rules, "source": "llm", "text": text}
    except Exception:
        pass
    return {"rules": _fallback_compile(text), "source": "fallback", "text": text}

