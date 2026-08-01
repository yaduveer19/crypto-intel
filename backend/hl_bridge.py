# Hyperliquid WebSocket Bridge — standalone, no SDK needed.
# Subscribes to Hyperliquid public streams (mids, l2Book, trades)
# and rebroadcasts normalized JSON to any client connected to ws://localhost:8765
#
# Usage:  python hl_bridge.py  (optionally pass port:  python hl_bridge.py 9000)

import asyncio
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [bridge] %(message)s")
logger = logging.getLogger("hl_bridge")

try:
    import websockets
except ImportError:
    logger.error("websockets not installed. Run: pip install websockets")
    sys.exit(1)

HL_WS = os.environ.get("HL_WS_URL", "wss://api.hyperliquid.xyz/ws")
DEFAULT_COINS = ["BTC", "ETH", "SOL"]
BRIDGE_PORT = int(os.environ.get("HL_BRIDGE_PORT", "8765"))

clients = set()
last_state = {"mids": {}, "l2": {}, "trades": {}}


def normalize(channel: str, data) -> dict:
    if channel in ("mids", "allMids"):
        return {"type": "hl_mids", "data": data}
    if channel == "l2Book":
        book = data if isinstance(data, dict) else {}
        levels = book.get("levels", [[], []])
        asks, bids = levels[0], levels[1]
        return {
            "type": "hl_orderbook",
            "data": {
                "coin": book.get("coin", ""),
                "time": book.get("time", 0),
                "asks": [[float(a["px"]), float(a["sz"])] for a in asks],
                "bids": [[float(b["px"]), float(b["sz"])] for b in bids],
            },
        }
    if channel == "trades":
        trades = data if isinstance(data, list) else []
        return {
            "type": "hl_trades",
            "data": [
                {
                    "coin": t.get("coin", ""),
                    "price": float(t["px"]),
                    "size": float(t["sz"]),
                    "side": "BUY" if t.get("side") == "B" else "SELL",
                    "time": t.get("time", 0),
                    "hash": t.get("hash", ""),
                }
                for t in trades
            ],
        }
    return {"type": channel, "data": data}


async def fanout(message: dict):
    global clients
    if not clients:
        return
    payload = json.dumps(message, default=str)
    dead = set()
    for c in clients:
        try:
            await c.send(payload)
        except Exception:
            dead.add(c)
    clients -= dead


async def hl_listener():
    coins = os.environ.get("HL_COINS", ",".join(DEFAULT_COINS)).split(",")
    coins = [c.strip().upper() for c in coins if c.strip()]
    subscriptions = [{"type": "allMids"}]
    for coin in coins:
        subscriptions.append({"type": "l2Book", "coin": coin})
        subscriptions.append({"type": "trades", "coin": coin})

    while True:
        try:
            logger.info(f"Connecting to {HL_WS} — {len(subscriptions)} subs")
            async with websockets.connect(HL_WS, ping_interval=20, ping_timeout=20) as ws:
                for sub in subscriptions:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
                await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx"}}))
                logger.info("Subscribed. Streaming...")
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    channel = msg.get("channel")
                    data = msg.get("data")
                    if channel == "subscriptionResponse":
                        logger.info(f"Sub ok: {data.get('subscription')}")
                        continue
                    if not channel or data is None:
                        continue
                    norm = normalize(channel, data)
                    if channel in ("mids", "allMids"):
                        last_state["mids"].update(data.get("mids") or {})
                        norm["data"] = {"mids": last_state["mids"]}
                    elif channel == "l2Book":
                        last_state["l2"][data.get("coin", "")] = norm
                    elif channel == "trades":
                        last_state["trades"].setdefault(data[0]["coin"], []).extend(norm["data"])
                    await fanout(norm)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"HL connection lost: {e} — retry in 5s")
            await asyncio.sleep(5)


async def bridge_server(port: int):
    async def handler(ws):
        logger.info("Client connected to bridge")
        clients.add(ws)
        try:
            if last_state["mids"]:
                await ws.send(json.dumps({"type": "hl_mids", "data": {"mids": last_state["mids"]}}, default=str))
            for coin, entry in list(last_state["l2"].items())[-5:]:
                await ws.send(json.dumps(entry, default=str))
            async for _ in ws:
                pass
        except Exception:
            pass
        finally:
            clients.discard(ws)

    async with websockets.serve(handler, "localhost", port):
        logger.info(f"Bridge server running on ws://localhost:{port}")
        await asyncio.Future()


async def main():
    await asyncio.gather(hl_listener(), bridge_server(BRIDGE_PORT))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        BRIDGE_PORT = int(sys.argv[1])
    print(f"Hyperliquid bridge -> ws://localhost:{BRIDGE_PORT}")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
