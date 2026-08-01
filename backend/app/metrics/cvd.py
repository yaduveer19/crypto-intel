"""Cumulative Volume Delta — tracks buyer/seller aggression from the trade tape."""

from typing import List, Dict, Optional


def compute_cvd(trades: List[dict], limit: int = None) -> List[dict]:
    """trades: [{time, price, amount, side}] sorted ascending by time.
    Returns per-trade running delta: [{time, price, cvd}] where cvd is cumulative
    (buy volume - sell volume) in base-currency terms."""
    if not trades:
        return []
    if limit:
        trades = trades[-limit:]
    cvd = 0.0
    out = []
    for t in trades:
        signed = t["amount"] if str(t.get("side", "BUY")).upper() == "BUY" else -t["amount"]
        cvd += signed
        out.append({"time": t.get("time"), "price": t.get("price"), "cvd": round(cvd, 6)})
    return out


def compute_delta_profile(trades: List[dict], bins: int = 24) -> List[dict]:
    """Bucket trades by time into N bins, return per-bin net delta and volume."""
    if not trades:
        return []
    t0 = trades[0]["time"]
    t1 = trades[-1]["time"]
    span = max((t1 - t0) / bins, 1)
    bins_out = []
    for i in range(bins):
        start = t0 + i * span
        end = start + span
        bucket = [t for t in trades if start <= t["time"] < end]
        buy = sum(t["amount"] for t in bucket if str(t.get("side", "BUY")).upper() == "BUY")
        sell = sum(t["amount"] for t in bucket if str(t.get("side", "BUY")).upper() == "SELL")
        bins_out.append({
            "bin": i,
            "start": int(start),
            "end": int(end),
            "buy_vol": round(buy, 4),
            "sell_vol": round(sell, 4),
            "net_delta": round(buy - sell, 4),
            "volume": round(buy + sell, 4),
        })
    return bins_out


def cvd_divergence_signal(klines: List[dict], cvd_series: List[dict], lookback: int = 20) -> Dict:
    """Compare price trend vs CVD trend over lookback bars.
    Returns: {"divergence": "bullish"|"bearish"|"none", "strength": 0-1, "message": str}"""
    if len(klines) < lookback or len(cvd_series) < lookback:
        return {"divergence": "none", "strength": 0.0, "message": "Not enough data"}
    price_start = klines[-lookback]["close"]
    price_end = klines[-1]["close"]
    cvd_start = cvd_series[-lookback]["cvd"]
    cvd_end = cvd_series[-1]["cvd"]
    price_up = price_end > price_start
    cvd_up = cvd_end > cvd_start
    price_change = abs(price_end - price_start) / max(price_start, 1e-9)
    if price_up and not cvd_up:
        return {"divergence": "bearish", "strength": min(1, price_change * 8), "message": "Price making new highs but CVD falling — weak buying conviction, reversal risk"}
    if not price_up and cvd_up:
        return {"divergence": "bullish", "strength": min(1, price_change * 8), "message": "Price dipping but CVD rising — accumulation underway, reversal potential"}
    return {"divergence": "none", "strength": 0.0, "message": "Price and CVD aligned — no divergence"}
