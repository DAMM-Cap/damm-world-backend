import json
import redis.asyncio as aioredis

redis_client = aioredis.from_url("redis://redis:6379")

def get_json_payload_for_public_event(event: str, data: dict):
    return {
        "target": "broadcast",
        "payload": {
            "event": event,
            "data": data
        }
    }

def get_json_payload_for_private_event(wallet: str, event: str, data: dict):
    return {
        "target": "wallet",
        "wallet": wallet,
        "payload": {
            "event": event,
            "data": data
        }
    }

async def publish_public_event(broadcast_event: str, message_event: str, data: dict):
    payload = get_json_payload_for_public_event(message_event, data)
    await redis_client.publish(broadcast_event, json.dumps(payload))
    print(f"[Events] Published {message_event} for {data}")

async def publish_private_event(wallet: str, broadcast_event: str, message_event: str, data: dict):
    payload = get_json_payload_for_private_event(wallet, message_event, data)
    await redis_client.publish(broadcast_event, json.dumps(payload))
    print(f"[Events] Published {message_event} for {data}")
