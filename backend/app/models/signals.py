from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Double
from sqlalchemy.sql import func
from app.database import Base


class OHLC(Base):
    __tablename__ = "ohlc"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    exchange = Column(String(10), default="binance")


class FundingRate(Base):
    __tablename__ = "funding_rate"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    rate = Column(Float)
    exchange = Column(String(10), default="binance")


class OpenInterest(Base):
    __tablename__ = "open_interest"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    oi = Column(Float)
    oi_usd = Column(Float)
    exchange = Column(String(10), default="binance")


class Liquidation(Base):
    __tablename__ = "liquidations"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    side = Column(String(10))
    amount = Column(Float)
    price = Column(Float)
    exchange = Column(String(10), default="binance")


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True))
    source = Column(String(50))
    title = Column(Text)
    url = Column(Text)
    sentiment = Column(String(10))
    sentiment_score = Column(Float, default=0)


class LaneOutput(Base):
    __tablename__ = "lane_outputs"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    lane = Column(String(20), primary_key=True)
    bias = Column(String(10))
    tier = Column(String(10))
    signals = Column(JSON)
    raw_data = Column(JSON)


class Verdict(Base):
    __tablename__ = "verdicts"
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    bias = Column(String(10))
    tier = Column(String(10))
    entry_price = Column(Float)
    stop_loss = Column(Float)
    tp1 = Column(Float)
    tp2 = Column(Float)
    reasoning = Column(Text)
    lane_breakdown = Column(JSON)


class LaneAccuracy(Base):
    __tablename__ = "lane_accuracy"
    lane = Column(String(20), primary_key=True)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    win_rate = Column(Float, default=0.5)
    last_updated = Column(DateTime(timezone=True), default=func.now())


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20))
    side = Column(String(10))
    entry_price = Column(Float)
    size = Column(Float)
    stop_loss = Column(Float)
    take_profit1 = Column(Float)
    take_profit2 = Column(Float)
    status = Column(String(20), default="open")
    opened_at = Column(DateTime(timezone=True), default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
