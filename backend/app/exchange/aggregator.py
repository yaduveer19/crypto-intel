"""Multi-exchange aggregator — normalizes data from all exchanges, 
tracks live/simulated status, and provides unified queries."""

import logging
import time
import threading
from typing import Dict, List, Optional, Any

from app.exchange.base import UnifiedExchange, ExchangeError, SYMBOL_MAP
from app.exchange.hyperliquid_client import HyperliquidClient
from app.exchange.live_ws import create_live_ws

logger = logging.getLogger(__name__)

ALL_EXCHANGES = ["binance", "bybit", "okx", "deribit", "hyperliquid"]
PRIMARY_EXCHANGE = "binance"


class ExchangeAggregator:
    def __init__(self):
        self._rest_clients: Dict[str, UnifiedExchange] = {}
        self._hl = HyperliquidClient()
        self._live_ws: Dict[str, Any] = {}
        self._latest = {
            "trades": {},       # {"binance:BTCUSDT": {time, price, amount, side, exchange}}
            "orderbook": {},    # {"binance:BTCUSDT": {bids, asks, time}}
            "bookTicker": {},   # {"binance:BTCUSDT": {bid, ask}}
            "cvd": {},          # {"BTCUSDT": float}
        }
        self._lock = threading.Lock()
        self._ws_started = False
        self._mode = "simulated"  # "live" if at least one exchange WS/REST works

    # ── REST access ──────────────────────────────────────────
    def _rest(self, exchange: str) -> Optional[UnifiedExchange]:
        if exchange == "hyperliquid":
            return None  # handled separately
        if exchange not in self._rest_clients:
            try:
                self._rest_clients[exchange] = UnifiedExchange(exchange)
            except Exception as e:
                logger.warning(f"[agg] {exchange} init failed: {e}")
                return None
        return self._rest_clients.get(exchange)

    def get_klines(self, symbol: str, exchange: Optional[str] = None, timeframe: str = "1m", limit: int = 100) -> List[dict]:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                if ex == "hyperliquid":
                    return self._hl.get_klines(symbol, timeframe, limit)
                client = self._rest(ex)
                if client:
                    return client.get_klines(symbol, timeframe, limit)
            except Exception as e:
                logger.warning(f"[agg] klines {ex} failed: {e}")
        return self._simulated_klines(symbol, limit)

    def get_orderbook(self, symbol: str, exchange: Optional[str] = None, limit: int = 20) -> dict:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                if ex == "hyperliquid":
                    ob = self._hl.get_orderbook(symbol, limit)
                else:
                    client = self._rest(ex)
                    ob = client.get_orderbook(symbol, limit) if client else None
                if ob:
                    self._set_mode("live")
                    return ob
            except Exception as e:
                logger.warning(f"[agg] orderbook {ex} failed: {e}")
        return self._simulated_orderbook(symbol)

    def get_funding_rate(self, symbol: str, exchange: Optional[str] = None) -> Optional[dict]:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                if ex == "hyperliquid":
                    f = self._hl.get_funding_rate(symbol)
                else:
                    client = self._rest(ex)
                    f = client.get_funding_rate(symbol) if client else None
                if f:
                    return f
            except Exception as e:
                logger.warning(f"[agg] funding {ex} failed: {e}")
        return {"symbol": symbol, "exchange": "simulated", "rate": 0.0001, "timestamp": int(time.time())}

    def get_open_interest(self, symbol: str, exchange: Optional[str] = None) -> Optional[dict]:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                client = self._rest(ex)
                if client:
                    oi = client.get_open_interest(symbol)
                    if oi:
                        return oi
            except Exception as e:
                logger.warning(f"[agg] OI {ex} failed: {e}")
        return {"symbol": symbol, "exchange": "simulated", "oi": 0, "oi_value": 0, "timestamp": int(time.time())}

    def get_recent_trades(self, symbol: str, exchange: Optional[str] = None, limit: int = 100) -> List[dict]:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                if ex == "hyperliquid":
                    t = self._hl.get_recent_trades(symbol, limit)
                else:
                    client = self._rest(ex)
                    t = client.get_recent_trades(symbol, limit) if client else None
                if t:
                    self._set_mode("live")
                    return t
            except Exception as e:
                logger.warning(f"[agg] trades {ex} failed: {e}")
        return self._simulated_trades(symbol, limit)

    def get_ticker(self, symbol: str, exchange: Optional[str] = None) -> Optional[dict]:
        exchanges = [exchange] if exchange else [PRIMARY_EXCHANGE]
        for ex in exchanges:
            try:
                if ex == "hyperliquid":
                    t = self._hl.get_ticker(symbol)
                else:
                    client = self._rest(ex)
                    t = client.get_ticker(symbol) if client else None
                if t:
                    self._set_mode("live")
                    return t
            except Exception as e:
                logger.warning(f"[agg] ticker {ex} failed: {e}")
        return {"symbol": symbol, "last": 50000, "bid": 49900, "ask": 50100, "volume": 0, "exchange": "simulated"}

    # ── Live WS ingestion ─────────────────────────────────────
    def start_live_streams(self, symbols: List[str]):
        if self._ws_started:
            return
        self._ws_started = True
        for exchange in ["binance", "bybit", "okx", "deribit"]:
            for symbol in symbols[:2]:  # 2 symbols per exchange to limit connections
                key = f"{exchange}:{symbol}"
                try:
                    ws = create_live_ws(exchange, symbol, {
                        "trades": lambda p, k=key: self._on_trade(k, p),
                        "orderbook": lambda p, k=key: self._on_orderbook(k, p),
                        "bookTicker": lambda p, k=key: self._on_bookticker(k, p),
                    })
                    if ws:
                        ws.start()
                        self._live_ws[key] = ws
                        logger.info(f"[agg] live WS started: {key}")
                        self._set_mode("live")
                except Exception as e:
                    logger.warning(f"[agg] live WS start failed {key}: {e}")

    def stop_live_streams(self):
        for ws in self._live_ws.values():
            try:
                ws.stop()
            except:
                pass
        self._live_ws.clear()

    def _on_trade(self, key: str, payload: dict):
        with self._lock:
            self._latest["trades"][key] = payload
            symbol = key.split(":")[1]
            side_mult = 1.0 if payload["side"] == "BUY" else -1.0
            delta = payload["price"] * payload["amount"] * side_mult
            self._latest["cvd"][symbol] = self._latest["cvd"].get(symbol, 0) + delta

    def _on_orderbook(self, key: str, payload: dict):
        with self._lock:
            self._latest["orderbook"][key] = payload

    def _on_bookticker(self, key: str, payload: dict):
        with self._lock:
            self._latest["bookTicker"][key] = payload

    def get_latest(self, kind: str, exchange: str, symbol: str) -> Optional[dict]:
        with self._lock:
            return self._latest.get(kind, {}).get(f"{exchange}:{symbol}")

    def get_cvd(self, symbol: str) -> float:
        with self._lock:
            return self._latest["cvd"].get(symbol, 0.0)

    # ── Mode & status ─────────────────────────────────────────
    def _set_mode(self, mode: str):
        if mode == "live" and self._mode != "live":
            self._mode = "live"

    def get_mode(self) -> str:
        return self._mode

    def get_status(self) -> dict:
        return {
            "mode": self._mode,
            "exchanges": {
                "binance": {"live_ws": "binance" in [k.split(":")[0] for k in self._live_ws]},
                "bybit": {"live_ws": "bybit" in [k.split(":")[0] for k in self._live_ws]},
                "okx": {"live_ws": "okx" in [k.split(":")[0] for k in self._live_ws]},
                "deribit": {"live_ws": "deribit" in [k.split(":")[0] for k in self._live_ws]},
                "hyperliquid": {"live_ws": True, "note": "via hl_bridge on :8765"},
            },
        }

    # ── Simulated fallbacks (dashboard never blank) ───────────
    def _simulated_klines(self, symbol: str, limit: int) -> List[dict]:
        base = {"BTCUSDT": 67000, "ETHUSDT": 3400, "SOLUSDT": 140}.get(symbol, 100)
        out = []
        t = int(time.time()) - limit * 60
        price = base * 0.98
        for i in range(limit):
            import random
            drift = (random.random() - 0.48) * 0.002
            price *= (1 + drift)
            out.append({
                "time": t + i * 60,
                "open": round(price, 2),
                "high": round(price * 1.001, 2),
                "low": round(price * 0.999, 2),
                "close": round(price, 2),
                "volume": round(random.uniform(5, 50), 2),
                "exchange": "simulated",
            })
        return out

    def _simulated_orderbook(self, symbol: str) -> dict:
        import random
        base = {"BTCUSDT": 67000, "ETHUSDT": 3400, "SOLUSDT": 140}.get(symbol, 100)
        mid = base * (1 + random.uniform(-0.001, 0.001))
        bids = [[round(mid * (1 - i * 0.0001), 2), round(random.uniform(0.1, 5), 3)] for i in range(1, 16)]
        asks = [[round(mid * (1 + i * 0.0001), 2), round(random.uniform(0.1, 5), 3)] for i in range(1, 16)]
        return {"symbol": symbol, "exchange": "simulated", "bids": bids, "asks": asks, "timestamp": int(time.time())}

    def _simulated_trades(self, symbol: str, limit: int) -> List[dict]:
        import random
        base = {"BTCUSDT": 67000, "ETHUSDT": 3400, "SOLUSDT": 140}.get(symbol, 100)
        out = []
        t = int(time.time())
        for i in range(limit):
            side = "BUY" if random.random() > 0.5 else "SELL"
            out.append({
                "time": t - i,
                "price": round(base * (1 + random.uniform(-0.0005, 0.0005)), 2),
                "amount": round(random.uniform(0.01, 2), 4),
                "side": side,
                "exchange": "simulated",
            })
        return out


# Singleton
aggregator = ExchangeAggregator()
