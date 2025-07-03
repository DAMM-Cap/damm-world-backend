from db.db import getEnvDb
from typing import Dict, Any, List

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
    db = getEnvDb('damm-public')
    
    vaults_query = """
        SELECT v.vault_id, v.price_oracle_address, v.safe_address, t.address as underlying_token_address
        FROM vaults v
        JOIN tokens t ON t.token_id = v.deposit_token_id
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
        AND chain_id = %s
        LIMIT 1
    """

    bot_status_query = """
        SELECT in_sync
        FROM bot_status
        WHERE vault_id = %s
        AND chain_id = %s
        LIMIT 1
    """

    vaults_txs = []

    vaults_df = db.frameResponse(vaults_query, (chain_id,))

    for row in vaults_df.itertuples(index=False):
        vault_id = row.vault_id

        indexer_state_df = db.frameResponse(indexer_state_query, (vault_id, chain_id))
        if indexer_state_df.empty:
            return {
                "status": "error",
                "message": "Indexer state not found"
            }
        bot_status_df = db.frameResponse(bot_status_query, (vault_id, chain_id))
        if bot_status_df.empty:
            return {
                "status": "error",
                "message": "Bot status not found"
            }
        indexer_is_syncing = indexer_state_df.iloc[0].is_syncing
        if indexer_is_syncing:
            return {
                "status": "syncing",
                "message": "Indexer is currently syncing blockchain data. Bot operations are paused until synchronization completes.",
                "vault_txs": []
            }
        bot_in_sync = bot_status_df.iloc[0].in_sync
        if not bot_in_sync:
            return {
                "status": "syncing",
                "message": "Bot is not in sync with the indexer. Bot operations are paused until synchronization completes.",
                "vault_txs": []
            }
        
        price_oracle_address = row.price_oracle_address
        safe_address = row.safe_address
        underlying_token_address = row.underlying_token_address
        
        initial_update_df = db.frameResponse(initial_update_query, (chain_id, vault_id))
        deposit_df = db.frameResponse(deposit_query, (chain_id, vault_id))
        redeem_df = db.frameResponse(redeem_query, (chain_id, vault_id))
        settled_deposit_df = db.frameResponse(settled_deposit_query, (chain_id, vault_id))

        if deposit_df.empty and redeem_df.empty and settled_deposit_df.empty:
            continue
        vault_txs = {
            "vault_id": vault_id,
            "initialUpdate": initial_update_df.empty,
            "pendingDeposit": not deposit_df.empty,
            "pendingRedeem": not redeem_df.empty,
            "settledDeposit": [],
            "valuationManager": price_oracle_address,
            "safe": safe_address,
            "underlying_token_address": underlying_token_address
        }
        # Add settled deposit owner addresses
        if not settled_deposit_df.empty:
            vault_txs["settledDeposit"] = settled_deposit_df['owner'].tolist()
        
        vaults_txs.append(vault_txs)
        
    # Build response structure
    result = {
        "status": "ok",
        "vaults_txs": vaults_txs
    }
    
    
    return result

