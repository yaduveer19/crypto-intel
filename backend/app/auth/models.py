from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    plan = Column(String(20), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())


class TelegramConnection(Base):
    __tablename__ = "telegram_connections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    bot_token = Column(String(255))
    chat_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class UserStrategy(Base):
    __tablename__ = "user_strategies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_key = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    is_enabled = Column(Boolean, default=True)
    params = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class TradeSignal(Base):
    __tablename__ = "trade_signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_key = Column(String(50))
    symbol = Column(String(20))
    bias = Column(String(10))
    tier = Column(String(10))
    entry_price = Column(Integer)
    stop_loss = Column(Integer)
    tp1 = Column(Integer)
    tp2 = Column(Integer)
    reasoning = Column(Text)
    delivered_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
