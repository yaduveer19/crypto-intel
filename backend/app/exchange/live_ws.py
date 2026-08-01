"""Live WebSocket clients for raw market data (trades, orderbook, bookTicker).
No API keys needed — all public streams."""

import asyncio
import json
import logging
import time
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class LiveWebSocketBase:
    """Base class: connects, subscribes, reconnects, dispatches parsed JSON to handlers."""

    def __init__(self, url: str, handlers: dict):
        """handlers: {"trades": fn, "orderbook": fn, "bookTicker": fn}"""
        self.url = url
        self.handlers = handlers
        self.ws = None
        self._loop = None
        self._thread = None
        self._running = False
        self._buffer = []

    def start(self):
        if not HAS_WEBSOCKETS:
            logger.warning("[ws] websockets library not installed")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            logger.error(f"[ws] loop error: {e}")

    async def _connect_and_listen(self):
        while self._running:
            try:
                self.ws = await websockets.connect(self.url, ping_interval=20, ping_timeout=20)
                await self.on_connect()
                while self._running:
                    raw = await self.ws.recv()
                    await self.on_message(raw)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[ws] {self.url} disconnected: {e} — reconnecting in 5s")
                await asyncio.sleep(5)

    async def on_connect(self):
        pass

    async def on_message(self, raw: str):
        try:
            data = json.loads(raw)
            await self.dispatch(data)
        except Exception as e:
            logger.debug(f"[ws] parse error: {e}")

    async def dispatch(self, data: dict):
        pass

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ── thread-safe emit helpers ──────────────────────────────
    def emit(self, key: str, payload: dict):
        fn = self.handlers.get(key)
        if fn:
            try:
                fn(payload)
            except Exception as e:
                logger.debug(f"[ws] handler {key} error: {e}")


class BinanceFuturesWS(LiveWebSocketBase):
    STREAM = "wss://fstream.binance.com/stream"

    def __init__(self, symbol: str, handlers: dict):
        self.symbol = symbol.lower().replace("usdt", "usdt")
        self.sub_payload = {
            "method": "SUBSCRIBE",
            "params": [
                f"{self.symbol}@aggTrade",
                f"{self.symbol}@depth20@100ms",
                f"{self.symbol}@bookTicker",
            ],
            "id": 1,
        }
        super().__init__(f"{self.STREAM}?streams={self.symbol}@aggTrade/{self.symbol}@depth20@100ms/{self.symbol}@bookTicker", handlers)

    async def on_connect(self):
        await self.ws.send(json.dumps(self.sub_payload))

    async def dispatch(self, data: dict):
        stream = data.get("stream", "")
        d = data.get("data", {})
        if "@aggTrade" in stream:
            self.emit("trades", {
                "exchange": "binance",
                "price": float(d.get("p", 0)),
                "amount": float(d.get("q", 0)),
                "side": "BUY" if d.get("m") is False else "SELL",
                "time": int(d.get("E", time.time() * 1000) / 1000),
            })
        elif "@depth20" in stream:
            self.emit("orderbook", {
                "exchange": "binance",
                "bids": [[float(b[0]), float(b[1])] for b in d.get("bids", [])],
                "asks": [[float(a[0]), float(a[1])] for a in d.get("asks", [])],
                "time": int(time.time()),
            })
        elif "@bookTicker" in stream:
            self.emit("bookTicker", {
                "exchange": "binance",
                "bid": float(d.get("b", 0)),
                "ask": float(d.get("a", 0)),
            })


