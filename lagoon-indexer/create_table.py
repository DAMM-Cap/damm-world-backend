import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection config
DB_PARAMS = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT', '5432')
}

def create_lagoon_tables():
    """
    Create Lagoon-specific tables if they do not exist.
    """
    create_lagoon_last_processed_query = """
    CREATE TABLE IF NOT EXISTS lagoon_last_processed (
        chain_id INT4 NOT NULL,
        contract_address VARCHAR(42) NOT NULL,
        last_processed_block BIGINT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (chain_id, contract_address)
    );
    """

    create_settle_deposit_query = """
    CREATE TABLE IF NOT EXISTS lagoon_settledeposit (
        block BIGINT,
        log_index INT4,
        epoch_id BIGINT,
        settled_id BIGINT,
        total_assets NUMERIC(78),
        total_supply NUMERIC(78),
        assets_deposited NUMERIC(78),
        shares_minted NUMERIC(78),
        tx_hash VARCHAR(66),
        contract_address VARCHAR(42),
        chain_id INT4,
        UNIQUE (block, log_index, tx_hash)
    );
    """

    create_settle_redeem_query = """
    CREATE TABLE IF NOT EXISTS lagoon_settleredeem (
        block BIGINT,
        log_index INT4,
        epoch_id BIGINT,
        settled_id BIGINT,
        total_assets NUMERIC(78),
        total_supply NUMERIC(78),
        assets_withdrawed NUMERIC(78),
        shares_burned NUMERIC(78),
        tx_hash VARCHAR(66),
        contract_address VARCHAR(42),
        chain_id INT4,
        UNIQUE (block, log_index, tx_hash)
    );
    """

    create_deposit_request_canceled_query = """
    CREATE TABLE IF NOT EXISTS lagoon_depositrequestcanceled (
        block BIGINT,
        log_index INT4,
        request_id BIGINT,
        controller VARCHAR(42),
        tx_hash VARCHAR(66),
        contract_address VARCHAR(42),
        chain_id INT4,
        UNIQUE (block, log_index, tx_hash)
    );
    """

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(create_lagoon_last_processed_query)
            cur.execute(create_settle_deposit_query)
            cur.execute(create_settle_redeem_query)
            cur.execute(create_deposit_request_canceled_query)
        conn.commit()
    print("Lagoon tables created (or already exist).")

def truncate_event_tables():
    """
    Truncate Lagoon event tables (empty data but keep structure).
    """
    lagoon_tables = [
        "lagoon_settledeposit",
        "lagoon_settleredeem",
        "lagoon_depositrequestcanceled"
    ]
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for table in lagoon_tables:
                cur.execute(f"TRUNCATE TABLE {table};")
                print(f"Truncated table: {table}")
        conn.commit()

def truncate_lagoon_last_processed():
    """
    Truncate the table that tracks last processed block.
    """
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE lagoon_last_processed;")
            print("Truncated table: lagoon_last_processed")
        conn.commit()

if __name__ == "__main__":
    create_lagoon_tables()
    truncate_event_tables()
    truncate_lagoon_last_processed()
