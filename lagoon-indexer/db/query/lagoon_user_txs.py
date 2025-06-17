from db.db import getEnvDb
from typing import Dict, Any
from core.lagoon_deployments import get_lagoon_deployments
from utils.converters import convert_numpy_types

def get_count_query(table: str, owner_join_column: bool = False) -> str:
    if owner_join_column:
        return f"""
            SELECT COUNT(*) AS count
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            JOIN users u ON t.user_id = u.user_id
            WHERE u.address = %s
            AND v.chain_id = %s
        """
    else:
        return f"""
            SELECT COUNT(*) AS count
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            WHERE (t.from_address = %s OR t.to_address = %s)
            AND t.from_address != ALL(%s)
            AND t.to_address != ALL(%s)
            AND v.chain_id = %s
        """


def get_tx_query(table: str, owner_join_column: bool = False, offset: int = 0, limit: int = 20) -> str:
    if owner_join_column:
        return f"""
            SELECT 
                t.*,
                v.chain_id,
                v.name as vault_name,
                t2.symbol as vault_token_symbol,
                t3.symbol as deposit_token_symbol,
                t2.address as vault_token_address,
                t3.address as deposit_token_address,
                '{table}' AS source_table
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            JOIN users u ON t.user_id = u.user_id
            JOIN tokens t2 ON v.vault_token_id = t2.token_id
            JOIN tokens t3 ON v.deposit_token_id = t3.token_id
            JOIN events e ON t.event_id = e.event_id
            WHERE u.address = %s
            AND v.chain_id = %s
            ORDER BY e.block_number DESC, e.log_index DESC
            OFFSET {offset}
            LIMIT {limit}
        """
    else:
        return f"""
            SELECT 
                t.*,
                v.chain_id,
                v.name as vault_name,
                t2.symbol as vault_token_symbol,
                t3.symbol as deposit_token_symbol,
                t2.address as vault_token_address,
                t3.address as deposit_token_address,
                '{table}' AS source_table
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            JOIN tokens t2 ON v.vault_token_id = t2.token_id
            JOIN tokens t3 ON v.deposit_token_id = t3.token_id
            JOIN events e ON t.event_id = e.event_id
            WHERE (t.from_address = %s OR t.to_address = %s)
            AND t.from_address != ALL(%s)
            AND t.to_address != ALL(%s)
            AND v.chain_id = %s
            ORDER BY e.block_number DESC, e.log_index DESC
            OFFSET {offset}
            LIMIT {limit}
        """

def get_user_txs(address: str, offset: int, limit: int, chain_id: int = 480) -> Dict[str, Any]:
    db = getEnvDb('damm-public')
    lowercase_address = address.lower()
    contract_addresses = [
        get_lagoon_deployments(chain_id)['lagoon_address'].lower(),
        get_lagoon_deployments(chain_id)['silo'].lower()
    ]

    tables_config_owner_join = {
        "deposit_requests": True,
        "redeem_requests": True,
        "vault_returns": True,
        "transfers": False
    }

    total_count = 0
    all_txs = []

    for table, owner_join_column in tables_config_owner_join.items():
        # Count query
        count_query = get_count_query(table, owner_join_column)
        if owner_join_column:
            count_df = db.frameResponse(count_query, (lowercase_address, chain_id))
        else:
            count_df = db.frameResponse(
                count_query,
                (lowercase_address, lowercase_address, contract_addresses, contract_addresses, chain_id)
            )
        if not count_df.empty:
            total_count += int(count_df.iloc[0]['count'])

        # Transaction query
        tx_query = get_tx_query(table, owner_join_column, offset, limit)
        if owner_join_column:
            tx_df = db.frameResponse(tx_query, (lowercase_address, chain_id))
        else:
            tx_df = db.frameResponse(
                tx_query,
                (lowercase_address, lowercase_address, contract_addresses, contract_addresses, chain_id)
            )
        if not tx_df.empty:
            txs = tx_df.to_dict(orient="records")
            txs_converted = [convert_numpy_types(t) for t in txs]
            all_txs.extend(txs_converted)

    # Sort combined
    all_txs_sorted = sorted(
        all_txs,
        key=lambda x: (x.get('block_number', 0), x.get('log_index', 0)),
        reverse=True
    )

    return {
        "total": total_count,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "txs": all_txs_sorted
    }
