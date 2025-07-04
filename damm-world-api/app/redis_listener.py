import asyncio, json
import redis.asyncio as aioredis
from fastapi import FastAPI
from .websockets.manager import broadcast_update, send_private_update

""" 
Supported Redis message formats:

Broadcast update:
{
  "target": "broadcast",
  "payload": {
    "event": "vault_tvl_updated",
    "data": { "vault_id": "abc123", "new_tvl": 12345678 }
  }
}

Private update:
{
  "target": "wallet",
  "wallet": "0xYourWalletAddress",
  "payload": {
    "event": "tx_confirmed",
    "data": { "tx_hash": "0xabc..." }
  }
}

"""

def register_redis_listener(app: FastAPI):
    @app.on_event("startup")
    async def start_redis_listener():
        redis_client = aioredis.from_url("redis://redis:6379")
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("bot_events")

        async def reader():
            try:
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue  # skip pings or other events

                    try:
                        data = json.loads(message["data"])
                        print(f"[Redis Listener] Received event: {data}")

                        target = data.get("target")

                        if target == "broadcast":
                            payload = data.get("payload", {})
                            await broadcast_update(payload)

                        elif target == "wallet":
                            wallet = data.get("wallet")
                            payload = data.get("payload", {})
                            if wallet:
                                await send_private_update(wallet, payload)
                            else:
                                print("[Redis Listener] Missing 'wallet' field for private update.")

                        else:
                            print("[Redis Listener] Unknown or missing target, ignoring message.")

                    except Exception as e:
                        print(f"[Redis Listener] Error processing message: {e}")

            except asyncio.CancelledError:
                print("[Redis Listener] Cancelled, exiting gracefully...")
            except Exception as e:
                print(f"[Redis Listener] Listener error: {e}")

        task = asyncio.create_task(reader())

        # Store resources for clean shutdown
        app.state.redis_pubsub = pubsub
        app.state.redis_task = task

    @app.on_event("shutdown")
    async def stop_redis_listener():
        print("[Redis Listener] Shutting down...")
        if hasattr(app.state, "redis_task"):
            app.state.redis_task.cancel()
        if hasattr(app.state, "redis_pubsub"):
            await app.state.redis_pubsub.close()
