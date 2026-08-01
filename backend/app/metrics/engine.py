"""Metrics Engine — computes all market microstructure metrics for a symbol
from raw data sources (klines, trades, orderbook snapshots)."""

import logging
import time
from typing import List, Dict, Optional

from app.metrics.cvd import compute_cvd, compute_delta_profile, cvd_divergence_signal
from app.metrics.footprint import footprint_from_trades, tpo_profile
from app.metrics.volume_profile import volume_profile_from_trades, vwap_from_klines
from app.metrics.orderbook_heatmap import heatmap_from_snapshots

logger = logging.getLogger(__name__)


def build_all(
    symbol: str,
    klines: List[dict] = None,
    trades: List[dict] = None,
    ob_snapshots: List[dict] = None,
    mode: str = "simulated",
) -> Dict:
    """Compute everything for one symbol. Any missing input degrades gracefully."""
    klines = klines or []
    trades = trades or []
    ob_snapshots = ob_snapshots or []

    result = {
        "symbol": symbol,
        "mode": mode,
        "time": int(time.time()),
        "cvd": {"series": [], "delta_profile": [], "signal": None},
        "footprint": [],
        "tpo": [],
        "volume_profile": {"levels": [], "poc": None, "value_area": {"high": None, "low": None}, "vwap": None},
        "vwap_line": [],
        "orderbook_heatmap": {"rows": [], "max_depth": 0},
    }

    if trades:
        result["cvd"]["series"] = compute_cvd(trades)
        result["cvd"]["delta_profile"] = compute_delta_profile(trades)
        result["cvd"]["signal"] = cvd_divergence_signal(klines, result["cvd"]["series"]) if klines else None
        result["footprint"] = footprint_from_trades(trades)
        result["tpo"] = tpo_profile(trades)
        result["volume_profile"] = volume_profile_from_trades(trades)

    if klines:
        result["vwap_line"] = vwap_from_klines(klines)
        if not result["volume_profile"]["vwap"] and result["vwap_line"]:
            result["volume_profile"]["vwap"] = result["vwap_line"][-1]["vwap"]

    if ob_snapshots:
        result["orderbook_heatmap"] = heatmap_from_snapshots(ob_snapshots)

    return result
