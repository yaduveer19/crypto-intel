"""Real Telegram alerts — bot token + chat id stored locally, messages sent via
the official Bot API. Also used to auto-deliver strategy signals."""
import json
import os
from typing import Optional

from app.intel.fetcher import UA

try:
    import httpx
except ImportError:
    httpx = None

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "telegram_state.json")


def _load() -> dict:
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict):
                return st
    except Exception:
        pass
    return {"connected": False, "bot_token": None, "chat_id": None, "username": None}


def _save(st: dict) -> None:
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
    except Exception:
        pass


def status() -> dict:
    st = _load()
    return {"connected": bool(st.get("connected")), "username": st.get("username"),
            "chat_id": st.get("chat_id"), "has_token": bool(st.get("bot_token"))}


def _api(token: str, method: str, payload: dict) -> Optional[dict]:
    if httpx is None:
        return None
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/{method}",
                       json=payload, timeout=15, headers=UA)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def connect(bot_token: str, chat_id: str) -> dict:
    """Validate the token, resolve bot identity, send a test message."""
    if not bot_token or not chat_id:
        return {"connected": False, "error": "bot_token and chat_id are required"}
    me = _api(bot_token, "getMe", {})
    if not me or not me.get("ok"):
        return {"connected": False, "error": "Invalid bot token — check it with @BotFather"}
    username = (me.get("result") or {}).get("username")
    sent = _api(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": "✅ *Crypto Intel connected* — strategy alerts will arrive here.",
        "parse_mode": "Markdown",
    })
    if not sent or not sent.get("ok"):
        return {"connected": False, "error": "Token OK but message failed — is chat_id correct? (start your bot with /start)"}
    st = {"connected": True, "bot_token": bot_token, "chat_id": str(chat_id), "username": username}
    _save(st)
    return {"connected": True, "username": username, "chat_id": str(chat_id),
            "message": "Connected — test message delivered."}


def disconnect() -> dict:
    _save({"connected": False, "bot_token": None, "chat_id": None, "username": None})
    return {"connected": False, "message": "Telegram disconnected"}


def send(text: str) -> dict:
    """Send a message if connected. Silently no-ops when not configured."""
    st = _load()
    if not st.get("connected") or not st.get("bot_token"):
        return {"sent": False, "reason": "not_connected"}
    res = _api(st["bot_token"], "sendMessage",
               {"chat_id": st["chat_id"], "text": text, "parse_mode": "Markdown",
                "disable_web_page_preview": True})
    ok = bool(res and res.get("ok"))
    return {"sent": ok, "reason": None if ok else "telegram_error"}


def send_signal(sig: dict) -> dict:
    """Format a strategy signal and deliver it (deeepr-style alert)."""
    arrow = "📈 LONG" if str(sig.get("bias", "")).upper() == "BULL" else "📉 SHORT"
    lines = [
        f"{arrow} *{sig.get('symbol', '')}* — {sig.get('name') or sig.get('strategy', '')}",
        f"Tier: *{sig.get('tier', 'n/a')}*",
        f"Entry: `{sig.get('entry')}`",
        f"Stop: `{sig.get('sl')}`",
        f"Target: `{sig.get('tp1')}` / `{sig.get('tp2')}`",
    ]
    if sig.get("reasoning"):
        lines.append(f"_{str(sig['reasoning'])[:140]}_")
    lines.append("⚠️ Not financial advice. DYOR.")
    return send("\n".join(lines))
