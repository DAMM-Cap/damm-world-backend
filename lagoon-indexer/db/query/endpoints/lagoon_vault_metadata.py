from db.db import getEnvDb
from typing import Dict, Any, Optional
import os

def get_vault_metadata(vault_id: str) -> Optional[Dict[str, Any]]:
    """
    Get vault metadata for a specific vault_id.
    Returns the metadata JSONB field or None if not found.
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    
    query = """
        SELECT 
            vm.vault_id,
            vm.metadata,
            vm.created_at,
            vm.updated_at,
            v.chain_id,
            t.address as vault_address
        FROM vault_metadata vm
        JOIN vaults v ON vm.vault_id = v.vault_id
        JOIN tokens t ON v.vault_token_id = t.token_id
        WHERE vm.vault_id = %s
    """
    
    result = db.queryResponse(query, (vault_id,))
    
    if not result or len(result) == 0:
        return None
    
    row = result[0]
    return {
        "vault_id": str(row["vault_id"]),
        "vault_address": row["vault_address"],
        "chain_id": row["chain_id"],
        "metadata": row["metadata"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }

