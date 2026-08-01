"""Footprint / TPO chart data — per-price-level buy vs sell volume from the tape."""

from typing import List, Dict


def footprint_from_trades(trades: List[dict], bins: int = 10, tick_size: float = None) -> List[dict]:
    """Aggregate trades into (price bucket × time bin) footprint grid.
    Returns list of rows: {price, time_bin, buy_vol, sell_vol, delta, total}"""
    if not trades:
        return []
    prices = [t["price"] for t in trades]
    lo, hi = min(prices), max(prices)
    if hi == lo:
        hi = lo + 1e-6
    tick = tick_size or ((hi - lo) / bins)
    t0 = trades[0]["time"]
    t1 = trades[-1]["time"]
    span = max((t1 - t0) / bins, 1)
    rows = []
    for t in trades:
        bucket = int((t["price"] - lo) / tick)
        bucket = min(bucket, bins - 1)
        bin_idx = int((t["time"] - t0) / span)
        bin_idx = min(bin_idx, bins - 1)
        is_buy = str(t.get("side", "BUY")).upper() == "BUY"
        rows.append({
            "price_bucket": bucket,
            "time_bin": bin_idx,
            "is_buy": is_buy,
            "amount": t["amount"],
        })
    grid = {}
    for r in rows:
        key = (r["price_bucket"], r["time_bin"])
        cell = grid.setdefault(key, {"buy": 0.0, "sell": 0.0})
        if r["is_buy"]:
            cell["buy"] += r["amount"]
        else:
            cell["sell"] += r["amount"]
    out = []
    for (pb, tb), cell in sorted(grid.items()):
        buy, sell = cell["buy"], cell["sell"]
        price = lo + (pb + 0.5) * tick
        out.append({
            "price": round(price, 2),
            "time_bin": tb,
            "buy_vol": round(buy, 4),
            "sell_vol": round(sell, 4),
            "delta": round(buy - sell, 4),
            "total": round(buy + sell, 4),
            "poc": False,
        })
    if out:
        max_total = max(r["total"] for r in out)
        for r in out:
            if r["total"] == max_total:
                r["poc"] = True
    return out


def tpo_profile(trades: List[dict], tick_size: float = None) -> List[dict]:
    """Market Profile (TPO) — time price opportunity per price level.
    Returns: [{price, tpo_count, volume, buy_pct}]"""
    if not trades:
        return []
    prices = [t["price"] for t in trades]
    lo, hi = min(prices), max(prices)
    if hi == lo:
        hi = lo + 1e-6
    tick = tick_size or ((hi - lo) / 50)
    levels = {}
    for t in trades:
        bucket = int((t["price"] - lo) / tick)
        level = levels.setdefault(bucket, {"tpo": set(), "buy": 0.0, "sell": 0.0})
        level["tpo"].add(int(t["time"] / 600))  # 10-min TPO letters
        if str(t.get("side", "BUY")).upper() == "BUY":
            level["buy"] += t["amount"]
        else:
            level["sell"] += t["amount"]
    out = []
    for bucket, level in sorted(levels.items()):
        total = level["buy"] + level["sell"]
        out.append({
            "price": round(lo + (bucket + 0.5) * tick, 2),
            "tpo_count": len(level["tpo"]),
            "volume": round(total, 4),
            "buy_pct": round(level["buy"] / total * 100, 1) if total else 50.0,
        })
    return out
