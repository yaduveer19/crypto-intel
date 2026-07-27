import json
import logging
from datetime import datetime, timezone
from celery import shared_task
from app.database import SessionLocal
from app.config import settings
from app.ingestion.binance_client import BinanceClient
from app.ingestion.news_client import NewsClient
from app.ingestion.macro_client import MacroClient
from app.lanes.technical_lane import TechnicalLane
from app.lanes.flow_lane import FlowLane
from app.lanes.narrative_lane import NarrativeLane
from app.lanes.macro_lane import MacroLane
from app.synthesizer.synthesizer import Synthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── INGESTION ────────────────────────────────────────────────────────────────

@shared_task(name="app.tasks.ingest_price_data", bind=True, max_retries=3)
def ingest_price_data(self, symbol: str):
    try:
        client = BinanceClient()
        db = SessionLocal()
        try:
            saved = client.save_klines(db, symbol, "1m", limit=5)
            logger.info(f"[ingest] {symbol}: saved {saved} klines")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[ingest] {symbol}: {e}")
        raise self.retry(exc=e, countdown=10)


@shared_task(name="app.tasks.ingest_funding", bind=True, max_retries=3)
def ingest_funding(self, symbol: str):
    try:
        client = BinanceClient()
        db = SessionLocal()
        try:
            saved = client.save_funding_rate(db, symbol, limit=10)
            logger.info(f"[funding] {symbol}: saved {saved}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[funding] {symbol}: {e}")
        raise self.retry(exc=e, countdown=10)


@shared_task(name="app.tasks.ingest_open_interest", bind=True, max_retries=3)
def ingest_open_interest(self, symbol: str):
    try:
        client = BinanceClient()
        db = SessionLocal()
        try:
            saved = client.save_open_interest(db, symbol)
            logger.info(f"[oi] {symbol}: saved {saved}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[oi] {symbol}: {e}")
        raise self.retry(exc=e, countdown=10)


# ─── LANES ────────────────────────────────────────────────────────────────────

@shared_task(name="app.tasks.run_technical_lane", bind=True, max_retries=2)
def run_technical_lane(self, symbol: str):
    try:
        lane = TechnicalLane(symbol)
        result = lane.analyze()
        db = SessionLocal()
        try:
            lane.save_output(db, result)
            logger.info(f"[technical] {symbol}: {result['bias']}/{result['tier']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[technical] {symbol}: {e}")
        raise self.retry(exc=e, countdown=15)


@shared_task(name="app.tasks.run_flow_lane", bind=True, max_retries=2)
def run_flow_lane(self, symbol: str):
    try:
        lane = FlowLane(symbol)
        result = lane.analyze()
        db = SessionLocal()
        try:
            lane.save_output(db, result)
            logger.info(f"[flow] {symbol}: {result['bias']}/{result['tier']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[flow] {symbol}: {e}")
        raise self.retry(exc=e, countdown=15)


@shared_task(name="app.tasks.run_narrative_lane", bind=True, max_retries=2)
def run_narrative_lane(self):
    try:
        lane = NarrativeLane()
        result = lane.analyze()
        db = SessionLocal()
        try:
            lane.save_output(db, result)
            logger.info(f"[narrative] bias={result['bias']} tier={result['tier']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[narrative]: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(name="app.tasks.run_macro_lane", bind=True, max_retries=2)
def run_macro_lane(self):
    try:
        lane = MacroLane()
        result = lane.analyze()
        db = SessionLocal()
        try:
            lane.save_output(db, result)
            logger.info(f"[macro] bias={result['bias']} tier={result['tier']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[macro]: {e}")
        raise self.retry(exc=e, countdown=30)


# ─── SYNTHESIZER ──────────────────────────────────────────────────────────────

@shared_task(name="app.tasks.run_synthesizer", bind=True, max_retries=2)
def run_synthesizer(self, symbol: str):
    try:
        synth = Synthesizer()
        verdict = synth.generate_verdict(symbol)
        db = SessionLocal()
        try:
            synth.save_verdict(db, verdict)
            logger.info(f"[verdict] {symbol}: {verdict['bias']}/{verdict['tier']} entry={verdict.get('entry_price')}")

            from app.api.websocket import ws_manager
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(ws_manager.broadcast({
                    "type": "verdict",
                    "symbol": symbol,
                    "data": verdict
                }))
                loop.close()
            except:
                pass

            if settings.telegram_bot_token:
                try:
                    from app.bot.telegram_bot import send_signal
                    send_signal(symbol, verdict)
                except Exception as te:
                    logger.warning(f"[telegram] send failed: {te}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[synthesizer] {symbol}: {e}")
        raise self.retry(exc=e, countdown=30)
