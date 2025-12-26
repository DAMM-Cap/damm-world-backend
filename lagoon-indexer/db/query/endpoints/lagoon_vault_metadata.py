from db.db import getEnvDb
from typing import Dict, Any, Optional
import os
import json

def get_vault_metadata(vault_id: str) -> Optional[Dict[str, Any]]:
    """
    Get vault metadata for a specific vault_id.
    Returns the metadata JSONB field or None if vault not found.
    Metadata structure is kept nested: { "structure": { "mother": "...", "children": [...] } }
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    
    # First, get vault info even if metadata doesn't exist
    vault_query = """
        SELECT 
            v.vault_id,
            v.chain_id,
            t.address as vault_address
        FROM vaults v
        JOIN tokens t ON v.vault_token_id = t.token_id
        WHERE v.vault_id = %s
    """
    
    vault_result = db.queryResponse(vault_query, (vault_id,))
    
    if not vault_result or len(vault_result) == 0:
        return None
    
    vault_row = vault_result[0]
    vault_address = vault_row["vault_address"]
    chain_id = vault_row["chain_id"]
    
    # Now try to get metadata if it exists
    metadata_query = """
        SELECT 
            vm.metadata,
            vm.created_at,
            vm.updated_at
        FROM vault_metadata vm
        WHERE vm.vault_id = %s
    """
    
    metadata_result = db.queryResponse(metadata_query, (vault_id,))
    
    metadata = None
    created_at = None
    updated_at = None
    
    if metadata_result and len(metadata_result) > 0:
        metadata_row = metadata_result[0]
        metadata = metadata_row["metadata"]
        created_at = metadata_row["created_at"]
        updated_at = metadata_row["updated_at"]
    
    # Handle case where metadata might be a string (PostgreSQL JSONB sometimes returns as string)
    if metadata and isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = None
    
    return {
        "vault_id": str(vault_row["vault_id"]),
        "vault_address": vault_address,
        "chain_id": chain_id,
        "metadata": metadata,  # Keep nested structure intact
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }

