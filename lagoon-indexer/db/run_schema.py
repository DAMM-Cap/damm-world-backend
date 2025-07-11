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

if __name__ == "__main__":
    db = getEnvDb(os.getenv('DB_NAME'))
    if execute_sql_file("db/schema.sql"):
        truncate_event_tables()
    db.closeConnection()
