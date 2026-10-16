"""Daily market brief — real snapshot → LLM narrative. Cached 30 min;
template fallback when the LLM is unreachable (still uses real data)."""
import json
import time
from datetime import datetime, timezone

from app.intel.fetcher import cached

LLM_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
LLM_KEY = "sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf"
LLM_MODEL = "agnes-3.0-flash"


def _snapshot() -> dict:
    snap = {"symbols": {}, "fng": None, "headlines": [], "events": [], "macro": None,
            "funding": None, "mode": None}
    try:
        from app.exchange.aggregator import aggregator
        snap["mode"] = aggregator.get_mode()
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            k = aggregator.get_klines(sym, timeframe="1h", limit=25)
            f = aggregator.get_funding_rate(sym)
            if k and len(k) > 1:
                snap["symbols"][sym] = {
                    "price": k[-1]["close"],
                    "chg_24h_pct": round((k[-1]["close"] / k[0]["close"] - 1) * 100, 2),
                    "high_24h": max(x["high"] for x in k),
                    "low_24h": min(x["low"] for x in k),
                    "funding_pct": round((f.get("rate") or 0) * 100, 4) if f else None,
                }
            if f and f.get("rate") is not None:
                snap["funding"] = round(float(f["rate"]) * 100, 4)
    except Exception:
        pass
    try:
        from app.intel.news import get_news
        n = get_news()
        snap["fng"] = n.get("fear_greed")
        snap["headlines"] = [h.get("title") for h in (n.get("headlines") or [])[:6]]
        snap["events"] = [{"t": e.get("title"), "d": e.get("date"), "impact": e.get("impact")}
                          for e in (n.get("calendar") or [])[:4]]
    except Exception:
        pass
    try:
        from app.intel.macro import get_macro
        m = get_macro()
        snap["macro"] = {"risk": m.get("macro_risk"),
                         "rows": [{"a": r.get("asset"), "c": r.get("change_pct")}
                                  for r in (m.get("rows") or [])[:5]]}
    except Exception:
        pass
    return snap


def _template_brief(snap: dict, ts: str) -> str:
    lines = [f"## Market Brief — {ts}", ""]
    for sym, d in (snap.get("symbols") or {}).items():
        arrow = "▲" if d["chg_24h_pct"] >= 0 else "▼"
        lines.append(f"- **{sym}** {d['price']:,.2f} {arrow} {d['chg_24h_pct']:+.2f}% (24h) | "
                     f"range {d['low_24h']:,.0f}–{d['high_24h']:,.0f}")
    fng = snap.get("fng") or {}
    if fng.get("value") is not None:
        lines.append(f"- **Fear & Greed:** {fng['value']} ({fng.get('label','')})")
    if snap.get("macro"):
        lines.append(f"- **Macro regime:** {snap['macro'].get('risk')} | " +
                     ", ".join(f"{r['a']} {r['c']:+.2f}%" for r in snap["macro"]["rows"] if r.get("c") is not None))
    if snap.get("headlines"):
        lines += ["", "### Headlines"] + [f"- {h}" for h in snap["headlines"][:5]]
    if snap.get("events"):
        lines += ["", "### On the calendar"] + [f"- {e['t']} ({e['d']}) [{e['impact']}]" for e in snap["events"][:3]]
    lines += ["", "_⚠️ Not financial advice. DYOR._"]
    return "\n".join(lines)


def get_brief() -> dict:
    def build():
        snap = _snapshot()
        ts = datetime.now(timezone.utc).strftime("%A, %d %b %Y %H:%M UTC")
        prompt = ("Write today's crypto market brief in markdown with sections: "
                  "**Market Tone** (2 sentences), **Levels to Watch** (per symbol, using the data), "
                  "**Flows & Macro** (funding/FNG/DXY regime), **Calendar** (2 lines on upcoming events), "
                  "**Bottom line** (1 sentence). Use ONLY this data, be specific with numbers, "
                  "no boilerplate. End with '⚠️ Not financial advice. DYOR.'\n\nData:\n" +
                  json.dumps(snap, default=str)[:3500])
        reply, source = None, "llm"
        try:
            from app.deeepr.llm import chat
            reply = chat([{"role": "system", "content": "You are a sharp crypto market desk writing a daily brief for active traders."},
                          {"role": "user", "content": prompt}],
                         temperature=0.4, max_tokens=900, timeout=45)
        except Exception:
            reply = None
        if not reply:
            reply, source = _template_brief(snap, ts), "template"
        return {"brief": reply, "snapshot": snap, "source": source,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    return cached("daily_brief", 1800, build,
                  default={"brief": "Brief unavailable — market data offline.", "source": "none"})
