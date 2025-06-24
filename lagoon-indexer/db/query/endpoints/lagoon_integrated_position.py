from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils

def get_integrated_position_data_query(offset: int = 0, limit: int = 20) -> str:
    """Custom data query for integrated positions with calculated fields."""
    return f"""
    WITH
    -- Resolve user ID
    resolved_user AS (
    SELECT user_id FROM users WHERE address = %s AND chain_id = %s
    ),

    -- All user vaults on this chain
    user_vaults AS (
    SELECT DISTINCT vr.vault_id
    FROM vault_returns vr
    WHERE vr.user_id = (SELECT user_id FROM resolved_user)
    ),

    -- Latest snapshot per vault
    latest_snapshot AS (
    SELECT DISTINCT ON (vs.vault_id)
        vs.vault_id,
        vs.total_assets,
        vs.total_shares,
        vs.apy,
        vs.share_price,
        ev.event_timestamp
    FROM vault_snapshots vs
    JOIN events ev ON ev.event_id = vs.event_id
    WHERE vs.vault_id IN (SELECT vault_id FROM user_vaults)
    ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    -- Best-effort 12h-ago snapshot per vault
    snapshot_12h_ago AS (
    SELECT DISTINCT ON (vs.vault_id)
        vs.vault_id,
        vs.total_assets,
        vs.apy,
        ev.event_timestamp
    FROM vault_snapshots vs
    JOIN events ev ON ev.event_id = vs.event_id
    WHERE vs.vault_id IN (SELECT vault_id FROM user_vaults)
        AND ev.event_timestamp <= COALESCE(
        (
            SELECT MAX(ev2.event_timestamp)
            FROM vault_snapshots vs2
            JOIN events ev2 ON ev2.event_id = vs2.event_id
            WHERE vs2.vault_id = vs.vault_id
            AND ev2.event_timestamp <= NOW() - INTERVAL '12 hours'
        ),
        NOW()
        )
    ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    -- Raw user deposits and withdrawals
    user_deposits AS (
    SELECT vr.vault_id, vr.shares, vr.assets, ev.event_timestamp
    FROM vault_returns vr
    JOIN events ev ON ev.event_id = vr.event_id
    WHERE vr.return_type = 'deposit'
        AND vr.user_id = (SELECT user_id FROM resolved_user)
    ),

    user_withdrawals AS (
    SELECT vr.vault_id, vr.shares, vr.assets, ev.event_timestamp
    FROM vault_returns vr
    JOIN events ev ON ev.event_id = vr.event_id
    WHERE vr.return_type = 'withdraw'
        AND vr.user_id = (SELECT user_id FROM resolved_user)
    ),

    -- Snapshot prices by vault
    snapshot_prices AS (
    SELECT vs.vault_id, ev.event_timestamp AS snapshot_time, vs.share_price
    FROM vault_snapshots vs
    JOIN events ev ON ev.event_id = vs.event_id
    ),

    -- Matched deposit prices
    deposit_with_price AS (
    SELECT
        ud.vault_id,
        ud.shares,
        ud.assets,
        sp.share_price
    FROM user_deposits ud
    JOIN LATERAL (
        SELECT sp.share_price
        FROM snapshot_prices sp
        WHERE sp.vault_id = ud.vault_id AND sp.snapshot_time <= ud.event_timestamp
        ORDER BY sp.snapshot_time DESC
        LIMIT 1
    ) sp ON TRUE
    ),

    -- Matched withdrawal prices
    withdrawal_with_price AS (
    SELECT
        uw.vault_id,
        uw.shares,
        uw.assets,
        sp.share_price
    FROM user_withdrawals uw
    JOIN LATERAL (
        SELECT sp.share_price
        FROM snapshot_prices sp
        WHERE sp.vault_id = uw.vault_id AND sp.snapshot_time <= uw.event_timestamp
        ORDER BY sp.snapshot_time DESC
        LIMIT 1
    ) sp ON TRUE
    )

    SELECT
    -- Vault key
    ls.vault_id,

    -- TVL and APY
    COALESCE(ls.total_assets, 0) AS latest_tvl,
    COALESCE(s12.total_assets, 0) AS tvl_12h_ago,
    COALESCE(ls.apy, 0) AS latest_apy,
    COALESCE(s12.apy, 0) AS apy_12h_ago,
    COALESCE(ls.share_price, 0) AS share_price,

    -- User value computation
    COALESCE(SUM(dwp.shares * dwp.share_price), 0) AS deposit_value,
    COALESCE(SUM(wwp.shares * wwp.share_price), 0) AS withdrawal_value,
    COALESCE(SUM(dwp.shares * dwp.share_price), 0) - COALESCE(SUM(wwp.shares * wwp.share_price), 0) AS position_value,

    -- Share tracking
    COALESCE(SUM(dwp.shares), 0) - COALESCE(SUM(wwp.shares), 0) AS user_total_shares,
    COALESCE(ls.total_shares, 0) AS total_shares,
    COALESCE(SUM(dwp.assets), 0) AS completed_deposits,
    COALESCE(SUM(wwp.assets), 0) AS completed_redeems

    FROM latest_snapshot ls
    LEFT JOIN snapshot_12h_ago s12 ON s12.vault_id = ls.vault_id
    LEFT JOIN deposit_with_price dwp ON dwp.vault_id = ls.vault_id
    LEFT JOIN withdrawal_with_price wwp ON wwp.vault_id = ls.vault_id

    GROUP BY
    ls.vault_id,
    ls.total_assets,
    s12.total_assets,
    ls.apy,
    s12.apy,
    ls.share_price,
    ls.total_shares

    OFFSET {offset}
    LIMIT {limit}
    """

def get_integrated_position(address: str, offset: int, limit: int, chain_id: int = 480) -> Dict[str, Any]:
    """
    Get user positions across all vaults by constructing data on the fly from multiple tables.
    """
    db = getEnvDb('damm-public')
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
        count_query=PaginationUtils.get_integrated_position_count_query,
        data_query=get_integrated_position_data_query,
        query_params=(lowercase_address, chain_id),
        offset=offset,
        limit=limit,
        result_key="positions"
    )
    
    print(f"DEBUG: Final result: {result}")
    return result