from db import getEnvDb
import os
from insert_factory_data import insert_factory_data

def initialize_factory_data():
    factories = os.getenv("FACTORIES").split(",")
    print("Initializing factory data...")
    
    for factory_str in factories:
        tx_hash, chain_id = factory_str.split(":")
        insert_factory_data(tx_hash, int(chain_id))

    print("Factory data initialized successfully.")

def execute_sql_file(file_path: str) -> bool:
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
        with db.connection.cursor() as cursor:
            cursor.execute(sql)
        db.connection.commit()
        print(f"Successfully executed SQL file: {file_path}")
        return True
    except Exception as e:
        print(f"Error executing SQL file {file_path}: {e}")
        db.connection.rollback()
        return False

def drop_all_schema_objects():
    print("Dropping all Lagoon tables and custom types...")

    drop_sql = """
    -- Drop tables
    DROP TABLE IF EXISTS 
        user_positions,
        vault_returns,
        transfers,
        settlements,
        redeem_requests,
        deposit_requests,
        vault_snapshots,
        events,
        vaults,
        tokens,
        users,
        chains,
        indexer_state,
        bot_status,
        vault_metadata,
        factory,
    CASCADE;

    -- Drop enum types
    DROP TYPE IF EXISTS deposit_request_status CASCADE;
    DROP TYPE IF EXISTS redeem_request_status CASCADE;
    DROP TYPE IF EXISTS transaction_status CASCADE;
    DROP TYPE IF EXISTS vault_status CASCADE;
    DROP TYPE IF EXISTS event_type CASCADE;
    DROP TYPE IF EXISTS settlement_type CASCADE;
    DROP TYPE IF EXISTS vault_return_type CASCADE;
    DROP TYPE IF EXISTS operation_type CASCADE;
    DROP TYPE IF EXISTS network_type CASCADE;
    DROP TYPE IF EXISTS strategy_type CASCADE;

    -- Drop custom domains
    DROP DOMAIN IF EXISTS bps_type CASCADE;
    """

    with db.connection.cursor() as cur:
        cur.execute(drop_sql)
    db.connection.commit()
    print("Dropped all tables, types, and domains.")

if __name__ == "__main__":
    db = getEnvDb(os.getenv("DB_NAME"))
    drop_all_schema_objects()
    if execute_sql_file("db/schema.sql"):
        print("Schema recreated successfully.")
    initialize_factory_data()
    db.closeConnection()
