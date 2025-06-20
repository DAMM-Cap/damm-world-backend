from db.db import getEnvDb
from typing import Dict, Any, List

def get_pending_requests(chain_id: int = 480) -> List[Dict[str, Any]]:
    """
    Get all pending deposit and redeem requests that need to be settled.
    Returns a list of request objects with id, request_id, owner, and type.
    """
    db = getEnvDb('damm-public')
    
    # Get pending deposit requests
    deposit_query = """
        SELECT 
            dr.request_id as id,
            dr.request_id,
            u.address as owner,
            'deposit' as type,
            dr.assets,
            v.vault_id,
            v.name as vault_name
        FROM deposit_requests dr
        JOIN users u ON dr.user_id = u.user_id
        JOIN vaults v ON dr.vault_id = v.vault_id
        WHERE dr.status = 'pending'
        AND v.chain_id = %s
        ORDER BY dr.request_id
    """
    
    # Get pending redeem requests
    redeem_query = """
        SELECT 
            rr.request_id as id,
            rr.request_id,
            u.address as owner,
            'redeem' as type,
            rr.shares as assets,
            v.vault_id,
            v.name as vault_name
        FROM redeem_requests rr
        JOIN users u ON rr.user_id = u.user_id
        JOIN vaults v ON rr.vault_id = v.vault_id
        WHERE rr.status = 'pending'
        AND v.chain_id = %s
        ORDER BY rr.request_id
    """
    
    deposit_df = db.frameResponse(deposit_query, (chain_id,))
    redeem_df = db.frameResponse(redeem_query, (chain_id,))
    
    # Combine results
    pending_requests = []
    
    if not deposit_df.empty:
        for _, row in deposit_df.iterrows():
            pending_requests.append({
                'id': row['id'],
                'request_id': row['request_id'],
                'owner': row['owner'],
                'type': row['type'],
                'assets': row['assets'],
                'vault_id': row['vault_id'],
                'vault_name': row['vault_name']
            })
    
    if not redeem_df.empty:
        for _, row in redeem_df.iterrows():
            pending_requests.append({
                'id': row['id'],
                'request_id': row['request_id'],
                'owner': row['owner'],
                'type': row['type'],
                'assets': row['assets'],
                'vault_id': row['vault_id'],
                'vault_name': row['vault_name']
            })
    
    return pending_requests

