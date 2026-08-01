"""Unified exchange interface — ccxt REST + raw WebSocket clients.
All methods return normalized dicts. Every exchange is optional —
if one fails, aggregator falls back to others."""

import logging
import time
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

SYMBOL_MAP = {
    "binance": {"BTCUSDT": "BTC/USDT:USDT", "ETHUSDT": "ETH/USDT:USDT", "SOLUSDT": "SOL/USDT:USDT"},
    "bybit": {"BTCUSDT": "BTC/USDT:USDT", "ETHUSDT": "ETH/USDT:USDT", "SOLUSDT": "SOL/USDT:USDT"},
    "okx": {"BTCUSDT": "BTC/USDT:USDT", "ETHUSDT": "ETH/USDT:USDT", "SOLUSDT": "SOL/USDT:USDT"},
    "deribit": {"BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT"},
    "hyperliquid": {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"},
}

EXCHANGE_CLASSES = {
    "binance": "binanceusdm",
    "bybit": "bybit",
    "okx": "okx",
    "deribit": "deribit",
    "hyperliquid": "hyperliquid",
}


class ExchangeError(Exception):
    pass


class UnifiedExchange:
    """ccxt-based REST client for multi-exchange data."""

    def __init__(self, exchange_name: str):
        import ccxt
        class_name = EXCHANGE_CLASSES.get(exchange_name)
        if not class_name:
            raise ExchangeError(f"Unsupported exchange: {exchange_name}")
        self.name = exchange_name
        try:
            self.exchange = getattr(ccxt, class_name)({
                "enableRateLimit": True,
                "timeout": 15000,
            })
        except Exception as e:
            raise ExchangeError(f"ccxt init failed for {exchange_name}: {e}")

    def _to_ccxt_symbol(self, symbol: str) -> str:
        return SYMBOL_MAP.get(self.name, {}).get(symbol, symbol)

    def get_klines(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[dict]:
        """Unified OHLCV: [{time, open, high, low, close, volume}]"""
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            ohlcv = self.exchange.fetch_ohlcv(ccxt_sym, timeframe=timeframe, limit=limit)
            return [
                {
                    "time": int(k[0] / 1000),  # unix seconds
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "exchange": self.name,
                }
                for k in ohlcv
            ]
        except Exception as e:
            logger.warning(f"[{self.name}] klines error {symbol}: {e}")
            raise ExchangeError(str(e))

    def get_ticker(self, symbol: str) -> Optional[dict]:
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            t = self.exchange.fetch_ticker(ccxt_sym)
            bid = float(t.get("bid") or 0)
            ask = float(t.get("ask") or 0)
            last = float(t.get("last") or t.get("close") or (bid + ask) / 2 or 0)
            return {
                "symbol": symbol,
                "last": last,
                "bid": bid,
                "ask": ask,
                "volume": float(t.get("baseVolume") or 0),
                "exchange": self.name,
            }
        except Exception as e:
            logger.warning(f"[{self.name}] ticker error {symbol}: {e}")
            return None

    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[dict]:
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            ob = self.exchange.fetch_order_book(ccxt_sym, limit)
            return {
                "symbol": symbol,
                "exchange": self.name,
                "bids": [[float(b[0]), float(b[1])] for b in ob["bids"][:limit]],
                "asks": [[float(a[0]), float(a[1])] for a in ob["asks"][:limit]],
                "timestamp": int(time.time()),
            }
        except Exception as e:
            logger.warning(f"[{self.name}] orderbook error {symbol}: {e}")
            return None

    def get_funding_rate(self, symbol: str) -> Optional[dict]:
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            f = self.exchange.fetch_funding_rate(ccxt_sym)
            return {
                "symbol": symbol,
                "exchange": self.name,
                "rate": float(f.get("fundingRate", 0)),
                "timestamp": int(time.time()),
            }
        except Exception as e:
            logger.warning(f"[{self.name}] funding error {symbol}: {e}")
            return None

    def get_open_interest(self, symbol: str) -> Optional[dict]:
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            oi = self.exchange.fetch_open_interest(ccxt_sym)
            return {
                "symbol": symbol,
                "exchange": self.name,
                "oi": float(oi.get("openInterestAmount", 0)),
                "oi_value": float(oi.get("openInterestValue", 0)),
                "timestamp": int(time.time()),
            }
        except Exception as e:
            logger.warning(f"[{self.name}] OI error {symbol}: {e}")
            return None

    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        """Unified trades: [{time, price, amount, side}]"""
        try:
            ccxt_sym = self._to_ccxt_symbol(symbol)
            trades = self.exchange.fetch_trades(ccxt_sym, limit=limit)
            return [
                {
                    "time": int(t["timestamp"] / 1000) if t.get("timestamp") else int(time.time()),
                    "price": float(t["price"]),
                    "amount": float(t["amount"]),
                    "side": str(t.get("side", "buy")).upper(),
                    "exchange": self.name,
                }
                for t in trades
            ]
        except Exception as e:
            logger.warning(f"[{self.name}] trades error {symbol}: {e}")
            return []
