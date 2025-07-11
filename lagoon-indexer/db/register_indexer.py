from db.db import getEnvDb
from core.lagoon_deployments import get_lagoon_deployments
import os
import sys
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants.abi.lagoon import LAGOON_ABI
from constants.abi.erc20 import ERC20_ABI
from utils.rpc import get_w3
from utils.chain_metadata import get_chain_metadata
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils

def insert_chain(db, chain_id: int):
    metadata = get_chain_metadata(chain_id)
    if metadata is None:
        print(f"No chain found with ID {chain_id}")
        return
    
    name = metadata["name"]
    network_type = metadata["network_type"]
    native_currency_symbol = metadata["native_currency_symbol"]
    explorer_url = metadata["explorer_url"]
    created_at = LagoonDbDateUtils.get_datetime_formatted_now()

    query = """
    INSERT INTO chains (
        chain_id, name, network_type, explorer_url, native_currency_symbol, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (chain_id) DO NOTHING
    RETURNING chain_id;
    """
    with db.connection as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                chain_id,
                name,
                network_type,
                explorer_url,
                native_currency_symbol,
                created_at
            ))
        conn.commit()
    print(f"{name} chain inserted (or already exists).")

def insert_token(db, chain_id, token_address):
    w3 = get_w3(chain_id)
    token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    
    symbol = token_contract.functions.symbol().call()
    name = token_contract.functions.name().call()
    decimals = token_contract.functions.decimals().call()

    token_id = str(uuid.uuid4())
    created_at = LagoonDbDateUtils.get_datetime_formatted_now()
    query = """
    INSERT INTO tokens (
        token_id, chain_id, address, symbol, name, decimals, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (chain_id, address) DO NOTHING
    RETURNING token_id;
    """
    with db.connection as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                token_id,
                chain_id,
                token_address,
                symbol,
                name,
                decimals,
                created_at
            ))
            result = cur.fetchone()

            if result:
                final_token_id = result[0]
            else:
                # Already exists, fetch the existing ID
                cur.execute(
                    "SELECT token_id FROM tokens WHERE chain_id = %s AND address = %s",
                    (chain_id, token_address)
                )
                final_token_id = cur.fetchone()[0]
        conn.commit()
        
    print(f"{name} token inserted (or already exists).")
    return final_token_id

def insert_vault(db, chain_id):
    lagoon_address = get_lagoon_deployments(chain_id)["lagoon_address"]
    
    vault_id = str(uuid.uuid4())
    vault_token_id = insert_token(db, chain_id, lagoon_address)
    
    w3 = get_w3(chain_id)
    vault_contract = w3.eth.contract(address=lagoon_address, abi=LAGOON_ABI)
    
    deposit_token_address = vault_contract.functions.asset().call()
    deposit_token_id = insert_token(db, chain_id, deposit_token_address)

    name = vault_contract.functions.name().call()
    
    strategy_type = 'yield_farming'
    status = 'active'
    total_assets = 0
    management_rate = 0
    performance_rate = 0
    high_water_mark = 0
                
    min_deposit = 0 #TODO
    max_deposit = None #TODO
    
    roles_storage = vault_contract.functions.getRolesStorage().call()
    whitelist_manager_address = roles_storage[0]
    fee_receiver_address = roles_storage[1]
    safe_address = roles_storage[2]
    fee_registry_address = roles_storage[3]
    price_oracle_address = roles_storage[4]

    administrator_address = vault_contract.functions.owner().call()
    created_at = LagoonDbDateUtils.get_datetime_formatted_now()
    query = """
    INSERT INTO vaults (
        vault_id, chain_id, name, vault_token_id, deposit_token_id,
        strategy_type, status, total_assets, management_rate, performance_rate, high_water_mark, 
        min_deposit, max_deposit, administrator_address, safe_address, price_oracle_address,
        whitelist_manager_address, fee_receiver_address, fee_registry_address, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (chain_id, vault_token_id) DO NOTHING
    RETURNING vault_id;
    """

    with db.connection as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                vault_id,
                chain_id,
                name,
                vault_token_id,
                deposit_token_id,
                strategy_type,
                status,
                total_assets,
                management_rate,
                performance_rate,
                high_water_mark,
                min_deposit,
                max_deposit,
                administrator_address,
                safe_address,
                price_oracle_address,
                whitelist_manager_address,
                fee_receiver_address,
                fee_registry_address,
                created_at
            ))
            result = cur.fetchone()

            if result:
                final_vault_id = result[0]
            else:
                # fallback: fetch existing vault_id
                cur.execute(
                    "SELECT vault_id FROM vaults WHERE chain_id = %s AND vault_token_id = %s",
                    (chain_id, vault_token_id)
                )
                final_vault_id = cur.fetchone()[0]

        conn.commit()

    print(f"{name} vault inserted (or already exists).")
    return final_vault_id

def insert_indexer_state(db, vault_id, chain_id):
    now_ts = LagoonDbDateUtils.get_datetime_formatted_now()
    query = """
    INSERT INTO indexer_state (
    vault_id, chain_id, last_processed_block, last_processed_timestamp, 
    indexer_version, is_syncing, sync_started_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (vault_id, chain_id) DO NOTHING;
    """
    with db.connection as conn:
        with conn.cursor() as cur:
            cur.execute(query, (vault_id, chain_id, None, now_ts, "1.0.0", True, now_ts, now_ts))
        conn.commit()
    print(f"Indexer state inserted (or already exists).")

def insert_bot_status(db, vault_id, chain_id):
    now_ts = LagoonDbDateUtils.get_datetime_formatted_now()
    query = """
    INSERT INTO bot_status (
    vault_id, chain_id, last_processed_block, last_processed_timestamp, 
    in_sync, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (vault_id, chain_id) DO NOTHING;
    """
    with db.connection as conn:
        with conn.cursor() as cur:
            cur.execute(query, (vault_id, chain_id, None, now_ts, False, now_ts))
        conn.commit()
    print(f"Bot status inserted (or already exists).")

def register_indexer(chain_id):
    db = getEnvDb(os.getenv('DB_NAME'))
    insert_chain(db, chain_id)
    vault_id = insert_vault(db, chain_id)
    insert_indexer_state(db, vault_id, chain_id)
    insert_bot_status(db, vault_id, chain_id)
    db.closeConnection()
    return vault_id