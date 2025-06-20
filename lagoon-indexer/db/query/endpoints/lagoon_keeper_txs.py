from db.db import getEnvDb
from typing import Dict, Any, List

def get_keepers_pending_txs_metadata(chain_id: int = 480) -> Dict[str, Any]:
    """
    Get pending deposit and redeem requests that need to be settled.
    Get settled deposit requests owners for claiming shares on behalf.
    Returns a JSON structure with:
        pendingDeposit: bool
        pendingRedeem: bool
        settledDeposit: list of controllers
    """
    db = getEnvDb('damm-public')
    
    vaults_query = """
        SELECT vault_id, price_oracle_address, safe_address
        FROM vaults
        WHERE chain_id = %s
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

    vaults_txs = []
    
    vaults_df = db.frameResponse(vaults_query, (chain_id,))

    for row in vaults_df.itertuples(index=False):
        vault_id = row.vault_id
        price_oracle_address = row.price_oracle_address
        safe_address = row.safe_address
        
        deposit_df = db.frameResponse(deposit_query, (chain_id, vault_id))
        redeem_df = db.frameResponse(redeem_query, (chain_id, vault_id))
        settled_deposit_df = db.frameResponse(settled_deposit_query, (chain_id, vault_id))

        if deposit_df.empty and redeem_df.empty and settled_deposit_df.empty:
            continue
        vault_txs = {
            "vault_id": vault_id,
            "pendingDeposit": not deposit_df.empty,
            "pendingRedeem": not redeem_df.empty,
            "settledDeposit": [],
            "valuationManager": price_oracle_address,
            "safe": safe_address
        }
        # Add settled deposit owner addresses
        if not settled_deposit_df.empty:
            vault_txs["settledDeposit"] = settled_deposit_df['owner'].tolist()
        
        vaults_txs.append(vault_txs)
        
    # Build response structure
    result = {
        "vaults_txs": vaults_txs
    }
    
    
    return result

