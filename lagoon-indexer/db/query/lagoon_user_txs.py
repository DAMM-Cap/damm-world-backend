from db.db import getEnvDb
from typing import Dict, Any
from core.lagoon_deployments import get_lagoon_deployments
from utils.converters import convert_numpy_types

def get_count_query(table: str, owner_column: str = None) -> str:
    if owner_column:
        return f"""
            SELECT COUNT(*) AS count
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            WHERE t.{owner_column} = %s
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


def get_tx_query(table: str, owner_column: str = None, offset: int = 0, limit: int = 20) -> str:
    if owner_column:
        return f"""
            SELECT 
                t.*,
                v.chain_id,
                v.name as vault_name,
                v.vault_token_address as vault_address,
                v.vault_token_symbol as vault_symbol,
                v.deposit_token_symbol as deposit_symbol,
                '{table}' AS source_table
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            WHERE t.{owner_column} = %s
            AND v.chain_id = %s
            ORDER BY t.block DESC, t.log_index DESC
            OFFSET {offset}
            LIMIT {limit}
        """
    else:
        return f"""
            SELECT 
                t.*,
                v.chain_id,
                v.name as vault_name,
                v.vault_token_address as vault_address,
                v.vault_token_symbol as vault_symbol,
                v.deposit_token_symbol as deposit_symbol,
                '{table}' AS source_table
            FROM {table} t
            JOIN vaults v ON t.vault_id = v.vault_id
            WHERE (t.from_address = %s OR t.to_address = %s)
            AND t.from_address != ALL(%s)
            AND t.to_address != ALL(%s)
            AND v.chain_id = %s
            ORDER BY t.block DESC, t.log_index DESC
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

    tables_config = {
        "lagoon_depositrequest": "owner",
        "lagoon_redeemrequest": "owner",
        "lagoon_withdraw": "owner",
        "lagoon_transfer": None
    }

    total_count = 0
    all_txs = []

    for table, owner_column in tables_config.items():
        # Count query
        count_query = get_count_query(table, owner_column)
        if owner_column:
            count_df = db.frameResponse(count_query, (lowercase_address, chain_id))
        else:
            count_df = db.frameResponse(
                count_query,
                (lowercase_address, lowercase_address, contract_addresses, contract_addresses, chain_id)
            )
        if not count_df.empty:
            total_count += int(count_df.iloc[0]['count'])

        # Transaction query
        tx_query = get_tx_query(table, owner_column, offset, limit)
        if owner_column:
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
        key=lambda x: (x.get('block', 0), x.get('log_index', 0)),
        reverse=True
    )

    return {
        "total": total_count,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "txs": all_txs_sorted
    }
