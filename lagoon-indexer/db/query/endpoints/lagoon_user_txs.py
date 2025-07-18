from db.db import getEnvDb
from typing import Dict, Any
from .pagination_utils import PaginationUtils
import os
from db.query.lagoon_db_utils import LagoonDbUtils


def get_data_query(table: str, owner_join_column: bool = False, offset: int = 0, limit: int = 20) -> str:
    """Generate data query for a table."""
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
                e.transaction_hash as tx_hash,
                e.block_number as block,
                e.event_timestamp as timestamp,
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
                e.transaction_hash as tx_hash,
                e.block_number as block,
                e.event_timestamp as timestamp,
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

def get_user_txs(address: str, offset: int, limit: int, chain_id: int, vault_address: str) -> Dict[str, Any]:
    db = getEnvDb(os.getenv('DB_NAME'))
    lowercase_address = address.lower()
    silo_address = LagoonDbUtils.get_silo_from_factory(db, vault_address, chain_id)
    contract_addresses = [
        vault_address,
        silo_address
    ]

    # Configure tables for pagination
    tables_config = {
        "deposit_requests": {
            "owner_join_column": True,
            "count_query": PaginationUtils.get_count_query,
            "data_query": get_data_query,
            "count_query_params": (lowercase_address, chain_id),
            "data_query_params": (lowercase_address, chain_id)
        },
        "redeem_requests": {
            "owner_join_column": True,
            "count_query": PaginationUtils.get_count_query,
            "data_query": get_data_query,
            "count_query_params": (lowercase_address, chain_id),
            "data_query_params": (lowercase_address, chain_id)
        },
        "vault_returns": {
            "owner_join_column": True,
            "count_query": PaginationUtils.get_count_query,
            "data_query": get_data_query,
            "count_query_params": (lowercase_address, chain_id),
            "data_query_params": (lowercase_address, chain_id)
        },
        "transfers": {
            "owner_join_column": False,
            "count_query": PaginationUtils.get_count_query,
            "data_query": get_data_query,
            "count_query_params": (lowercase_address, lowercase_address, contract_addresses, contract_addresses, chain_id),
            "data_query_params": (lowercase_address, lowercase_address, contract_addresses, contract_addresses, chain_id)
        }
    }

    # Use the generic pagination function
    result = PaginationUtils.get_paginated_results(
        db=db,
        tables_config=tables_config,
        count_query_params={},  # Not used in this case, params are in table config
        data_query_params={},  # Not used in this case, params are in table config
        offset=offset,
        limit=limit
    )

    # Rename 'results' to 'txs' for backward compatibility
    result['txs'] = result.pop('results')
    
    return result
