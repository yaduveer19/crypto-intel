import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except:
    HAS_HTTPX = False


def format_signal(symbol: str, verdict: dict) -> str:
    bias_emoji = {"BULL": "🟢", "BEAR": "🔴", "NEUTRAL": "⚪"}
    tier_emoji = {"HIGH": "🔥", "MOD": "⭐", "LOW": "📊"}

    bias = verdict.get("bias", "NEUTRAL")
    tier = verdict.get("tier", "LOW")

    lines = [
        f"{bias_emoji.get(bias, '')} {tier_emoji.get(tier, '')} **{symbol} SIGNAL**",
        f"",
        f"**Bias:** {bias}",
        f"**Confidence:** {tier}",
        f"**Entry:** ${verdict.get('entry_price', 'N/A')}",
        f"**Stop Loss:** ${verdict.get('stop_loss', 'N/A')}",
        f"**TP1:** ${verdict.get('tp1', 'N/A')}  (R:R 1:1.5)",
        f"**TP2:** ${verdict.get('tp2', 'N/A')}  (R:R 1:3)",
        f"",
        f"_{verdict.get('reasoning', '')}_",
        f"",
        f"⚠️ Not financial advice. Trade responsibly.",
    ]
    return "\n".join(lines)


def send_signal(symbol: str, verdict: dict):
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("[telegram] not configured, skipping")
        return

    if not HAS_HTTPX:
        logger.warning("[telegram] httpx not available")
        return

    message = format_signal(symbol, verdict)

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"[telegram] API error: {resp.status_code} {resp.text[:200]}")
        else:
            logger.info(f"[telegram] signal sent for {symbol}")
    except Exception as e:
        logger.error(f"[telegram] send failed: {e}")


def register_webhook(webhook_url: str) -> bool:
    if not settings.telegram_bot_token:
        return False
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
            json={"url": webhook_url},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[telegram] webhook registration failed: {e}")
        return False
