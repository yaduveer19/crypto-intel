import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth.routes import get_current_user
from app.auth.models import User, TelegramConnection
from app.telegram.delivery import test_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str


@router.post("/connect")
def connect_telegram(body: TelegramConfig, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = test_connection(body.bot_token, body.chat_id)
    if not test["success"]:
        raise HTTPException(400, test.get("error", "Telegram connection failed"))

    existing = db.query(TelegramConnection).filter(
        TelegramConnection.user_id == user.id
    ).first()

    if existing:
        existing.bot_token = body.bot_token
        existing.chat_id = body.chat_id
        existing.is_active = True
    else:
        conn = TelegramConnection(user_id=user.id, bot_token=body.bot_token, chat_id=body.chat_id, is_active=True)
        db.add(conn)

    db.commit()
    return {"status": "ok", "message": "Telegram connected! Test message sent."}


@router.get("/status")
def telegram_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = db.query(TelegramConnection).filter(
        TelegramConnection.user_id == user.id,
        TelegramConnection.is_active == True,
    ).first()

    if conn:
        return {"connected": True, "chat_id": conn.chat_id, "bot_token": conn.bot_token[:10] + "..." if conn.bot_token else None}
    return {"connected": False}


@router.post("/disconnect")
def disconnect_telegram(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(TelegramConnection).filter(
        TelegramConnection.user_id == user.id
    ).first()
    if existing:
        existing.is_active = False
        db.commit()
    return {"status": "ok", "message": "Telegram disconnected"}
