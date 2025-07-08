from broadcaster.redis_broadcaster import publish_public_event, publish_private_event
from decimal import Decimal
from typing import Dict, Any
import datetime
import uuid



# ----- VAULT EVENTS -----

async def publish_vault_tvl_update(vault_id: str, new_tvl: int):
    await publish_public_event("bot_events", "vault_tvl_updated", {"vault_id": vault_id, "new_tvl": new_tvl})

# ----- BOT EVENTS -----

async def publish_bot_syncing_update(bot_percentage_behind: float):
    await publish_public_event("bot_events", "bot_syncing", {"percentage_behind": bot_percentage_behind})

# ----- PRIVATE USER EVENTS -----

async def publish_tx_confirmation(wallet: str, tx_hash: str):
    await publish_private_event(wallet, "bot_events", "tx_confirmed", {"tx_hash": tx_hash})

async def publish_settled_status(settlement_type: str, wallet: str, tx_hash: str):
    try:
        if settlement_type == "deposit":
            await publish_private_event(wallet, "bot_events", "deposit", {"status": "settled", "tx_hash": tx_hash})
        elif settlement_type == "redeem":
            await publish_private_event(wallet, "bot_events", "redeem", {"status": "settled", "tx_hash": tx_hash})
    except Exception as e:
        print(f"[Error] Failed to publish settlement update for wallet {wallet}: {e}")

async def publish_completed_status(tx_type: str, wallet: str, tx_hash: str):
    try:
        if tx_type == "deposit":
            await publish_private_event(wallet, "bot_events", "deposit", {"status": "completed", "tx_hash": tx_hash})
        elif tx_type == "redeem":
            await publish_private_event(wallet, "bot_events", "redeem", {"status": "completed", "tx_hash": tx_hash})
    except Exception as e:
        print(f"[Error] Failed to publish completed status for wallet {wallet}: {e}")

async def publish_canceled_status(wallet: str, tx_hash: str):
    try:
        await publish_private_event(wallet, "bot_events", "deposit", {"status": "canceled", "tx_hash": tx_hash})
    except Exception as e:
        print(f"[Error] Failed to publish canceled status for wallet {wallet}: {e}")

async def publish_deposit_request(event_timestamp: str, tx_hash: str, block_number: int, assets: Decimal, controller_address: str):
    try:
        await publish_private_event(
            controller_address, 
            "bot_events", 
            "new_tx", 
            {
                "source_table": "deposit_requests",
                "status": "pending", 
                "timestamp": event_timestamp, 
                "tx_hash": tx_hash, 
                "block": block_number,
                "assets": str(assets)
            }
        )
    except Exception as e:
        print(f"[Error] Failed to publish deposit request for controller {controller_address}: {e}")

async def publish_redeem_request(event_timestamp: str, tx_hash: str, block_number: int, shares: Decimal, controller_address: str):
    try:
        await publish_private_event(
            controller_address, 
            "bot_events", 
            "new_tx", 
            {
                "source_table": "redeem_requests", 
                "status": "pending", 
                "timestamp": event_timestamp, 
                "tx_hash": tx_hash, 
                "block": block_number,
                "shares": str(shares)
            }
        )
    except Exception as e:
        print(f"[Error] Failed to publish redeem request for controller {controller_address}: {e}")

async def publish_withdraw(wallet: str, event_timestamp: str, tx_hash: str, block_number: int, assets: Decimal, shares: Decimal):
    try:
        await publish_private_event(wallet, "bot_events", "new_tx", {
            "source_table": "vault_returns",
            "return_type": "withdraw",
            "assets": str(assets),
            "shares": str(shares),
            "timestamp": event_timestamp,
            "tx_hash": tx_hash,
            "block": block_number,
        })
    except Exception as e:
        print(f"[Error] Failed to publish withdraw for wallet {wallet}: {e}")

async def publish_transfer(event_timestamp: str, tx_hash: str, block_number: int, amount: Decimal, from_address: str, to_address: str):
    try:
        await publish_private_event(
            from_address, 
            "bot_events", 
            "new_tx", 
            {
                "source_table": "transfer",
                "transfer_type": "sent",
                "timestamp": event_timestamp, 
                "tx_hash": tx_hash, 
                "block": block_number,
                "shares": str(amount),
                "to_address": to_address
            }
        )
        await publish_private_event(
            to_address, 
            "bot_events", 
            "new_tx",
            {
                "source_table": "transfer",
                "transfer_type": "received",
                "timestamp": event_timestamp, 
                "tx_hash": tx_hash, 
                "block": block_number,
                "shares": str(amount),
                "from_address": from_address
            }
        )
    except Exception as e:
        print(f"[Error] Failed to publish transfer for from_address {from_address}: {e}")

async def publish_integrated_position(wallet: str, integrated_position: Dict):
    def make_json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: make_json_safe(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [make_json_safe(v) for v in value]
        elif isinstance(value, (Decimal, datetime.datetime, uuid.UUID)):
            return str(value)
        else:
            return value

    try:
        await publish_private_event(wallet, "bot_events", "integrated_position", make_json_safe(integrated_position))
    except Exception as e:
        print(f"[Error] Failed to publish integrated position for wallet {wallet}: {e}")