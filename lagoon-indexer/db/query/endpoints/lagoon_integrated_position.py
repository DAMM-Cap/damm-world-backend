from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils
import os

def get_integrated_position_data_query(offset: int = 0, limit: int = 20) -> str:
    return f"""
    WITH user_vaults AS (
        SELECT DISTINCT dr.vault_id
        FROM deposit_requests dr
        WHERE dr.user_id = %s AND dr.vault_id = %s
    ),

    latest_snapshots AS (
        SELECT DISTINCT ON (vs.vault_id)
            vs.vault_id, vs.total_assets, vs.total_shares,
            vs.apy, vs.share_price, ev.event_timestamp
        FROM vault_snapshots vs
        JOIN events ev ON ev.event_id = vs.event_id
        WHERE vs.vault_id = %s
        ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    snapshots_12h_ago AS (
        SELECT DISTINCT ON (vs.vault_id)
            vs.vault_id, vs.total_assets, vs.apy, ev.event_timestamp
        FROM vault_snapshots vs
        JOIN events ev ON ev.event_id = vs.event_id
        WHERE vs.vault_id = %s
          AND ev.event_timestamp <= NOW() - INTERVAL '12 hours'
        ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    user_returns AS (
        SELECT vault_id,
            SUM(CASE WHEN return_type = 'deposit' THEN assets ELSE 0 END) AS total_deposit,
            SUM(CASE WHEN return_type = 'withdraw' THEN assets ELSE 0 END) AS total_withdraw,
            SUM(CASE WHEN return_type = 'deposit' THEN shares ELSE 0 END) -
            SUM(CASE WHEN return_type = 'withdraw' THEN shares ELSE 0 END) AS user_total_shares
        FROM vault_returns
        WHERE user_id = %s AND vault_id = %s
        GROUP BY vault_id
    ),

    settled_redeems AS (
        SELECT vault_id,
            SUM(shares) AS total_settled_redeem
        FROM redeem_requests
        WHERE user_id = %s AND status = 'settled' AND vault_id = %s
        GROUP BY vault_id
    )

    SELECT
        ls.vault_id,
        COALESCE(ls.total_assets, 0) AS latest_tvl,
        COALESCE(s12.total_assets, 0) AS tvl_12h_ago,
        COALESCE(ls.apy, 0) AS latest_apy,
        COALESCE(s12.apy, 0) AS apy_12h_ago,
        COALESCE(ls.share_price, 0) AS share_price,
        COALESCE(ur.total_deposit, 0) AS deposit_value,
        COALESCE(ur.total_withdraw, 0) AS withdrawal_value,
        COALESCE(ur.total_deposit, 0) - COALESCE(ur.total_withdraw, 0) AS position_value,
        COALESCE(ur.user_total_shares, 0) AS user_total_shares,
        COALESCE(ls.total_shares, 0) AS total_shares,
        COALESCE(ur.total_deposit, 0) AS completed_deposits,
        COALESCE(sr.total_settled_redeem, 0) AS settled_redeems,
        COALESCE(ur.total_withdraw, 0) AS completed_redeems
    FROM latest_snapshots ls
    LEFT JOIN snapshots_12h_ago s12 ON s12.vault_id = ls.vault_id
    LEFT JOIN user_returns ur ON ur.vault_id = ls.vault_id
    LEFT JOIN settled_redeems sr ON sr.vault_id = ls.vault_id
    OFFSET {offset}
    LIMIT {limit};
    """


def get_integrated_position(address: str, offset: int, limit: int, chain_id: int, vault_address: str) -> Dict[str, Any]:
    """
    Get user position for a specific vault using vault_id resolved from vault_address.
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    lowercase_address = address.lower()
    lowercase_vault_address = vault_address.lower()

    print(f"DEBUG: Looking for user {lowercase_address} on chain {chain_id} and vault {lowercase_vault_address}")

    # Fetch user_id
    user_df = db.frameResponse(
        "SELECT user_id FROM users WHERE address = %s AND chain_id = %s",
        (lowercase_address, chain_id)
    )
    if user_df.empty:
        print("DEBUG: No user found, returning empty result")
        return {"total": 0, "next_offset": None, "positions": []}

    user_id = user_df.iloc[0]['user_id']
    print(f"DEBUG: User ID: {user_id}")

    # Resolve vault_id
    vault_df = db.frameResponse("""
        SELECT v.vault_id
        FROM vaults v
        JOIN tokens t ON v.vault_token_id = t.token_id
        WHERE v.chain_id = %s AND LOWER(t.address) = %s
    """, (chain_id, lowercase_vault_address))

    if vault_df.empty:
        print("DEBUG: No vault found for given chain and address")
        return {"total": 0, "next_offset": None, "positions": []}

    vault_id = vault_df.iloc[0]['vault_id']
    print(f"DEBUG: Resolved vault ID: {vault_id}")

    count_query_params = (user_id, vault_id)

    # Prepare query parameters
    data_query_params = (
        user_id, vault_id,  # user_vaults
        vault_id,           # latest_snapshots
        vault_id,           # snapshots_12h_ago
        user_id, vault_id,  # user_returns
        user_id, vault_id   # settled_redeems
    )

    result = PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=PaginationUtils.get_integrated_position_count_query(),
        data_query=get_integrated_position_data_query,
        count_query_params=count_query_params,
        data_query_params=data_query_params,
        offset=offset,
        limit=limit,
        result_key="positions"
    )

    print(f"DEBUG: Final result: {result}")
    return result
