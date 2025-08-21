from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils
import os

def get_integrated_position_data_query(offset: int = 0, limit: int = 20) -> str:
    """
    Return a single-page dataset of *all* vaults for a chain, enriched with:
      - latest snapshot
      - snapshot ~12h ago
      - user returns and settled redeems (left-joined; zero if none)
    Pagination is applied at the end (OFFSET/LIMIT).
    Parameters (in order) expected by this SQL:
      1) chain_id (for static_vault_data)
      2) user_id  (for user_returns; can be NULL)
      3) user_id  (for settled_redeems; can be NULL)
    """
    return f"""
    WITH static_vault_data AS (
        SELECT
            v.vault_id,
            share_token.address  AS vault_address,
            share_token.symbol   AS vault_symbol,
            share_token.decimals AS vault_decimals,
            under_token.address  AS token_address,
            under_token.symbol   AS token_symbol,
            under_token.decimals AS token_decimals,
            v.status             AS vault_status,
            v.name               AS vault_name
        FROM vaults v
        JOIN tokens under_token ON v.deposit_token_id = under_token.token_id
        JOIN tokens share_token ON v.vault_token_id   = share_token.token_id
        WHERE v.chain_id = %s
    ),

    latest_snapshots AS (
        SELECT DISTINCT ON (vs.vault_id)
            vs.vault_id, vs.total_assets, vs.total_shares,
            vs.apy, vs.share_price, ev.event_timestamp,
            vs.performance_fee, vs.management_fee
        FROM vault_snapshots vs
        JOIN events ev ON ev.event_id = vs.event_id
        JOIN static_vault_data sv ON sv.vault_id = vs.vault_id
        ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    snapshots_12h_ago AS (
        SELECT DISTINCT ON (vs.vault_id)
            vs.vault_id, vs.total_assets, vs.apy, ev.event_timestamp
        FROM vault_snapshots vs
        JOIN events ev ON ev.event_id = vs.event_id
        JOIN static_vault_data sv ON sv.vault_id = vs.vault_id
        WHERE ev.event_timestamp <= NOW() - INTERVAL '12 hours'
        ORDER BY vs.vault_id, ev.event_timestamp DESC
    ),

    user_returns AS (
        SELECT
            vr.vault_id,
            SUM(CASE WHEN vr.return_type = 'deposit'  THEN vr.assets ELSE 0 END) AS total_deposit,
            SUM(CASE WHEN vr.return_type = 'withdraw' THEN vr.assets ELSE 0 END) AS total_withdraw,
            SUM(CASE WHEN vr.return_type = 'deposit'  THEN vr.shares ELSE 0 END) -
            SUM(CASE WHEN vr.return_type = 'withdraw' THEN vr.shares ELSE 0 END) AS user_total_shares
        FROM vault_returns vr
        JOIN static_vault_data sv ON sv.vault_id = vr.vault_id
        WHERE vr.user_id = %s
        GROUP BY vr.vault_id
    ),

    settled_redeems AS (
        SELECT
            rr.vault_id,
            SUM(rr.shares) AS total_settled_redeem
        FROM redeem_requests rr
        JOIN static_vault_data sv ON sv.vault_id = rr.vault_id
        WHERE rr.user_id = %s AND rr.status = 'settled'
        GROUP BY rr.vault_id
    )

    SELECT
        sv.vault_id,
        sv.vault_address,
        sv.vault_symbol,
        sv.vault_decimals,
        sv.token_address,
        sv.token_symbol,
        sv.token_decimals,
        sv.vault_status,
        sv.vault_name,
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
        COALESCE(ur.total_withdraw, 0) AS completed_redeems,
        COALESCE(ls.performance_fee, 0) AS performance_fee,
        COALESCE(ls.management_fee, 0) AS management_fee
    FROM static_vault_data sv
    LEFT JOIN latest_snapshots  ls  ON ls.vault_id  = sv.vault_id
    LEFT JOIN snapshots_12h_ago s12 ON s12.vault_id = sv.vault_id
    LEFT JOIN user_returns      ur  ON ur.vault_id  = sv.vault_id
    LEFT JOIN settled_redeems   sr  ON sr.vault_id  = sv.vault_id
    ORDER BY sv.vault_name, sv.vault_id
    OFFSET {offset}
    LIMIT {limit};
    """


def get_integrated_position(address: str, offset: int, limit: int, chain_id: int) -> Dict[str, Any]:
    """
    Endpoint: returns paginated integrated positions for ALL vaults in `chain_id`
    for the given `address`. No per-vault loop. Rows appear with zeros when the
    user has no activity (thanks to LEFT JOINs + COALESCE).
    """
    db = getEnvDb(os.getenv('DB_NAME'))
    lowercase_address = address.lower()

    # Try to resolve a user_id; if none, pass NULL so CTEs return 0 rows (LEFT JOIN keeps vault rows).
    user_df = db.frameResponse(
        "SELECT user_id FROM users WHERE address = %s AND chain_id = %s",
        (lowercase_address, chain_id)
    )
    user_id = user_df.iloc[0]['user_id'] if not user_df.empty else None

    result = PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=PaginationUtils.get_integrated_position_count_query(),     # expects (chain_id,)
        data_query=get_integrated_position_data_query,        # expects (chain_id, user_id, user_id)
        count_query_params=(chain_id,),
        data_query_params=(chain_id, user_id, user_id),
        offset=offset,
        limit=limit,
        result_key="positions"
    )
    return result
