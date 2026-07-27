from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.routes import router as api_router
from app.api.websocket import ws_manager, websocket_endpoint
from app.auth.routes import router as auth_router
from app.strategies.routes import router as strategy_router
from app.telegram.routes import router as telegram_router
from app.auth.models import User, TelegramConnection, UserStrategy, TradeSignal
from app.models.signals import OHLC, FundingRate, OpenInterest, Liquidation, News, LaneOutput, Verdict, LaneAccuracy, Position

app = FastAPI(title="Crypto Intel", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(api_router, prefix="/api")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crypto-intel"}
