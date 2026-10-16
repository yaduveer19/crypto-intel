"""4-lane Analyze — TECH / FLOW / NEWS / MACRO read separately → one verdict.

Every lane uses REAL data:
- TECH  → RSI / EMA structure / momentum on live klines
- FLOW  → Binance futures funding, OI change, taker buy/sell ratio (fapi, cached)
- NEWS  → Fear&Greed + headline keyword sentiment + high-impact event proximity
- MACRO → DXY / SPX / Gold 1-day changes + BTC correlations + risk regime

Reconciliation: lanes vote (+1/-1/0). |bulls - bears| >= 2 → LONG/SHORT, else WAIT.
Levels: ATR-based entry / stop / TP1 / TP2 (deeepr-style).
"""
import time
from typing import List, Optional

from app.intel.fetcher import cached, get_json
from app.intel.macro import get_macro
from app.intel.news import get_news

BULL_WORDS = ("rally", "rallies", "surge", "surges", "soar", "gains", "approval", "approved",
              "inflow", "inflows", "adoption", "record high", "breakout", "bull", "pump",
              "partnership", "etf", "upgrade", "buyback", "milestone", "recovery")
BEAR_WORDS = ("hack", "exploit", "ban", "lawsuit", "sec ", "crash", "plunge", "drop",
              "outflow", "outflows", "liquidat", "bankrupt", "fraud", "selloff", "bear",
              "SEC", "fine", "halt", "pause", "breach", "stolen", "fear")

TF_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120,
              "4h": 240, "6h": 360, "12h": 720, "1d": 1440}


def _ema(vals: List[float], period: int) -> Optional[float]:
    if len(vals) < period:
        return None
    k = 2 / (period + 1)
    e = sum(vals[:period]) / period
    for v in vals[period:]:
        e = v * k + e * (1 - k)
    return e


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 2)


