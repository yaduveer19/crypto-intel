"""Real footprint — buy/sell volume per price level from the actual tape.

Unlike the synthetic generator, this buckets REAL trades by price and time-bin so
the delta (aggression) at each level is genuine.
"""
from typing import List


def build_footprint(trades: List[dict], bins: int = 12, price_buckets: int = 14) -> dict:
    """trades: [{price, qty/amount, side('buy'|'sell') or buyer_maker bool, ts}]"""
    rows = []
    if not trades:
        return {"footprint": [], "bins": [], "live": False, "note": "no trades"}

    parsed = []
    for t in trades:
        try:
            price = float(t.get("price") or 0)
            qty = float(t.get("qty") or t.get("amount") or 0)
        except Exception:
            continue
        if not price or not qty:
            continue
        side = t.get("side")
        if side is None:
            bm = t.get("isBuyerMaker")
            side = "sell" if bm else "buy"
        parsed.append({"price": price, "qty": qty, "side": str(side).lower()})
    if not parsed:
        return {"footprint": [], "bins": [], "live": False, "note": "no parseable trades"}

    prices = [p["price"] for p in parsed]
    lo, hi = min(prices), max(prices)
    span = (hi - lo) or 1e-9
    step = span / price_buckets

    n = len(parsed)
    per_bin = max(1, n // bins)
    cells = {}
    for idx, t in enumerate(parsed):
        tb = min(bins - 1, idx // per_bin)
        bucket = min(price_buckets - 1, int((t["price"] - lo) / step)) if step else 0
        key = (bucket, tb)
        c = cells.setdefault(key, {"buy": 0.0, "sell": 0.0})
        if t["side"] == "buy":
            c["buy"] += t["qty"]
        else:
            c["sell"] += t["qty"]

    max_total = 0.0
    flat = []
    for (bucket, tb), c in cells.items():
        px = lo + (bucket + 0.5) * step
        total = c["buy"] + c["sell"]
        max_total = max(max_total, total)
        flat.append({
            "price": round(px, 2), "time_bin": tb,
            "buy_vol": round(c["buy"], 4), "sell_vol": round(c["sell"], 4),
            "delta": round(c["buy"] - c["sell"], 4), "total": round(total, 4),
        })
    # mark POC (highest total)
    poc = max(flat, key=lambda r: r["total"])["price"] if flat else None
    for r in flat:
        r["poc"] = r["price"] == poc

    tpo = []
    for bucket in range(price_buckets):
        px = lo + (bucket + 0.5) * step
        subset = [r for r in flat if abs(r["price"] - px) < step / 2]
        if not subset:
            continue
        buy = sum(r["buy_vol"] for r in subset)
        sell = sum(r["sell_vol"] for r in subset)
        tot = buy + sell
        tpo.append({
            "price": round(px, 2), "volume": round(tot, 4),
            "buy_pct": round(buy / tot * 100, 1) if tot else 0,
            "tpo_count": len(subset),
        })

    return {
        "footprint": sorted(flat, key=lambda r: (r["price"], r["time_bin"])),
        "tpo": tpo,
        "poc": poc,
        "max_total": round(max_total, 4),
        "live": True,
        "trades_used": n,
        "bins": bins,
        "price_buckets": price_buckets,
    }