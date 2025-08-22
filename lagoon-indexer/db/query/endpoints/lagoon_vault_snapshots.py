from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils
import os

RANGE_TO_INTERVAL = {
    "24h":  "24 hours",
    "7d":   "7 days",
    "1m":   "1 month",
    "6m":   "6 months",
    "1y":   "1 year",
    "all":  None,
}

def get_vault_snapshots_data_query(offset: int = 0, limit: int = 20, interval: str | None = None) -> str:
    """Custom data query for vault snapshots."""
    
    time_filter = f"AND e.event_timestamp >= NOW() - INTERVAL '{interval}'" if interval else ""

    return f"""
        SELECT 
            t.*,
            v.chain_id,
            v.name as vault_name,
            t2.symbol as vault_token_symbol,
            t3.symbol as deposit_token_symbol,
            t2.address as vault_token_address,
            t3.address as deposit_token_address,
            e.event_timestamp as event_timestamp
        FROM vault_snapshots t
        JOIN vaults v ON t.vault_id = v.vault_id
        JOIN tokens t2 ON v.vault_token_id = t2.token_id
        JOIN tokens t3 ON v.deposit_token_id = t3.token_id
        JOIN events e ON t.event_id = e.event_id
        WHERE v.chain_id = %s
            {time_filter}

        ORDER BY e.block_number DESC, e.log_index DESC
        OFFSET {offset}
        LIMIT {limit}
    """

def get_vault_snapshots(offset: int, limit: int, chain_id: int, ranges: str) -> Dict[str, Any]:
    """
    Get vault snapshots for a specific vault.
    """
    db = getEnvDb(os.getenv('DB_NAME'))

    interval = RANGE_TO_INTERVAL.get(ranges, None)

    # Use the enhanced PaginationUtils for custom queries
    result = PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=lambda: PaginationUtils.get_vault_snapshots_count_query(interval),
        data_query=lambda off, lim: get_vault_snapshots_data_query(off, lim, interval),
        count_query_params=(chain_id,),
        data_query_params=(chain_id,),
        offset=offset,
        limit=limit,
        result_key="snapshots"
    )
    
    return result