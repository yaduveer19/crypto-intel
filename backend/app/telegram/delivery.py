import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.auth.models import TelegramConnection, TradeSignal

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except:
    HAS_HTTPX = False


def format_signal(signal: TradeSignal) -> str:
    emoji = {"BULL": "🟢", "BEAR": "🔴", "NEUTRAL": "⚪"}
    tier_s = {"HIGH": "🔥", "MOD": "⭐", "LOW": "📊"}
    lines = [
        f"{emoji.get(signal.bias, '')} {tier_s.get(signal.tier, '')} **{signal.symbol} SIGNAL**",
        f"**Strategy:** {signal.strategy_key}",
        f"**Bias:** {signal.bias} | **Confidence:** {signal.tier}",
        f"**Entry:** ${signal.entry_price:,.0f}" if signal.entry_price else "",
        f"**Stop:** ${signal.stop_loss:,.0f}" if signal.stop_loss else "",
        f"**TP1:** ${signal.tp1:,.0f}" if signal.tp1 else "",
        f"**TP2:** ${signal.tp2:,.0f}" if signal.tp2 else "",
        f"",
        f"_{signal.reasoning or ''}_",
        f"",
        f"⚙️ Manage alerts: {signal.strategy_key} strategy",
        f"⚠️ Not financial advice.",
    ]
    return "\n".join(line for line in lines if line)


def deliver_signal(user_id: int, signal: TradeSignal, db: Session = None):
    if not HAS_HTTPX:
        return

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        conn = db.query(TelegramConnection).filter(
            TelegramConnection.user_id == user_id,
            TelegramConnection.is_active == True,
        ).first()

        if not conn or not conn.bot_token or not conn.chat_id:
            return

        message = format_signal(signal)
        resp = httpx.post(
            f"https://api.telegram.org/bot{conn.bot_token}/sendMessage",
            json={
                "chat_id": conn.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )

        if resp.status_code == 200:
            signal.delivered_telegram = True
            db.commit()
            logger.info(f"[telegram] signal {signal.id} delivered to user {user_id}")
        else:
            logger.warning(f"[telegram] delivery failed: {resp.status_code}")
    except Exception as e:
        logger.error(f"[telegram] delivery error: {e}")
    finally:
        if close_db:
            db.close()


def test_connection(bot_token: str, chat_id: str) -> dict:
    if not HAS_HTTPX:
        return {"success": False, "error": "httpx not available"}
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": "✅ Crypto Intel connected! You will receive trade alerts here.", "parse_mode": "Markdown"},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": f"Telegram API error: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
