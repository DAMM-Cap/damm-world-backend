from db import getEnvDb
import os

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

def truncate_event_tables():
    """
    Truncate Lagoon event tables (empty data but keep structure).
    """
    lagoon_tables = [
        "user_positions",
        "vault_returns",
        "transfers",
        "settlements",
        "redeem_requests",
        "deposit_requests",
        "vault_snapshots",
        "events",
        "vaults",
        "tokens",
        "indexer_state",
        "bot_status",
        "users",
        "chains"
    ]
    with db.connection as conn:
        with conn.cursor() as cur:
            for table in lagoon_tables:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"Truncated table: {table}")
        conn.commit()

def drop_enum_types():
    """
    Drop custom enum types before recreating schema to accept updates.
    """
    enum_types = [
        "deposit_request_status",
        "redeem_request_status",
        "transaction_status",
        "vault_status",
        "event_type",
        "settlement_type",
        "vault_return_type",
        "operation_type",
        "network_type",
        "strategy_type"
    ]
    with db.connection.cursor() as cur:
        for enum_type in enum_types:
            print(f"Dropping enum type: {enum_type}")
            cur.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE;")
    db.connection.commit()

if __name__ == "__main__":
    db = getEnvDb(os.getenv('DB_NAME'))
    drop_enum_types()
    if execute_sql_file("db/schema.sql"):
        truncate_event_tables()
    db.closeConnection()
