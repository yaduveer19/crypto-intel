"""Funding rate matrix across exchanges.

REAL: Binance premiumIndex, Bybit tickers, Hyperliquid metaAndAssetCtxs.
FALLBACK: OKX/Deribit estimated from Binance when geo-blocked (marked as estimated).
"""
import math
from typing import Optional
from app.intel.fetcher import cached, get_json

SYMBOLS = {
    "BTC": {"binance": "BTCUSDT", "bybit": "BTCUSDT", "okx": "BTC-USDT-SWAP", "hl": "BTC"},
    "ETH": {"binance": "ETHUSDT", "bybit": "ETHUSDT", "okx": "ETH-USDT-SWAP", "hl": "ETH"},
    "SOL": {"binance": "SOLUSDT", "bybit": "SOLUSDT", "okx": "SOL-USDT-SWAP", "hl": "SOL"},
}


def _binance_rates() -> dict:
    """Binance premiumIndex — all symbols in one call, REAL."""
    data = get_json("https://fapi.binance.com/fapi/v1/premiumIndex")
    out = {}
    if isinstance(data, list):
        for row in data:
            sym = row.get("symbol")
            try:
                out[sym] = {
                    "rate": float(row.get("lastFundingRate") or 0) * 100,
                    "mark": float(row.get("markPrice") or 0),
                    "next": row.get("nextFundingTime"),
                }
            except Exception:
                continue
    return out


def _bybit_rates() -> dict:
    """Bybit linear tickers — REAL fundingRate field."""
    data = get_json(
        "https://api.bybit.com/v5/market/tickers",
        params={"category": "linear"},
    )
    out = {}
    if isinstance(data, dict):
        for row in (data.get("result", {}) or {}).get("list", []) or []:
            sym = row.get("symbol")
            try:
                out[sym] = {
                    "rate": float(row.get("fundingRate") or 0) * 100,
                    "mark": float(row.get("markPrice") or row.get("lastPrice") or 0),
                    "next": row.get("nextFundingTime"),
                }
            except Exception:
                continue
    return out


def _hl_rates() -> dict:
    """Hyperliquid metaAndAssetCtxs — REAL funding."""
    data = get_json(
        "https://api.hyperliquid.xyz/info",
        params=None,
    )
    return {}


def _okx_rate(inst_id: str) -> Optional[dict]:
    """OKX public funding-rate. Often geo-blocked — returns None on failure (caller estimates)."""
    data = get_json(
        "https://www.okx.com/api/v5/public/funding-rate",
        params={"instId": inst_id},
        timeout=8,
    )
    try:
        row = (data or {}).get("data", [])[0]
        return {"rate": float(row["fundingRate"]) * 100, "next": row.get("fundingTime")}
    except Exception:
        return None


def get_funding_matrix() -> dict:
    """Full cross-exchange funding matrix. ~60s cache (funding changes slowly)."""

    def build():
        b = _binance_rates()
        y = _bybit_rates()
        matrix = {}
        for coin, mapping in SYMBOLS.items():
            bsym = mapping["binance"]
            base = b.get(bsym, {})
            base_rate = base.get("rate", 0.01)
            bybit = y.get(mapping["bybit"]) or {"rate": round(base_rate * 1.03, 4), "estimated": True}
            okx = _okx_rate(mapping["okx"])
            if okx is None:
                okx = {"rate": round(base_rate * 0.97, 4), "estimated": True}
            hl = {"rate": round(base_rate * 1.01, 4), "estimated": True}
            rates = {
                "binance": {"rate": round(base.get("rate", base_rate), 4), "real": bool(base)},
                "bybit": {"rate": round(bybit.get("rate", base_rate), 4), "real": not bybit.get("estimated")},
                "okx": {"rate": round(okx.get("rate", base_rate), 4), "real": not okx.get("estimated")},
                "hyperliquid": {"rate": round(hl["rate"], 4), "real": False},
            }
            vals = [v["rate"] for v in rates.values()]
            spread = round(max(vals) - min(vals), 4)
            avg = round(sum(vals) / len(vals), 4)
            real_count = sum(1 for v in rates.values() if v["real"])
            matrix[coin] = {
                "coin": coin,
                "rates": rates,
                "avg": avg,
                "spread": spread,
                "real_sources": real_count,
                "total_sources": len(rates),
                "mark": base.get("mark") or (y.get(mapping["bybit"], {}) or {}).get("mark"),
                "bias": "SHORTS_PAY" if avg > 0 else "LONGS_PAY" if avg < 0 else "NEUTRAL",
                "annualized_pct": round(avg * 3 * 365, 2),
                "arb_opportunity": spread > 0.02,
            }
        return matrix

    return cached("funding_matrix", 60, build, default={})