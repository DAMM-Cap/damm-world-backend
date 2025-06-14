from db import getEnvDb

def execute_sql_file() -> bool:
    try:
        with open("db/schema.sql", 'r') as f:
            sql = f.read()
        with db.connection.cursor() as cursor:
            cursor.execute(sql)
        db.connection.commit()
        print(f"Successfully executed SQL file")
        return True
    except Exception as e:
        print(f"Error executing SQL file: {e}")
        db.connection.rollback()
        return False

def truncate_event_tables():
    """
    Truncate Lagoon event tables (empty data but keep structure).
    """
    lagoon_tables = [
        # Skip vaults table
        "users",
        "chains",
        "tokens",
        "vaults",
        "events",
        "vault_snapshots",
        "deposit_requests",
        "redeem_requests", 
        "settlements", 
        "transfers", 
        "vault_returns", 
        "user_positions", 
        "indexer_state"
    ]
    with db.connection as conn:
        with conn.cursor() as cur:
            for table in lagoon_tables:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"Truncated table: {table}")
        conn.commit()

if __name__ == "__main__":
    db = getEnvDb('damm-public')
    execute_sql_file()
    truncate_event_tables()
    db.closeConnection()
