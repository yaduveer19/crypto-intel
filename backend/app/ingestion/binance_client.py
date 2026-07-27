import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, List
from app.models.signals import OHLC, FundingRate, OpenInterest, Liquidation

logger = logging.getLogger(__name__)


class BinanceClient:
    BASE = "https://api.binance.com"
    FUTURES = "https://fapi.binance.com"

    def _request(self, url: str, params: Optional[dict] = None) -> dict:
        resp = httpx.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[dict]:
        data = self._request(f"{self.BASE}/api/v3/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        })
        return [
            {
                "time": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "symbol": symbol,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "exchange": "binance",
            }
            for k in data
        ]

    def save_klines(self, db, symbol: str, interval: str = "1m", limit: int = 100) -> int:
        klines = self.get_klines(symbol, interval, limit)
        saved = 0
        for k in klines:
            try:
                db.merge(OHLC(**k))
                saved += 1
            except Exception as e:
                logger.warning(f"[binance] merge kline error: {e}")
        db.commit()
        return saved

    def get_funding_rate(self, symbol: str, limit: int = 10) -> List[dict]:
        data = self._request(f"{self.FUTURES}/fapi/v1/fundingRate", {
            "symbol": symbol,
            "limit": limit,
        })
        return [
            {
                "time": datetime.fromtimestamp(d["fundingTime"] / 1000, tz=timezone.utc),
                "symbol": symbol,
                "rate": float(d["fundingRate"]),
                "exchange": "binance",
            }
            for d in data
        ]

    def save_funding_rate(self, db, symbol: str, limit: int = 10) -> int:
        rates = self.get_funding_rate(symbol, limit)
        saved = 0
        for r in rates:
            try:
                db.merge(FundingRate(**r))
                saved += 1
            except Exception as e:
                logger.warning(f"[binance] merge funding error: {e}")
        db.commit()
        return saved

    def get_open_interest(self, symbol: str) -> dict:
        data = self._request(f"{self.FUTURES}/fapi/v1/openInterest", {
            "symbol": symbol,
        })
        return {
            "time": datetime.now(timezone.utc),
            "symbol": symbol,
            "oi": float(data["openInterest"]),
            "exchange": "binance",
        }

    def save_open_interest(self, db, symbol: str) -> int:
        oi = self.get_open_interest(symbol)
        oi_obj = OpenInterest(**oi)
        try:
            db.merge(oi_obj)
            db.commit()
            return 1
        except Exception as e:
            logger.warning(f"[binance] merge OI error: {e}")
            db.rollback()
            return 0

    def get_liquidations(self, symbol: str, limit: int = 50) -> List[dict]:
        try:
            data = self._request(f"{self.FUTURES}/fapi/v1/allLiquidationOrders", {
                "symbol": symbol,
                "limit": min(limit, 100),
            })
            return [
                {
                    "time": datetime.fromtimestamp(d["time"] / 1000, tz=timezone.utc),
                    "symbol": symbol,
                    "side": d["side"],
                    "amount": float(d["executedQty"]),
                    "price": float(d["price"]),
                    "exchange": "binance",
                }
                for d in data
            ]
        except Exception as e:
            logger.warning(f"[binance] liquidation fetch error: {e}")
            return []

    def get_current_price(self, symbol: str) -> float:
        ticker = self._request(f"{self.BASE}/api/v3/ticker/price", {"symbol": symbol})
        return float(ticker["price"])
