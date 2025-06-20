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
    
    # Check if there are pending deposit requests
    deposit_query = """
        SELECT 1
        FROM deposit_requests dr
        JOIN vaults v ON dr.vault_id = v.vault_id
        WHERE dr.status = 'pending'
        AND v.chain_id = %s
        LIMIT 1
    """
    
    # Check if there are pending redeem requests
    redeem_query = """
        SELECT 1
        FROM redeem_requests rr
        JOIN vaults v ON rr.vault_id = v.vault_id
        WHERE rr.status = 'pending'
        AND v.chain_id = %s
        LIMIT 1
    """
    
    # Get settled deposit requests owners (for claiming shares)
    settled_deposit_query = """
        SELECT DISTINCT u.address as owner
        FROM deposit_requests dr
        JOIN users u ON dr.user_id = u.user_id
        JOIN vaults v ON dr.vault_id = v.vault_id
        WHERE dr.status = 'settled'
        AND v.chain_id = %s
        ORDER BY u.address
    """
    
    deposit_df = db.frameResponse(deposit_query, (chain_id,))
    redeem_df = db.frameResponse(redeem_query, (chain_id,))
    settled_deposit_df = db.frameResponse(settled_deposit_query, (chain_id,))
    
    # Build response structure
    result = {
        "pendingDeposit": not deposit_df.empty,
        "pendingRedeem": not redeem_df.empty,
        "settledDeposit": []
    }
    
    # Add settled deposit owner addresses
    if not settled_deposit_df.empty:
        result["settledDeposit"] = settled_deposit_df['owner'].tolist()
    
    return result

