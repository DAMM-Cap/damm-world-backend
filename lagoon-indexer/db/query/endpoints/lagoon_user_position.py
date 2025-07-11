from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils
import os

def get_user_position_data_query(offset: int = 0, limit: int = 20) -> str:
    """Custom data query for user positions with calculated fields."""
    return f"""
        SELECT DISTINCT
            v.vault_id,
            v.name as vault_name,
            v.chain_id,
            t2.symbol as vault_token_symbol,
            t3.symbol as deposit_token_symbol,
            t2.address as vault_token_address,
            t3.address as deposit_token_address,
            u.address as user_address,
            u.user_id,
            -- Latest vault snapshot
            vs.total_assets,
            vs.total_shares,
            vs.share_price,
            vs.apy,
            vs.management_fee,
            vs.performance_fee,
            -- User's deposit requests
            COALESCE(SUM(CASE WHEN dr.status = 'pending' THEN dr.assets ELSE 0 END), 0) as pending_deposits,
            COALESCE(SUM(CASE WHEN dr.status = 'settled' THEN dr.assets ELSE 0 END), 0) as settled_deposits,
            COALESCE(SUM(CASE WHEN dr.status = 'completed' THEN dr.assets ELSE 0 END), 0) as completed_deposits,
            -- User's redeem requests
            COALESCE(SUM(CASE WHEN rr.status = 'pending' THEN rr.shares ELSE 0 END), 0) as pending_redeems,
            COALESCE(SUM(CASE WHEN rr.status = 'settled' THEN rr.shares ELSE 0 END), 0) as settled_redeems,
            COALESCE(SUM(CASE WHEN rr.status = 'completed' THEN rr.shares ELSE 0 END), 0) as completed_redeems,
            -- Calculate user's total shares (from completed deposits minus completed redeems)
            COALESCE(SUM(CASE WHEN dr.status = 'completed' THEN dr.assets / NULLIF(vs.share_price, 0) ELSE 0 END), 0) - 
            COALESCE(SUM(CASE WHEN rr.status = 'completed' THEN rr.shares ELSE 0 END), 0) as user_total_shares,
            -- Calculate user's position value
            (COALESCE(SUM(CASE WHEN dr.status = 'completed' THEN dr.assets / NULLIF(vs.share_price, 0) ELSE 0 END), 0) - 
             COALESCE(SUM(CASE WHEN rr.status = 'completed' THEN rr.shares ELSE 0 END), 0)) * COALESCE(vs.share_price, 0) as position_value,
            'user_positions' AS source_table
        FROM vaults v
        JOIN tokens t2 ON v.vault_token_id = t2.token_id
        JOIN tokens t3 ON v.deposit_token_id = t3.token_id
        JOIN users u ON u.address = %s AND u.chain_id = %s
        LEFT JOIN deposit_requests dr ON dr.vault_id = v.vault_id AND dr.user_id = u.user_id
        LEFT JOIN redeem_requests rr ON rr.vault_id = v.vault_id AND rr.user_id = u.user_id
        LEFT JOIN (
            SELECT DISTINCT ON (vs.vault_id) 
                vs.vault_id, vs.total_assets, vs.total_shares, vs.share_price, vs.apy, vs.management_fee, vs.performance_fee
            FROM vault_snapshots vs
            JOIN events e ON vs.event_id = e.event_id
            ORDER BY vs.vault_id, e.event_timestamp DESC
        ) vs ON vs.vault_id = v.vault_id
        WHERE v.chain_id = %s
        GROUP BY v.vault_id, v.name, v.chain_id, t2.symbol, t3.symbol, t2.address, t3.address, 
                 u.address, u.user_id, vs.total_assets, vs.total_shares, vs.share_price, vs.apy, 
                 vs.management_fee, vs.performance_fee
        ORDER BY position_value DESC
        OFFSET {offset}
        LIMIT {limit}
    """

def get_user_position(address: str, offset: int, limit: int, chain_id: int = 480) -> Dict[str, Any]:
    """
    Get user positions across all vaults by constructing data on the fly from multiple tables.
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    lowercase_address = address.lower()

    print(f"DEBUG: Looking for user {lowercase_address} on chain {chain_id}")

    # First, check if user exists
    user_check_query = "SELECT user_id FROM users WHERE address = %s AND chain_id = %s"
    user_df = db.frameResponse(user_check_query, (lowercase_address, chain_id))
    
    print(f"DEBUG: User check result: {len(user_df)} rows found")
    if not user_df.empty:
        print(f"DEBUG: User ID found: {user_df.iloc[0]['user_id']}")
    
    if user_df.empty:
        print(f"DEBUG: No user found, returning empty result")
        return {
            "total": 0,
            "next_offset": None,
            "positions": []
        }

    # Use the enhanced PaginationUtils for custom queries
    result = PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=PaginationUtils.get_user_position_count_query,
        data_query=get_user_position_data_query,
        count_query_params=(lowercase_address, chain_id, chain_id),
        data_query_params=(lowercase_address, chain_id, chain_id),
        offset=offset,
        limit=limit,
        result_key="positions"
    )
    
    print(f"DEBUG: Final result: {result}")
    return result