from db.db import getEnvDb
from typing import Dict, Any
from core.lagoon_deployments import get_lagoon_deployments
from .pagination_utils import PaginationUtils

def get_vault_snapshots_data_query(offset: int = 0, limit: int = 20) -> str:
    """Custom data query for vault snapshots."""
    return f"""
        SELECT 
            t.*,
            v.chain_id,
            v.name as vault_name,
            t2.symbol as vault_token_symbol,
            t3.symbol as deposit_token_symbol,
            t2.address as vault_token_address,
            t3.address as deposit_token_address,
            'vault_snapshots' AS source_table
        FROM vault_snapshots t
        JOIN vaults v ON t.vault_id = v.vault_id
        JOIN tokens t2 ON v.vault_token_id = t2.token_id
        JOIN tokens t3 ON v.deposit_token_id = t3.token_id
        JOIN events e ON t.event_id = e.event_id
        WHERE t.vault_id = %s
        AND v.chain_id = %s
        ORDER BY e.block_number DESC, e.log_index DESC
        OFFSET {offset}
        LIMIT {limit}
    """

def get_vault_snapshots(vault_id: str, offset: int, limit: int, chain_id: int = 480) -> Dict[str, Any]:
    """
    Get vault snapshots for a specific vault.
    """
    db = getEnvDb('damm-public')

    # Use the enhanced PaginationUtils for custom queries
    result = PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=PaginationUtils.get_vault_snapshots_count_query,
        data_query=get_vault_snapshots_data_query,
        count_query_params=(vault_id, chain_id),
        data_query_params=(vault_id, chain_id),
        offset=offset,
        limit=limit,
        result_key="snapshots"
    )
    
    return result