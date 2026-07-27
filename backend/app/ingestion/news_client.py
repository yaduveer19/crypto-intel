import httpx
import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.config import settings
from app.models.signals import News

logger = logging.getLogger(__name__)


class NewsClient:
    CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"

    def get_headlines(self, limit: int = 20) -> List[dict]:
        headlines = []

        # CryptoPanic
        if settings.cryptopanic_api_key:
            try:
                resp = httpx.get(self.CRYPTOPANIC_URL, params={
                    "auth_token": settings.cryptopanic_api_key,
                    "public": "true",
                    "limit": limit,
                }, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for post in data.get("results", []):
                        headlines.append({
                            "time": datetime.fromisoformat(post["published_at"].replace("Z", "+00:00")),
                            "source": post.get("source", {}).get("title", "CryptoPanic"),
                            "title": post["title"],
                            "url": post.get("url", ""),
                            "sentiment": "neutral",
                            "sentiment_score": 0.0,
                        })
                else:
                    logger.warning(f"[news] CryptoPanic HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"[news] CryptoPanic error: {e}")

        # RSS-style fallback: CoinDesk via direct parse
        try:
            resp = httpx.get("https://www.coindesk.com/arc/outboundfeeds/rss/", timeout=15)
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                ns = {"": "http://www.w3.org/2005/Atom"}
                for entry in list(root.findall(".//entry", ns))[:10]:
                    title_el = entry.find("title", ns)
                    link_el = entry.find("link", ns)
                    if title_el is not None:
                        headlines.append({
                            "time": datetime.now(timezone.utc),
                            "source": "CoinDesk",
                            "title": title_el.text,
                            "url": link_el.get("href") if link_el is not None else "",
                            "sentiment": "neutral",
                            "sentiment_score": 0.0,
                        })
        except Exception as e:
            logger.warning(f"[news] CoinDesk RSS error: {e}")

        return headlines

    def save_headlines(self, db, headlines: List[dict]) -> int:
        saved = 0
        for h in headlines:
            try:
                existing = db.query(News).filter(
                    News.title == h["title"],
                    News.source == h["source"],
                ).first()
                if not existing:
                    news = News(**h)
                    db.add(news)
                    saved += 1
            except Exception as e:
                logger.warning(f"[news] save error: {e}")
        if saved > 0:
            db.commit()
        return saved
