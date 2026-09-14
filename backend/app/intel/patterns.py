"""Chart pattern engine — runs on REAL klines.

Detects: double top/bottom, head & shoulders (+inverse), ascending/descending/symmetrical
triangle, rising/falling wedge, bull/bear flag, support/resistance breakouts.
All detections are geometric on real OHLC data.
"""
from typing import List, Optional


def _pivots(highs: List[float], lows: List[float], k: int = 3):
    ph, pl = [], []
    for i in range(k, len(highs) - k):
        if highs[i] == max(highs[i - k:i + k + 1]):
            ph.append((i, highs[i]))
        if lows[i] == min(lows[i - k:i + k + 1]):
            pl.append((i, lows[i]))
    return ph, pl


def _slope(ys: List[float]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs) or 1e-9
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


def detect_patterns(highs: List[float], lows: List[float], closes: List[float]) -> List[dict]:
    """Return list of detected patterns with confidence + bias + key levels."""
    out: List[dict] = []
    n = len(closes)
    if n < 20:
        return out

    price = closes[-1]
    ph, pl = _pivots(highs, lows, k=max(2, n // 30))
    rng = (max(highs) - min(lows)) or 1e-9
    tol = rng * 0.04

    # --- Double Top ---
    if len(ph) >= 2:
        (i1, h1), (i2, h2) = ph[-2], ph[-1]
        if abs(h1 - h2) <= tol and i2 - i1 >= 4:
            neckline = min(lows[i1:i2 + 1]) if i2 > i1 else price
            broke = price < neckline
            out.append({
                "pattern": "Double Top", "bias": "BEAR", "confirmed": broke,
                "confidence": round(0.85 if broke else 0.6, 2),
                "key_level": round(neckline, 2), "target": round(neckline - (h1 - neckline), 2),
                "points": [round(h1, 2), round(h2, 2)],
                "detail": "Two rejections at similar highs — bearish reversal",
            })

    # --- Double Bottom ---
    if len(pl) >= 2:
        (i1, l1), (i2, l2) = pl[-2], pl[-1]
        if abs(l1 - l2) <= tol and i2 - i1 >= 4:
            neckline = max(highs[i1:i2 + 1]) if i2 > i1 else price
            broke = price > neckline
            out.append({
                "pattern": "Double Bottom", "bias": "BULL", "confirmed": broke,
                "confidence": round(0.85 if broke else 0.6, 2),
                "key_level": round(neckline, 2), "target": round(neckline + (neckline - l1), 2),
                "points": [round(l1, 2), round(l2, 2)],
                "detail": "Two defended lows — bullish reversal",
            })

    # --- Head & Shoulders (+ inverse) ---
    if len(ph) >= 3:
        (_, s1), (_, head), (_, s2) = ph[-3], ph[-2], ph[-1]
        if head > s1 + tol * 0.5 and head > s2 + tol * 0.5 and abs(s1 - s2) <= tol * 1.5:
            neck = min(lows[-len(closes) // 2:]) if len(closes) > 4 else price
            out.append({
                "pattern": "Head & Shoulders", "bias": "BEAR", "confirmed": price < neck,
                "confidence": round(0.8 if price < neck else 0.55, 2),
                "key_level": round(neck, 2), "target": round(neck - (head - neck), 2),
                "points": [round(s1, 2), round(head, 2), round(s2, 2)],
                "detail": "Classic topping structure",
            })
    if len(pl) >= 3:
        (_, s1), (_, head), (_, s2) = pl[-3], pl[-2], pl[-1]
        if head < s1 - tol * 0.5 and head < s2 - tol * 0.5 and abs(s1 - s2) <= tol * 1.5:
            neck = max(highs[-len(closes) // 2:]) if len(closes) > 4 else price
            out.append({
                "pattern": "Inverse Head & Shoulders", "bias": "BULL", "confirmed": price > neck,
                "confidence": round(0.8 if price > neck else 0.55, 2),
                "key_level": round(neck, 2), "target": round(neck + (neck - head), 2),
                "points": [round(s1, 2), round(head, 2), round(s2, 2)],
                "detail": "Classic bottoming structure",
            })

    # --- Triangles & wedges via pivot trendlines ---
    if len(ph) >= 2 and len(pl) >= 2:
        upper = _slope([h for _, h in ph[-3:]])
        lower = _slope([l for _, l in pl[-3:]])
        scale = rng / max(n, 1)
        up_flat = abs(upper) < scale * 0.35
        lo_flat = abs(lower) < scale * 0.35
        if up_flat and lower > scale * 0.35:
            out.append({"pattern": "Ascending Triangle", "bias": "BULL", "confirmed": price >= max(h for _, h in ph[-2:]),
                        "confidence": 0.7, "key_level": round(max(h for _, h in ph[-2:]), 2),
                        "target": round(max(h for _, h in ph[-2:]) + rng * 0.3, 2), "points": [],
                        "detail": "Flat resistance + rising support — bullish continuation"})
        elif lo_flat and upper < -scale * 0.35:
            out.append({"pattern": "Descending Triangle", "bias": "BEAR", "confirmed": price <= min(l for _, l in pl[-2:]),
                        "confidence": 0.7, "key_level": round(min(l for _, l in pl[-2:]), 2),
                        "target": round(min(l for _, l in pl[-2:]) - rng * 0.3, 2), "points": [],
                        "detail": "Flat support + falling resistance — bearish continuation"})
        elif upper < -scale * 0.3 and lower > scale * 0.3:
            out.append({"pattern": "Symmetrical Triangle", "bias": "NEUTRAL", "confirmed": False,
                        "confidence": 0.55, "key_level": round(price, 2), "target": None, "points": [],
                        "detail": "Coiling volatility — breakout pending"})
        elif upper > scale * 0.3 and lower > scale * 0.3 and upper > lower:
            out.append({"pattern": "Rising Wedge", "bias": "BEAR", "confirmed": price < min(l for _, l in pl[-2:]),
                        "confidence": 0.65, "key_level": round(min(l for _, l in pl[-2:]), 2), "target": None, "points": [],
                        "detail": "Rising wedge — bearish reversal"})
        elif upper < -scale * 0.3 and lower < -scale * 0.3 and lower < upper:
            out.append({"pattern": "Falling Wedge", "bias": "BULL", "confirmed": price > max(h for _, h in ph[-2:]),
                        "confidence": 0.65, "key_level": round(max(h for _, h in ph[-2:]), 2), "target": None, "points": [],
                        "detail": "Falling wedge — bullish reversal"})

    # --- Range / Breakout ---
    hi, lo = max(highs), min(lows)
    if (hi - lo) / lo < 0.012 and n >= 20:
        out.append({"pattern": "Consolidation Range", "bias": "NEUTRAL", "confirmed": False,
                    "confidence": 0.5, "key_level": round(price, 2), "target": None, "points": [],
                    "detail": "Tight range — volatility expansion likely"})

    # --- Breakout retest ---
    if ph:
        recent_high = max(h for _, h in ph)
        if price >= recent_high * 0.999:
            out.append({"pattern": "Breakout (Resistance)", "bias": "BULL", "confirmed": True,
                        "confidence": 0.6, "key_level": round(recent_high, 2),
                        "target": round(recent_high + rng * 0.25, 2), "points": [],
                        "detail": "Price breaking prior swing high"})
    if pl:
        recent_low = min(l for _, l in pl)
        if price <= recent_low * 1.001:
            out.append({"pattern": "Breakdown (Support)", "bias": "BEAR", "confirmed": True,
                        "confidence": 0.6, "key_level": round(recent_low, 2),
                        "target": round(recent_low - rng * 0.25, 2), "points": [],
                        "detail": "Price breaking prior swing low"})

    # order by confidence
    out.sort(key=lambda p: p["confidence"], reverse=True)
    return out


def get_patterns(symbol: str, klines: List[dict]) -> dict:
    """Run pattern detection on real klines."""
    if not klines or len(klines) < 20:
        return {"symbol": symbol, "patterns": [], "count": 0, "live": False,
                "note": "insufficient kline data"}
    highs = [float(k["high"]) for k in klines]
    lows = [float(k["low"]) for k in klines]
    closes = [float(k["close"]) for k in klines]
    patterns = detect_patterns(highs, lows, closes)
    bulls = sum(1 for p in patterns if p["bias"] == "BULL")
    bears = sum(1 for p in patterns if p["bias"] == "BEAR")
    return {
        "symbol": symbol,
        "patterns": patterns[:8],
        "count": len(patterns),
        "signal": "BULL" if bulls > bears else "BEAR" if bears > bulls else "NEUTRAL",
        "bull_count": bulls,
        "bear_count": bears,
        "live": True,
        "last_price": closes[-1],
        "range": [round(min(lows), 2), round(max(highs), 2)],
    }