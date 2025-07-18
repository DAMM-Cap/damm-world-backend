from db.db import getEnvDb
from typing import Dict, Any
import os

def get_keepers_pending_txs_metadata(chain_id: int = 480) -> Dict[str, Any]:
    """
    Get pending deposit and redeem requests that need to be settled.
    Get settled deposit requests owners for claiming shares on behalf.
    Returns a JSON structure with:
        initialUpdate: bool
        pendingDeposit: bool
        pendingRedeem: bool
        settledDeposit: list of controllers
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    
    vaults_query = """
        SELECT v.vault_id, v.price_oracle_address, v.safe_address, dt.address as underlying_token_address, vt.address as vault_address
        FROM vaults v
        JOIN tokens dt ON dt.token_id = v.deposit_token_id
        JOIN tokens vt ON vt.token_id = v.vault_token_id
        WHERE v.chain_id = %s
    """
    
    # Check if the mandatory initial updateNewTotalAssets was done
    initial_update_query = """
        SELECT 1
        FROM events e
        JOIN vaults v ON v.vault_id = e.vault_id
        WHERE e.event_type = 'total_assets_updated'
        AND v.chain_id = %s
        AND e.vault_id = %s
        LIMIT 1
    """

    # Check if there are pending deposit requests
    deposit_query = """
        SELECT 1
        FROM deposit_requests dr
        JOIN vaults v ON v.vault_id = dr.vault_id
        WHERE dr.status = 'pending'
        AND v.chain_id = %s
        AND dr.vault_id = %s
        LIMIT 1
    """
    
    # Check if there are pending redeem requests
    redeem_query = """
        SELECT 1
        FROM redeem_requests rr
        JOIN vaults v ON v.vault_id = rr.vault_id
        WHERE rr.status = 'pending'
        AND v.chain_id = %s
        AND rr.vault_id = %s
        LIMIT 1
    """
    
    # Get settled deposit requests owners (for claiming shares)
    settled_deposit_query = """
        SELECT DISTINCT u.address as owner
        FROM deposit_requests dr
        JOIN vaults v ON v.vault_id = dr.vault_id
        JOIN users u ON dr.user_id = u.user_id
        WHERE dr.status = 'settled'
        AND v.chain_id = %s
        AND dr.vault_id = %s
        ORDER BY u.address
    """

    indexer_state_query = """
        SELECT is_syncing
        FROM indexer_state
        WHERE vault_id = %s
        LIMIT 1
    """

    bot_status_query = """
        SELECT in_sync
        FROM bot_status
        WHERE vault_id = %s
        LIMIT 1
    """

    vaults_txs = []

    vaults_df = db.frameResponse(vaults_query, (chain_id,))

    for row in vaults_df.itertuples(index=False):
        vault_id = row.vault_id

        vault = {
            "vault_id": vault_id,
            "vault_address": row.vault_address,
            "safe": row.safe_address,
            "valuationManager": row.price_oracle_address,
            "underlying_token_address": row.underlying_token_address,
        }

        indexer_state_df = db.frameResponse(indexer_state_query, (vault_id,))
        if indexer_state_df.empty:
            vaults_txs.append({
                "status": "error",
                "message": "Indexer state not found",
                "vault": vault,
                "vault_txs": {}
            })
            continue

        bot_status_df = db.frameResponse(bot_status_query, (vault_id,))
        if bot_status_df.empty:
            vaults_txs.append({
                "status": "error",
                "message": "Bot status not found",
                "vault": vault,
                "vault_txs": {}
            })
            continue
        
        indexer_is_syncing = indexer_state_df.iloc[0].is_syncing
        if indexer_is_syncing:
            vaults_txs.append({
                "status": "syncing",
                "message": "Indexer is currently syncing blockchain data. Bot operations are paused until synchronization completes.",
                "vault": vault,
                "vault_txs": {}
            })
            continue
        
        bot_in_sync = bot_status_df.iloc[0].in_sync
        if not bot_in_sync:
            vaults_txs.append({
                "status": "syncing",
                "message": "Bot is not in sync with the indexer. Bot operations are paused until synchronization completes.",
                "vault": vault,
                "vault_txs": {}
            })
            continue
        
        initial_update_df = db.frameResponse(initial_update_query, (chain_id, vault_id))
        deposit_df = db.frameResponse(deposit_query, (chain_id, vault_id))
        redeem_df = db.frameResponse(redeem_query, (chain_id, vault_id))
        settled_deposit_df = db.frameResponse(settled_deposit_query, (chain_id, vault_id))

        if deposit_df.empty and redeem_df.empty and settled_deposit_df.empty:
            continue
        vault_txs = {
            "initialUpdate": initial_update_df.empty,
            "pendingDeposit": not deposit_df.empty,
            "pendingRedeem": not redeem_df.empty,
            "settledDeposit": [],
        }
        # Add settled deposit owner addresses
        if not settled_deposit_df.empty:
            vault_txs["settledDeposit"] = settled_deposit_df['owner'].tolist()
        
        vaults_txs.append({
            "status": "ok",
            "message": "Vault is in sync",
            "vault": vault,
            "vault_txs": vault_txs
        })
        
    # Build response structure
    result = {
        "vaults_txs": vaults_txs
    }

    return result

