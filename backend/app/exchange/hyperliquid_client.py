"""Hyperliquid client — uses hyperliquid-python-sdk for REST data.
Live WS handled by hl_bridge.py (port 8765) for isolated operation."""

import logging
import time
from typing import List, Dict, Optional
from app.exchange.base import ExchangeError

logger = logging.getLogger(__name__)

try:
    from hyperliquid.info import Info
    HAS_HL = True
except ImportError:
    HAS_HL = False


class HyperliquidClient:
    BASE_URL = "https://api.hyperliquid.xyz"

    def __init__(self):
        if not HAS_HL:
            logger.warning("[hl] hyperliquid-python-sdk not installed")
            self.info = None
        else:
            try:
                self.info = Info(self.BASE_URL, skip_ws=True)
            except Exception as e:
                logger.warning(f"[hl] init error: {e}")
                self.info = None

    @staticmethod
    def _to_coin(symbol: str) -> str:
        return symbol.replace("USDT", "")

    def get_klines(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[dict]:
        if not self.info:
            raise ExchangeError("Hyperliquid SDK unavailable")
        try:
            candles = self.info.candles_snapshot(
                self._to_coin(symbol), interval=timeframe, limit=limit
            )
            return [
                {
                    "time": int(c["t"] / 1000),
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c["v"]),
                    "exchange": "hyperliquid",
                }
                for c in candles
            ]
        except Exception as e:
            raise ExchangeError(f"Hyperliquid klines: {e}")

    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[dict]:
        if not self.info:
            return None
        try:
            ob = self.info.l2_book(self._to_coin(symbol))
            return {
                "symbol": symbol,
                "exchange": "hyperliquid",
                "bids": [[float(b["px"]), float(b["szi"])] for b in ob["levels"][1][:limit]],
                "asks": [[float(a["px"]), float(a["szi"])] for a in ob["levels"][0][:limit]],
                "timestamp": int(time.time()),
            }
        except Exception as e:
            logger.warning(f"[hl] orderbook error: {e}")
            return None

    def get_funding_rate(self, symbol: str) -> Optional[dict]:
        if not self.info:
            return None
        try:
            ctx = self.info.meta_and_asset_ctxs()
            asset_ctxs = ctx.get("assetCtxs", [])
            meta = ctx.get("meta", {}).get("universe", [])
            coin = self._to_coin(symbol)
            for i, asset in enumerate(meta):
                if asset.get("name") == coin and i < len(asset_ctxs):
                    return {
                        "symbol": symbol,
                        "exchange": "hyperliquid",
                        "rate": float(asset_ctxs[i].get("funding", 0)),
                        "timestamp": int(time.time()),
                    }
        except Exception as e:
            logger.warning(f"[hl] funding error: {e}")
        return None

    def get_ticker(self, symbol: str) -> Optional[dict]:
        if not self.info:
            return None
        try:
            ctx = self.info.meta_and_asset_ctxs()
            meta = ctx.get("meta", {}).get("universe", [])
            asset_ctxs = ctx.get("assetCtxs", [])
            coin = self._to_coin(symbol)
            for i, asset in enumerate(meta):
                if asset.get("name") == coin and i < len(asset_ctxs):
                    ac = asset_ctxs[i]
                    return {
                        "symbol": symbol,
                        "last": float(ac.get("markPx", 0)),
                        "bid": float(ac.get("midPx", 0)) * 0.999,
                        "ask": float(ac.get("midPx", 0)) * 1.001,
                        "volume": float(ac.get("dayNtlVlm", 0)),
                        "exchange": "hyperliquid",
                    }
        except Exception as e:
            logger.warning(f"[hl] ticker error: {e}")
        return None

    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        if not self.info:
            return []
        try:
            trades = self.info.user_trades(self._to_coin(symbol), limit=limit)
            return [
                {
                    "time": int(t["time"] / 1000),
                    "price": float(t["px"]),
                    "amount": float(t["sz"]),
                    "side": str(t["side"]).upper(),
                    "exchange": "hyperliquid",
                }
                for t in trades
            ]
        except Exception as e:
            logger.warning(f"[hl] trades error: {e}")
            return []
