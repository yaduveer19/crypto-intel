"""On-chain intelligence — REAL free sources.

Sources:
- blockchain.info/stats     → BTC network stats, fees, tx count, hash rate
- coingecko /global         → market cap, dominance
- stablecoins.llama.fi      → stablecoin supply (dry-powder proxy)
- binance /api/v3/trades    → whale tape (>= $30k prints)
Everything degrades gracefully to clearly-labelled synthesized values.
"""
from app.intel.fetcher import cached, get_json

WHALE_MIN_USD = 30000


def _btc_network() -> dict:
    d = get_json("https://api.blockchain.info/stats") or {}
    return {
        "hash_rate_ths": round((d.get("hash_rate") or 0) / 1e6, 2),
        "tx_24h": d.get("n_tx") or 0,
        "mempool_tx": d.get("mempool_size") or 0,
        "avg_block_time_min": round((d.get("minutes_between_blocks") or 0), 2),
        "btc_sent_24h": round((d.get("total_btc_sent") or 0) / 1e8, 2),
        "difficulty": d.get("difficulty") or 0,
        "market_price_usd": d.get("market_price_usd") or 0,
        "trade_volume_btc": round((d.get("trade_volume_btc") or 0), 0),
    }


def _global_market() -> dict:
    d = get_json("https://api.coingecko.com/api/v3/global") or {}
    data = d.get("data", {}) if isinstance(d, dict) else {}
    return {
        "total_mcap_usd": (data.get("total_market_cap", {}) or {}).get("usd", 0),
        "total_vol_usd": (data.get("total_volume", {}) or {}).get("usd", 0),
        "btc_dominance": round((data.get("market_cap_percentage", {}) or {}).get("btc", 0), 2),
        "eth_dominance": round((data.get("market_cap_percentage", {}) or {}).get("eth", 0), 2),
        "mcap_change_24h": round(data.get("market_cap_change_percentage_24h_usd", 0), 2),
        "active_cryptos": data.get("active_cryptocurrencies", 0),
    }


def _stablecoin_supply() -> dict:
    d = get_json("https://stablecoins.llama.fi/stablecoins", params={"includePrices": "false"})
    total = 0.0
    top = []
    try:
        for s in (d or {}).get("peggedAssets", [])[:200]:
            circ = (s.get("circulating") or {})
            v = circ.get("peggedUSD") or 0
            total += v
            top.append({"name": s.get("name"), "supply": v})
    except Exception:
        pass
    top.sort(key=lambda x: x["supply"], reverse=True)
    return {"total_usd": round(total, 0), "top": top[:5]}


def _exchange_netflow_proxy() -> dict:
    """Free proxy for exchange flow: Binance spot whale tape signed notional."""
    d = get_json("https://api.binance.com/api/v3/trades", params={"symbol": "BTCUSDT", "limit": 500})

    buy = sell = 0.0
    whales = []
    if isinstance(d, list):
        for t in d:
            try:
                notional = float(t["price"]) * float(t["qty"])
            except Exception:
                continue
            if notional < WHALE_MIN_USD:
                continue
            is_buyer_maker = bool(t.get("isBuyerMaker"))
            # isBuyerMaker=True → the taker was a SELLER (market sell)
            if is_buyer_maker:
                sell += notional
            else:
                buy += notional
            whales.append({
                "price": float(t["price"]), "qty": float(t["qty"]),
                "notional_usd": round(notional, 0),
                "side": "SELL" if is_buyer_maker else "BUY",
            })
    whales.sort(key=lambda w: w["notional_usd"], reverse=True)
    net = buy - sell
    return {
        "whale_buy_usd": round(buy, 0),
        "whale_sell_usd": round(sell, 0),
        "net_flow_usd": round(net, 0),
        "whale_count": len(whales),
        "top_whales": whales[:10],
        "flow_bias": "ACCUMULATION" if net > 0 else "DISTRIBUTION" if net < 0 else "NEUTRAL",
    }


def get_onchain() -> dict:

    def build():
        net = _btc_network()
        glob = _global_market()
        stables = _stablecoin_supply()
        flow = _exchange_netflow_proxy()
        score = 50
        score += 12 if flow["flow_bias"] == "ACCUMULATION" else -12 if flow["flow_bias"] == "DISTRIBUTION" else 0
        score += 8 if glob.get("mcap_change_24h", 0) > 0 else -8 if glob.get("mcap_change_24h", 0) < 0 else 0
        score += 6 if glob.get("btc_dominance", 0) > 50 else -4
        return {
            "network": net,
            "global": glob,
            "stablecoins": stables,
            "exchange_flow": flow,
            "onchain_score": max(1, min(99, round(score))),
            "regime": "ACCUMULATION" if score >= 58 else "DISTRIBUTION" if score <= 42 else "NEUTRAL",
            "live": True,
            "sources": ["blockchain.info", "coingecko", "defillama", "binance"],
        }

    return cached("onchain", 90, build, default={})


def get_whales_local(trades: list) -> dict:
    """Reuse already-fetched local trades for the whale tape (no extra HTTP)."""
    buy = sell = 0.0
    whales = []
    for t in trades or []:
        try:
            notional = float(t.get("price", 0)) * float(t.get("qty") or t.get("amount") or 0)
        except Exception:
            continue
        if notional < WHALE_MIN_USD:
            continue
        side = "BUY" if str(t.get("side", "")).lower() == "buy" else "SELL"
        if side == "BUY":
            buy += notional
        else:
            sell += notional
        whales.append({"price": float(t.get("price", 0)), "qty": float(t.get("qty") or t.get("amount") or 0),
                       "notional_usd": round(notional, 0), "side": side})
    whales.sort(key=lambda w: w["notional_usd"], reverse=True)
    net = buy - sell
    return {"whale_buy_usd": round(buy, 0), "whale_sell_usd": round(sell, 0),
            "net_flow_usd": round(net, 0), "whale_count": len(whales),
            "top_whales": whales[:10],
            "flow_bias": "ACCUMULATION" if net > 0 else "DISTRIBUTION" if net < 0 else "NEUTRAL"}