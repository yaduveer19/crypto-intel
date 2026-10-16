"""Derivatives intel — OI series, taker volume, Coinbase premium.
Binance fapi REST works from this network (verified); Coinbase falls back to
an explicit estimated/blocked flag if unreachable."""
from app.intel.fetcher import cached, get_json


def oi_series(symbol: str, period: str = "1h", limit: int = 48) -> dict:
    def build():
        err = None
        d = None
        try:
            d = get_json("https://fapi.binance.com/futures/data/openInterestHist",
                         params={"symbol": symbol, "period": period, "limit": min(limit, 500)},
                         timeout=10)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        rows = []
        if isinstance(d, list):
            for x in d:
                try:
                    rows.append({"time": int(x["timestamp"]) // 1000,
                                 "oi": float(x["sumOpenInterest"]),
                                 "oi_value": float(x["sumOpenInterestValue"])})
                except Exception:
                    continue
        elif isinstance(d, dict):
            err = str(d.get("msg", d))[:200]
        chg = None
        if len(rows) >= 2 and rows[0]["oi"]:
            chg = round((rows[-1]["oi"] / rows[0]["oi"] - 1) * 100, 3)
        out = {"symbol": symbol, "period": period, "series": rows,
               "oi_change_pct": chg, "latest_oi": rows[-1] if rows else None,
               "live": bool(rows), "source": "Binance fapi"}
        if err and not rows:
            out["error"] = err
        return out

    return cached(f"oi_{symbol}_{period}_{limit}", 60, build,
                  default={"series": [], "live": False, "symbol": symbol})


def taker_volume(symbol: str, period: str = "1h", limit: int = 24) -> dict:
    def build():
        err = None
        d = None
        try:
            d = get_json("https://fapi.binance.com/futures/data/takerlongshortRatio",
                         params={"symbol": symbol, "period": period, "limit": min(limit, 500)},
                         timeout=10)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        rows = []
        if isinstance(d, list):
            for x in d:
                try:
                    rows.append({"time": int(x["timestamp"]) // 1000,
                                 "ratio": float(x["buySellRatio"]),
                                 "buy_vol": float(x["buyVol"]), "sell_vol": float(x["sellVol"])})
                except Exception:
                    continue
        elif isinstance(d, dict):
            err = str(d.get("msg", d))[:200]
        avg = round(sum(r["ratio"] for r in rows) / len(rows), 4) if rows else None
        bias = None
        if avg is not None:
            bias = "BUYERS" if avg >= 1.05 else ("SELLERS" if avg <= 0.95 else "BALANCED")
        out = {"symbol": symbol, "period": period, "series": rows,
               "avg_ratio": avg, "bias": bias, "live": bool(rows), "source": "Binance fapi"}
        if err and not rows:
            out["error"] = err
        return out

    return cached(f"taker_{symbol}_{period}_{limit}", 60, build,
                  default={"series": [], "live": False, "symbol": symbol})


def coinbase_premium(symbol: str = "BTCUSDT") -> dict:
    """Coinbase spot vs Binance — the Coinbase Premium Index (institutional US bid)."""
    def build():
        result = {"symbol": symbol, "live": False, "premium_pct": None, "note": None}
        if not symbol.startswith("BTC"):
            result["note"] = "Premium tracked for BTC only"
            return result
        cb = get_json("https://api.exchange.coinbase.com/products/BTC-USD/ticker", timeout=8)
        bn = get_json("https://fapi.binance.com/fapi/v1/premiumIndex",
                      params={"symbol": "BTCUSDT"}, timeout=8)
        try:
            cb_px = float(cb["price"])
            # binance spot for apples-to-apples premium
            bn_spot = get_json("https://api.binance.com/api/v3/ticker/price",
                               params={"symbol": "BTCUSDT"}, timeout=8)
            bn_px = float(bn_spot["price"])
            prem = (cb_px / bn_px - 1) * 100
            result.update({"coinbase_price": cb_px, "binance_price": bn_px,
                           "premium_pct": round(prem, 4), "live": True,
                           "signal": "INSTITUTIONAL BID" if prem > 0.05 else
                                     ("DISTRIBUTION" if prem < -0.05 else "NEUTRAL"),
                           "note": None})
        except Exception:
            result["note"] = "Coinbase unreachable from this network — premium estimated unavailable"
            if bn:
                try:
                    result["binance_mark"] = float(bn.get("markPrice"))
                except Exception:
                    pass
        return result

    return cached("cb_premium", 60, build, default={"live": False, "premium_pct": None})
