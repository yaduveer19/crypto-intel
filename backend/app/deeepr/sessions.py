"""Trading sessions — Asia / London / New York windows (UTC) + realised volatility
per session measured from REAL 1h klines of the last 7 days."""
from datetime import datetime, timezone
from typing import List

SESSIONS = [
    {"key": "asia", "label": "Asia", "emoji": "🇯🇵", "start_utc": 0, "end_utc": 8,
     "centers": "Tokyo / Hong Kong / Singapore"},
    {"key": "london", "label": "London", "emoji": "🇬🇧", "start_utc": 7, "end_utc": 16,
     "centers": "London / Zurich"},
    {"key": "newyork", "label": "New York", "emoji": "🇺🇸", "start_utc": 12, "end_utc": 21,
     "centers": "New York / Toronto"},
]


def _in_window(hour: int, start: int, end: int) -> bool:
    return start <= hour < end if start < end else (hour >= start or hour < end)


def _session_vol(symbol: str, session: dict) -> float:
    """Average |close-open| % of bars whose open hour falls inside the session (7d)."""
    try:
        from app.exchange.aggregator import aggregator
        klines = aggregator.get_klines(symbol, timeframe="1h", limit=168)
        vals = []
        for k in klines:
            h = datetime.fromtimestamp(k["time"], tz=timezone.utc).hour
            if _in_window(h, session["start_utc"], session["end_utc"]) and k["open"]:
                vals.append(abs(k["close"] - k["open"]) / k["open"] * 100)
        if vals:
            return round(sum(vals) / len(vals), 3)
    except Exception:
        pass
    return 0.0


def get_sessions(symbol: str = "BTCUSDT") -> dict:
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60
    from app.intel.fetcher import cached
    out_sessions: List[dict] = []
    active = []
    for s in SESSIONS:
        is_open = _in_window(int(hour), s["start_utc"], s["end_utc"])
        sess_key = s["key"]
        vol = cached(f"sess_vol_{symbol}_{sess_key}", 600,
                     lambda sk=sess_key: _session_vol(symbol, next(x for x in SESSIONS if x["key"] == sk)),
                     default=0.0)
        if is_open:
            active.append(s["label"])
        # hours until open (next cycle)
        if is_open:
            until = 0.0
            closes_in = round(s["end_utc"] - hour, 1) if s["end_utc"] > hour else round(24 - hour + s["end_utc"], 1)
        else:
            closes_in = None
            until = round(s["start_utc"] - hour, 1) if s["start_utc"] > hour else round(24 - hour + s["start_utc"], 1)
        out_sessions.append({**s, "open": is_open, "avg_vol_pct_7d": vol,
                             "opens_in_h": until if not is_open else 0,
                             "closes_in_h": closes_in})
    # overlap bonuses — the juiciest windows
    overlaps = []
    if _in_window(int(hour), 7, 8):
        overlaps.append({"label": "Asia × London overlap", "note": "liquidity hand-off"})
    if _in_window(int(hour), 12, 16):
        overlaps.append({"label": "London × New York overlap", "note": "highest volatility window"})
    return {
        "time_utc": now.strftime("%H:%M"),
        "date_utc": now.strftime("%Y-%m-%d"),
        "hour_utc": round(hour, 2),
        "active": active,
        "is_weekend": now.weekday() >= 5,
        "sessions": out_sessions,
        "overlaps": overlaps,
        "best_window_utc": "12:00–16:00 London×NY overlap",
        "symbol": symbol,
    }
