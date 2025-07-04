from broadcaster.redis_broadcaster import publish_public_event, publish_private_event

# ----- VAULT EVENTS -----

async def publish_vault_tvl_update(vault_id: str, new_tvl: int):
    await publish_public_event("bot_events", "vault_tvl_updated", {"vault_id": vault_id, "new_tvl": new_tvl})

# ----- BOT EVENTS -----

async def publish_bot_syncing_update(bot_percentage_behind: float):
    await publish_public_event("bot_events", "bot_syncing", {"percentage_behind": bot_percentage_behind})

# ----- PRIVATE USER EVENTS -----

async def publish_tx_confirmation(wallet: str, tx_hash: str):
    await publish_private_event(wallet, "bot_events", "tx_confirmed", {"tx_hash": tx_hash})

async def publish_settlement(settlement_type: str, wallet: str, vault_id: str):
    try:
        if settlement_type == "deposit":
            await publish_private_event(wallet, "bot_events", "deposit_settled", {"status": "settled", "vault_id": vault_id})
        elif settlement_type == "redeem":
            await publish_private_event(wallet, "bot_events", "redeem_settled", {"status": "settled", "vault_id": vault_id})
    except Exception as e:
        print(f"[Error] Failed to publish settlement update for wallet {wallet}: {e}")