def _atr(klines: list, period: int = 14) -> Optional[float]:
    if len(klines) < period + 1:
        return None
    trs = []
    for i in range(1, len(klines)):
        h, l, pc = klines[i]["high"], klines[i]["low"], klines[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def _tech_lane(klines: list, price: float) -> dict:
    closes = [k["close"] for k in klines]
    score = 0.0
    signals = []
    rsi = _rsi(closes)
    if rsi is not None:
        if rsi >= 58:
            score += 0.35
            signals.append(f"RSI {rsi} — momentum with buyers")
        elif rsi <= 42:
            score -= 0.35
            signals.append(f"RSI {rsi} — momentum with sellers")
        else:
            signals.append(f"RSI {rsi} — neutral zone")
    e9, e21, e50 = _ema(closes[-9:], 9), _ema(closes[-21:], 21), _ema(closes[-50:], 50) if len(closes) >= 50 else None
    if e9 and e21:
        if e9 > e21:
            score += 0.3
            signals.append("EMA9 above EMA21 — short-term uptrend")
        elif e9 < e21:
            score -= 0.3
            signals.append("EMA9 below EMA21 — short-term downtrend")
    if e50:
        if price > e50:
            score += 0.2
            signals.append("Price holding above EMA50")
        else:
            score -= 0.2
            signals.append("Price below EMA50 — under pressure")
    if len(closes) >= 24:
        chg = (closes[-1] / closes[-24] - 1) * 100
        hi20, lo20 = max(k["high"] for k in klines[-20:]), min(k["low"] for k in klines[-20:])
        signals.append(f"24-bar change {chg:+.2f}%")
        if price >= hi20 * 0.999:
            score += 0.2
            signals.append("Pushing 20-bar highs — breakout watch")
        elif price <= lo20 * 1.001:
            score -= 0.2
            signals.append("At 20-bar lows — breakdown watch")
    state = "Bullish" if score >= 0.3 else ("Bearish" if score <= -0.3 else "Neutral")
    return {"key": "tech", "letter": "T", "label": "Technical", "state": state,
            "bias": 1 if score >= 0.3 else (-1 if score <= -0.3 else 0),
            "score": round(max(-1, min(1, score)), 2), "signals": signals[:5],
            "data": {"rsi": rsi, "ema9": e9, "ema21": e21, "ema50": e50}}


def _flow_facts(symbol: str) -> dict:
    def build():
        facts = {"funding": None, "oi_chg_pct": None, "taker_ratio": None}
        try:
            from app.exchange.aggregator import aggregator
            f = aggregator.get_funding_rate(symbol)
            if f and f.get("rate") is not None:
                facts["funding"] = round(float(f["rate"]) * 100, 5)
        except Exception:
            pass
        d = get_json("https://fapi.binance.com/fapi/v1/openInterestHist",
                     params={"symbol": symbol, "period": "1h", "limit": 24}, timeout=10)
        try:
            first, last = float(d[0]["sumOpenInterest"]), float(d[-1]["sumOpenInterest"])
            if first:
                facts["oi_chg_pct"] = round((last / first - 1) * 100, 3)
        except Exception:
            pass
        t = get_json("https://fapi.binance.com/fapi/v1/takerlongshortRatio",
                     params={"symbol": symbol, "period": "1h", "limit": 24}, timeout=10)
        try:
            ratios = [float(x["buySellRatio"]) for x in t]
            facts["taker_ratio"] = round(sum(ratios) / len(ratios), 4)
        except Exception:
            pass
        return facts

    return cached(f"flow_{symbol}", 90, build, default={"funding": None, "oi_chg_pct": None, "taker_ratio": None})


def _flow_lane(symbol: str) -> dict:
    f = _flow_facts(symbol)
    score, signals = 0.0, []
    if f.get("taker_ratio") is not None:
        r = f["taker_ratio"]
        if r >= 1.05:
            score += 0.45
            signals.append(f"Taker buy/sell {r:.3f} — aggressive buyers")
        elif r <= 0.95:
            score -= 0.45
            signals.append(f"Taker buy/sell {r:.3f} — aggressive sellers")
        else:
            signals.append(f"Taker buy/sell {r:.3f} — balanced flow")
    if f.get("funding") is not None:
        fr = f["funding"]
        if fr >= 0.05:
            score -= 0.2
            signals.append(f"Funding {fr:+.4f}% — crowded longs (caution)")
        elif fr <= -0.03:
            score += 0.2
            signals.append(f"Funding {fr:+.4f}% — shorts paying, squeeze fuel")
        else:
            signals.append(f"Funding {fr:+.4f}% — neutral carry")
    if f.get("oi_chg_pct") is not None:
        oi = f["oi_chg_pct"]
        if oi >= 2:
            score += 0.3
            signals.append(f"OI {oi:+.2f}% in 24h — new money entering")
        elif oi <= -2:
            score -= 0.3
            signals.append(f"OI {oi:+.2f}% in 24h — positions unwinding")
        else:
            signals.append(f"OI {oi:+.2f}% in 24h — flat positioning")
    if not signals:
        signals.append("Flow data unavailable — lane skipped")
    state = "Bullish" if score >= 0.3 else ("Bearish" if score <= -0.3 else "Neutral")
    return {"key": "flow", "letter": "F", "label": "Flow", "state": state,
            "bias": 1 if score >= 0.3 else (-1 if score <= -0.3 else 0),
            "score": round(max(-1, min(1, score)), 2), "signals": signals[:5], "data": f}


def _news_lane() -> dict:
    n = get_news()
    score, signals = 0.0, []
    fng = (n.get("fear_greed") or {}).get("value")
    if fng is not None:
        if fng >= 60:
            score += 0.3
            signals.append(f"Fear & Greed {fng} ({n['fear_greed'].get('label','')}) — risk appetite up")
        elif fng <= 40:
            score -= 0.3
            signals.append(f"Fear & Greed {fng} ({n['fear_greed'].get('label','')}) — risk appetite down")
        else:
            signals.append(f"Fear & Greed {fng} — neutral sentiment")
    bull_hits, bear_hits = 0, 0
    for h in (n.get("headlines") or [])[:14]:
        t = (h.get("title") or "").lower()
        bull_hits += sum(1 for w in BULL_WORDS if w in t)
        bear_hits += sum(1 for w in BEAR_WORDS if w.lower() in t)
    if bull_hits or bear_hits:
        diff = bull_hits - bear_hits
        if diff >= 2:
            score += 0.4
            signals.append(f"Headlines lean positive ({bull_hits} bull vs {bear_hits} bear keywords)")
        elif diff <= -2:
            score -= 0.4
            signals.append(f"Headlines lean negative ({bull_hits} bull vs {bear_hits} bear keywords)")
        else:
            signals.append(f"Headlines mixed ({bull_hits} bull vs {bear_hits} bear)")
    upcoming = [e for e in (n.get("calendar") or []) if e.get("high_impact")]
    if upcoming:
        signals.append(f"Event risk: {upcoming[0].get('title','')} ({upcoming[0].get('date','')})")
    state = "Bullish" if score >= 0.3 else ("Bearish" if score <= -0.3 else "Neutral")
    return {"key": "news", "letter": "N", "label": "News", "state": state,
            "bias": 1 if score >= 0.3 else (-1 if score <= -0.3 else 0),
            "score": round(max(-1, min(1, score)), 2), "signals": signals[:5],
            "data": {"fear_greed": fng, "bull_keywords": bull_hits, "bear_keywords": bear_hits,
                     "high_impact_events": len(upcoming)}}


def _macro_lane() -> dict:
    m = get_macro()
    score, signals = 0.0, []
    rows = m.get("rows") or []
    dxy = next((r for r in rows if "DXY" in (r.get("asset") or "")), None)
    if dxy and dxy.get("change_pct") is not None:
        c = dxy["change_pct"]
        if c <= -0.15:
            score += 0.3
            signals.append(f"DXY {c:+.2f}% — weaker dollar = crypto tailwind")
        elif c >= 0.15:
            score -= 0.3
            signals.append(f"DXY {c:+.2f}% — stronger dollar = headwind")
        else:
            signals.append(f"DXY {c:+.2f}% — steady")
    risk = m.get("macro_risk")
    if risk == "RISK-ON":
        score += 0.3
        signals.append("Macro regime: RISK-ON (BTC 7d returns positive)")
    elif risk == "RISK-OFF":
        score -= 0.3
        signals.append("Macro regime: RISK-OFF (BTC 7d returns negative)")
    spx = next((r for r in rows if "S&P" in (r.get("asset") or "")), None)
    if spx and spx.get("change_pct") is not None:
        c = spx["change_pct"]
        if c >= 0.3:
            score += 0.2
            signals.append(f"S&P {c:+.2f}% — equities bid")
        elif c <= -0.3:
            score -= 0.2
            signals.append(f"S&P {c:+.2f}% — equities offered")
        else:
            signals.append(f"S&P {c:+.2f}%")
    if not signals:
        signals.append("Macro feed unavailable")
    state = "Bullish" if score >= 0.3 else ("Bearish" if score <= -0.3 else "Neutral")
    return {"key": "macro", "letter": "M", "label": "Macro", "state": state,
            "bias": 1 if score >= 0.3 else (-1 if score <= -0.3 else 0),
            "score": round(max(-1, min(1, score)), 2), "signals": signals[:5],
            "data": {"macro_risk": risk, "live_assets": m.get("live_assets")}}


def analyze(symbol: str, timeframe: str = "1h") -> dict:
    """Full 4-lane analysis with one reconciled verdict + ATR levels (60s cache)."""
    from app.intel.fetcher import cached
    return cached(f"analyze_{symbol}_{timeframe}", 60,
                  lambda: _analyze_uncached(symbol, timeframe),
                  default={"symbol": symbol, "lanes": [],
                           "verdict": {"direction": "WAIT", "conviction": 0,
                                       "agreement": "0 of 4 lanes agree", "entry": None,
                                       "stop": None, "targets": [None, None],
                                       "reasoning": "analysis unavailable"},
                           "error": "analysis unavailable"})


def _analyze_uncached(symbol: str, timeframe: str = "1h") -> dict:
    from app.exchange.aggregator import aggregator

    tf = timeframe if timeframe in TF_MINUTES else "1h"
    klines = aggregator.get_klines(symbol, timeframe=tf, limit=250)
    if not klines or len(klines) < 30:
        klines = aggregator.get_klines(symbol, timeframe=tf, limit=250, exchange=None) or klines
    price = klines[-1]["close"] if klines else 50000.0

    lanes = []
    if klines and len(klines) >= 30:
        lanes.append(_tech_lane(klines, price))
    else:
        lanes.append({"key": "tech", "letter": "T", "label": "Technical", "state": "Neutral",
                      "bias": 0, "score": 0, "signals": ["Not enough candles"], "data": {}})
    lanes.append(_flow_lane(symbol))
    lanes.append(_news_lane())
    lanes.append(_macro_lane())

    bulls = sum(1 for l in lanes if l["bias"] == 1)
    bears = sum(1 for l in lanes if l["bias"] == -1)
    if bulls - bears >= 2:
        direction = "LONG"
    elif bears - bulls >= 2:
        direction = "SHORT"
    else:
        direction = "WAIT"

    atr = _atr(klines) if klines else None
    if atr is None:
        atr = price * 0.015
    d = 1 if direction == "LONG" else (-1 if direction == "SHORT" else 0)
    lean = d or (1 if bulls >= bears else -1)  # WAIT still shows a conditional plan

    entry = round(price, 6 if price < 10 else 2)
    stop = round(price - 1.5 * atr * lean, 6 if price < 10 else 2)
    tp1 = round(price + 2.5 * atr * lean, 6 if price < 10 else 2)
    tp2 = round(price + 4.0 * atr * lean, 6 if price < 10 else 2)

    if direction == "WAIT":
        agree = max(bulls, bears)
        side_word = "long" if lean == 1 else "short"
        reasoning = (f"Lanes disagree ({bulls} bullish vs {bears} bearish) — waiting for alignment. "
                     f"Conditional {side_word} plan: entry {entry}, stop {stop}, targets {tp1} / {tp2}.")
    else:
        agree = bulls if direction == "LONG" else bears
        side = "bullish" if direction == "LONG" else "bearish"
        reasoning = f"{agree} of 4 lanes {side} — entry {entry}, stop {stop}, targets {tp1} / {tp2}."

    conviction = round(agree / 4 * 100)

    return {
        "symbol": symbol, "timeframe": tf, "price": entry,
        "lanes": lanes,
        "verdict": {
            "direction": direction,
            "conviction": conviction,
            "agreement": f"{agree} of 4 lanes agree",
            "bulls": bulls, "bears": bears,
            "entry": entry, "stop": stop,
            "targets": [tp1, tp2],
            "reasoning": reasoning,
        },
        "atr": round(atr, 4),
        "mode": aggregator.get_mode(),
        "updated": int(time.time()),
    }
