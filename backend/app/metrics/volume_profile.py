"""Volume Profile — volume per price level, value area, POC, VWAP."""

from typing import List, Dict


def volume_profile_from_trades(trades: List[dict], buckets: int = 30) -> Dict:
    """Volume profile from trade tape. Returns levels + value area stats."""
    if not trades:
        return {"levels": [], "poc": None, "value_area": {"high": None, "low": None}, "vwap": None}
    prices = [t["price"] for t in trades]
    lo, hi = min(prices), max(prices)
    if hi == lo:
        hi = lo + 1e-6
    step = (hi - lo) / buckets
    levels = {}
    total_vol = 0.0
    vwap_num = 0.0
    for t in trades:
        b = int((t["price"] - lo) / step)
        b = min(b, buckets - 1)
        entry = levels.setdefault(b, {"buy": 0.0, "sell": 0.0})
        if str(t.get("side", "BUY")).upper() == "BUY":
            entry["buy"] += t["amount"]
        else:
            entry["sell"] += t["amount"]
        total_vol += t["amount"]
        vwap_num += t["price"] * t["amount"]
    levels_out = []
    for b in sorted(levels):
        entry = levels[b]
        vol = entry["buy"] + entry["sell"]
        levels_out.append({
            "price": round(lo + (b + 0.5) * step, 2),
            "volume": round(vol, 4),
            "buy_vol": round(entry["buy"], 4),
            "sell_vol": round(entry["sell"], 4),
            "buy_pct": round(entry["buy"] / vol * 100, 1) if vol else 50.0,
        })
    if not levels_out:
        return {"levels": [], "poc": None, "value_area": {"high": None, "low": None}, "vwap": None}
    poc = max(levels_out, key=lambda r: r["volume"])
    total_vol = sum(r["volume"] for r in levels_out)
    sorted_by_vol = sorted(levels_out, key=lambda r: r["volume"], reverse=True)
    cumulative = 0.0
    va_prices = []
    for r in sorted_by_vol:
        cumulative += r["volume"]
        va_prices.append(r["price"])
        if cumulative / total_vol >= 0.70:
            break
    return {
        "levels": levels_out,
        "poc": poc["price"],
        "poc_volume": poc["volume"],
        "value_area": {"high": max(va_prices), "low": min(va_prices)},
        "vwap": round(vwap_num / total_vol, 2) if total_vol else None,
    }


def vwap_from_klines(klines: List[dict]) -> List[dict]:
    """Session VWAP line from klines: [{time, vwap, cumulative_vol}]"""
    out = []
    cum_pv = 0.0
    cum_v = 0.0
    for k in klines:
        typ = (k["high"] + k["low"] + k["close"]) / 3
        vol = k.get("volume", 0) or 0
        cum_pv += typ * vol
        cum_v += vol
        out.append({"time": k["time"], "vwap": round(cum_pv / cum_v, 2) if cum_v else k["close"]})
    return out
