import json
import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)

    async def broadcast(self, message: dict):
        payload = json.dumps(message, default=str)
        dead = set()
        for ws in self.connections:
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"[ws] send error: {e}")
                dead.add(ws)
        self.connections -= dead


ws_manager = ConnectionManager()


async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception as e:
        logger.warning(f"[ws] disconnect: {e}")
        ws_manager.disconnect(ws)