class BybitWS(LiveWebSocketBase):
    def __init__(self, symbol: str, handlers: dict):
        self.sym = symbol.lower()
        super().__init__("wss://stream.bybit.com/v5/public/linear", handlers)
        self.symbol = symbol

    async def on_connect(self):
        await self.ws.send(json.dumps({
            "op": "subscribe",
            "args": [f"publicTrade.{self.sym}", f"orderbook.20.{self.sym}", f"tickers.{self.sym}"],
        }))

    async def dispatch(self, data: dict):
        topic = data.get("topic", "")
        d = data.get("data", [])
        if "publicTrade" in topic:
            for t in d if isinstance(d, list) else [d]:
                self.emit("trades", {
                    "exchange": "bybit",
                    "price": float(t.get("p", 0)),
                    "amount": float(t.get("v", 0)),
                    "side": str(t.get("S", "Buy")).upper(),
                    "time": int(t.get("T", time.time() * 1000) / 1000),
                })
        elif "orderbook" in topic:
            self.emit("orderbook", {
                "exchange": "bybit",
                "bids": [[float(b[0]), float(b[1])] for b in d.get("b", [])],
                "asks": [[float(a[0]), float(a[1])] for a in d.get("a", [])],
                "time": int(time.time()),
            })
        elif "tickers" in topic:
            t = d if isinstance(d, dict) else {}
            self.emit("bookTicker", {
                "exchange": "bybit",
                "bid": float(t.get("bid1Price", 0) or 0),
                "ask": float(t.get("ask1Price", 0) or 0),
            })


class OKXWS(LiveWebSocketBase):
    def __init__(self, symbol: str, handlers: dict):
        self.sym = f"{symbol.replace('USDT', '')}-USDT"
        super().__init__("wss://ws.okx.com:8443/ws/v5/public", handlers)
        self.symbol = symbol

    async def on_connect(self):
        for channel in ["trades", "books5"]:
            await self.ws.send(json.dumps({
                "op": "subscribe",
                "args": [{"channel": channel, "instId": self.sym}],
            }))

    async def dispatch(self, data: dict):
        arg = data.get("arg", {})
        channel = arg.get("channel", "")
        d = data.get("data", [])
        if channel == "trades":
            for t in d:
                self.emit("trades", {
                    "exchange": "okx",
                    "price": float(t.get("px", 0)),
                    "amount": float(t.get("sz", 0)),
                    "side": str(t.get("side", "buy")).upper(),
                    "time": int(t.get("ts", time.time() * 1000) / 1000),
                })
        elif channel == "books5":
            b = d[0] if d else {}
            self.emit("orderbook", {
                "exchange": "okx",
                "bids": [[float(x[0]), float(x[1])] for x in b.get("bids", [])],
                "asks": [[float(x[0]), float(x[1])] for x in b.get("asks", [])],
                "time": int(time.time()),
            })


class DeribitWS(LiveWebSocketBase):
    def __init__(self, symbol: str, handlers: dict):
        self.sym = f"{symbol.replace('USDT', '')}-PERPETUAL"
        super().__init__("wss://www.deribit.com/ws/api/v2", handlers)
        self.symbol = symbol

    async def on_connect(self):
        for channel in [f"trades.{self.sym}.raw", f"book.{self.sym}.none.20.100ms"]:
            await self.ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "public/subscribe",
                "id": 1,
                "params": {"channels": [channel]},
            }))

    async def dispatch(self, data: dict):
        if data.get("method") != "subscription":
            return
        p = data.get("params", {})
        channel = p.get("channel", "")
        d = p.get("data", {})
        if "trades." in channel:
            for t in d if isinstance(d, list) else [d]:
                self.emit("trades", {
                    "exchange": "deribit",
                    "price": float(t.get("price", 0)),
                    "amount": float(t.get("amount", 0)),
                    "side": str(t.get("direction", "buy")).upper(),
                    "time": int(t.get("timestamp", time.time() * 1000) / 1000),
                })
        elif "book." in channel:
            self.emit("orderbook", {
                "exchange": "deribit",
                "bids": [[float(b[0]), float(b[1])] for b in d.get("bids", [])],
                "asks": [[float(a[0]), float(a[1])] for a in d.get("asks", [])],
                "time": int(time.time()),
            })


def create_live_ws(exchange: str, symbol: str, handlers: dict) -> Optional[LiveWebSocketBase]:
    """Factory — returns None if exchange not supported for live streams."""
    try:
        if exchange == "binance":
            return BinanceFuturesWS(symbol, handlers)
        if exchange == "bybit":
            return BybitWS(symbol, handlers)
        if exchange == "okx":
            return OKXWS(symbol, handlers)
        if exchange == "deribit":
            return DeribitWS(symbol, handlers)
    except Exception as e:
        logger.warning(f"[ws] {exchange} client init failed: {e}")
    return None
