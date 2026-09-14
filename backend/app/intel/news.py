"""News & events engine — REAL feeds.

Sources:
- Cointelegraph RSS          → crypto headlines
- ForexFactory calendar JSON → macro events (CPI/FOMC/NFP)
- alternative.me/fng         → Fear & Greed index
"""
import re
import html as _html
from datetime import datetime, timezone
from typing import List
from app.intel.fetcher import cached, get_text, get_json

RSS_FEEDS = [
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
]
HIGH_IMPACT = ("CPI", "FOMC", "NFP", "Non-Farm", "Interest Rate", "GDP", "PCE", "Unemployment", "Fed")


def _strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return _html.unescape(s).strip()


def _rss(url: str, source: str, limit: int = 12) -> List[dict]:
    xml = get_text(url, timeout=12)
    if not xml:
        return []
    items = re.findall(r"<item>(.*?)</item>", xml, re.S)[:limit]
    out = []
    for it in items:
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        desc = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", it, re.S)
        title_t = _strip(title.group(1)) if title else ""
        if not title_t:
            continue
        out.append({
            "source": source,
            "title": title_t[:180],
            "link": (link.group(1).strip() if link else ""),
            "summary": _strip(desc.group(1))[:220] if desc else "",
            "time": pub.group(1).strip() if pub else "",
        })
    return out


def _calendar() -> List[dict]:
    data = get_json("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=12)
    out = []
    if isinstance(data, list):
        for e in data[:120]:
            title = e.get("title") or ""
            impact = (e.get("impact") or "").lower()
            if impact not in ("high", "medium"):
                continue
            out.append({
                "title": title,
                "country": e.get("country") or "",
                "date": e.get("date") or "",
                "impact": impact,
                "forecast": e.get("forecast") or "",
                "previous": e.get("previous") or "",
                "high_impact": any(k.lower() in title.lower() for k in HIGH_IMPACT),
            })
    out.sort(key=lambda x: (not x["high_impact"], x["date"]))
    return out[:14]


def _fng() -> dict:
    d = get_json("https://api.alternative.me/fng/", timeout=10)
    try:
        row = d["data"][0]
        return {"value": int(row["value"]), "label": row["value_classification"],
                "timestamp": row.get("timestamp")}
    except Exception:
        return {"value": 50, "label": "Neutral", "timestamp": None}


def get_news() -> dict:

    def build():
        headlines = []
        for src, url in RSS_FEEDS:
            headlines.extend(_rss(url, src, 10))
        # de-dup by title
        seen, uniq = set(), []
        for h in headlines:
            k = h["title"][:60].lower()
            if k in seen:
                continue
            seen.add(k)
            uniq.append(h)
        cal = _calendar()
        fng = _fng()
        return {
            "headlines": uniq[:18],
            "calendar": cal,
            "fear_greed": fng,
            "live": len(uniq) > 0,
            "headline_count": len(uniq),
            "high_impact_count": sum(1 for e in cal if e["high_impact"]),
            "sources": [s for s, _ in RSS_FEEDS] + ["ForexFactory", "alternative.me"],
            "updated": datetime.now(timezone.utc).isoformat(),
        }

    return cached("news", 180, build, default={"headlines": [], "calendar": [], "fear_greed": {"value": 50, "label": "Neutral"}, "live": False})