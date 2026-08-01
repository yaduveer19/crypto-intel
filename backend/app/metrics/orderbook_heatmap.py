"""Orderbook Heatmap — builds price×time heatmap of bid/ask depth from snapshots."""

from typing import List, Dict


def heatmap_from_snapshots(snapshots: List[dict], price_buckets: int = 25, time_buckets: int = 30) -> Dict:
    """snapshots: [{time, bids: [[px, qty]], asks: [[px, qty]]}] sorted by time.
    Returns heatmap grid rows: {price, cells: [{t, depth, side}]} + max_depth."""
    if not snapshots:
        return {"rows": [], "max_depth": 0}
    all_px = []
    for s in snapshots:
        all_px += [p[0] for p in s.get("bids", [])] + [p[0] for p in s.get("asks", [])]
    if not all_px:
        return {"rows": [], "max_depth": 0}
    lo, hi = min(all_px), max(all_px)
    if hi == lo:
        hi = lo + 1e-6
    step = (hi - lo) / price_buckets
    t0 = snapshots[0].get("time") or snapshots[0].get("timestamp") or 0
    t1 = snapshots[-1].get("time") or snapshots[-1].get("timestamp") or t0
    span = max((t1 - t0) / time_buckets, 1)
    grid = {}
    for s in snapshots:
        tb = int(((s.get("time") or s.get("timestamp") or 0) - t0) / span)
        tb = min(tb, time_buckets - 1)
        for side, rows in (("bid", s.get("bids", [])), ("ask", s.get("asks", []))):
            for px, qty in rows:
                pb = int((px - lo) / step)
                pb = min(pb, price_buckets - 1)
                cell = grid.setdefault(pb, {})
                entry = cell.setdefault(tb, {"depth": 0.0})
                entry["depth"] += qty
                if side == "bid":
                    entry.setdefault("bids", 0.0)
                    entry["bids"] += qty
                else:
                    entry.setdefault("asks", 0.0)
                    entry["asks"] += qty
    rows = []
    max_depth = 0
    for pb in sorted(grid):
        cells = []
        for tb in range(time_buckets):
            cell = grid[pb].get(tb)
            if cell:
                depth = round(cell["depth"], 4)
                max_depth = max(max_depth, depth)
                cells.append({
                    "t": tb,
                    "depth": depth,
                    "bids": round(cell.get("bids", 0), 4),
                    "asks": round(cell.get("asks", 0), 4),
                    "imbalance": round((cell.get("bids", 0) - cell.get("asks", 0)) / max(depth, 1e-9), 2),
                })
            else:
                cells.append({"t": tb, "depth": 0.0, "bids": 0.0, "asks": 0.0, "imbalance": 0.0})
        rows.append({"price": round(lo + (pb + 0.5) * step, 2), "cells": cells})
    return {"rows": rows, "max_depth": max_depth, "price_min": round(lo, 2), "price_max": round(hi, 2)}
