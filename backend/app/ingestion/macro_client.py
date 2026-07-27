import httpx
import logging
from datetime import datetime, timezone
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class MacroClient:
    def get_dxy(self) -> Optional[float]:
        try:
            resp = httpx.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception as e:
            logger.warning(f"[macro] DXY error: {e}")

        try:
            import yfinance as yf
            dx = yf.Ticker("DX-Y.NYB")
            return dx.fast_info.last_price
        except:
            pass
        return None

    def get_gold(self) -> Optional[float]:
        try:
            resp = httpx.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception as e:
            logger.warning(f"[macro] Gold error: {e}")

        try:
            import yfinance as yf
            gold = yf.Ticker("GC=F")
            return gold.fast_info.last_price
        except:
            pass
        return None

    def get_fear_greed(self) -> Optional[dict]:
        try:
            resp = httpx.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                item = data["data"][0]
                return {
                    "value": int(item["value"]),
                    "classification": item["value_classification"],
                    "timestamp": datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc),
                }
        except Exception as e:
            logger.warning(f"[macro] Fear/Greed error: {e}")
        return None

    def get_fed_rate(self) -> Optional[float]:
        if not settings.fred_api_key:
            return None
        try:
            resp = httpx.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": "FEDFUNDS",
                    "api_key": settings.fred_api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data["observations"][0]["value"])
        except Exception as e:
            logger.warning(f"[macro] FRED error: {e}")
        return None
