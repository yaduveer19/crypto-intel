"""Macro correlation engine — REAL prices, REAL computed correlations.

Assets:
- BTC     → Binance klines
- ETH     → Binance klines
- Gold    → PAXGUSDT (tokenised gold, Binance)
- DXY     → Yahoo Finance DX-Y.NYB
- S&P 500 → Yahoo Finance ^GSPC
- Nasdaq  → Yahoo Finance ^IXIC

Correlation computed with Pearson coeff on daily returns (no hardcoded numbers).
"""
import math
from typing import List, Optional
from app.intel.fetcher import cached, get_json


def _pearson(a: List[float], b: List[float]) -> Optional[float]:
    n = min(len(a), len(b))
    if n < 5:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a)) or 1e-9
    db = math.sqrt(sum((y - mb) ** 2 for y in b)) or 1e-9
    return max(-1.0, min(1.0, num / (da * db)))


def _returns(vals: List[float]) -> List[float]:
    return [(vals[i] / vals[i - 1] - 1) for i in range(1, len(vals)) if vals[i - 1]]


def _yahoo(ticker: str) -> List[float]:
    d = get_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": "3mo", "interval": "1d"},
    )
    try:
        res = d["chart"]["result"][0]
        closes = res["indicators"]["quote"][0]["close"]
        return [float(c) for c in closes if c is not None]
    except Exception:
        return []


def _binance_daily(symbol: str) -> List[float]:
    d = get_json("https://api.binance.com/api/v3/klines",
                 params={"symbol": symbol, "interval": "1d", "limit": "90"})
    try:
        return [float(k[4]) for k in d]
    except Exception:
        return []


def get_macro(btc_klines: Optional[list] = None) -> dict:

    def build():
        btc = [float(k["close"]) for k in btc_klines] if btc_klines else _binance_daily("BTCUSDT")
        if not btc:
            btc = _binance_daily("BTCUSDT")
        eth = _binance_daily("ETHUSDT")
        gold = _binance_daily("PAXGUSDT")
        dxy = _yahoo("DX-Y.NYB")
        spx = _yahoo("%5EGSPC")
        ndx = _yahoo("%5EIXIC")

        btc_r = _returns(btc)
        assets = [
            ("Gold (PAXG)", gold, "Risk-off hedge"),
            ("DXY (Dollar)", dxy, "Inverse liquidity"),
            ("S&P 500", spx, "Risk sentiment"),
            ("Nasdaq", ndx, "Tech beta"),
            ("ETH", eth, "Crypto beta"),
        ]
        rows = []
        for name, series, desc in assets:
            r = _returns(series)
            corr = _pearson(btc_r, r)
            last = series[-1] if series else None
            prev = series[-2] if len(series) > 1 else None
            chg = round((last / prev - 1) * 100, 2) if last and prev else None
            rows.append({
                "asset": name,
                "correlation": round(corr, 3) if corr is not None else None,
                "price": round(last, 4) if last else None,
                "change_pct": chg,
                "relationship": desc,
                "strength": (
                    "STRONG" if corr is not None and abs(corr) >= 0.6 else
                    "MODERATE" if corr is not None and abs(corr) >= 0.3 else
                    "WEAK" if corr is not None else "N/A"
                ),
            })
        live = sum(1 for r in rows if r["correlation"] is not None)
        macro_risk = "RISK-ON" if (btc_r and sum(btc_r[-7:]) > 0) else "RISK-OFF"
        return {"rows": rows, "btc_last": round(btc[-1], 2) if btc else None,
                "macro_risk": macro_risk, "live_assets": live, "total_assets": len(rows),
                "live": live > 0,
                "note": "correlations computed on daily returns (3-month window)"}

    return cached("macro", 300, build, default={})