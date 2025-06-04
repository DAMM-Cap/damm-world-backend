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

    create_vaults_query = """
    CREATE TABLE IF NOT EXISTS vaults (
        vault_id SERIAL PRIMARY KEY,
        chain_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        vault_token_symbol TEXT NOT NULL,             -- This is the LP token, e.g., "vWLD"
        vault_token_address VARCHAR(42) NOT NULL,     -- Lagoon contract address
        deposit_token_symbol TEXT NOT NULL,           -- e.g., "WLD", "ETH", "USDC"
        deposit_token_address VARCHAR(42) NOT NULL,   -- Token users deposit into the vault
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (vault_token_address, chain_id)
    );
    """

    create_vault_snapshots_query = """
    CREATE TABLE IF NOT EXISTS vault_snapshots (
        vault_id INTEGER NOT NULL,
        nav NUMERIC,
        total_assets NUMERIC,
        total_shares NUMERIC,
        main_token_balance NUMERIC,
        secondary_token_balance NUMERIC,
        recorded_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (vault_id, recorded_at),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_lagoon_last_processed_query = """
    CREATE TABLE IF NOT EXISTS lagoon_last_processed (
        vault_id INTEGER NOT NULL,
        last_processed_block BIGINT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_deposit_request_status_enum = """
    DO $$ BEGIN
        CREATE TYPE deposit_request_status AS ENUM ('pending', 'settled', 'canceled');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """

    create_deposit_request_query = """
    CREATE TABLE IF NOT EXISTS lagoon_depositrequest (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        tx_hash VARCHAR(66) NOT NULL,
        request_id BIGINT,
        controller VARCHAR(42),
        owner VARCHAR(42),
        sender VARCHAR(42),
        assets NUMERIC(78, 0),
        status deposit_request_status NOT NULL DEFAULT 'pending',
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_redeem_request_status_enum = """
    DO $$ BEGIN
        CREATE TYPE redeem_request_status AS ENUM ('pending', 'settled');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """

    create_redeem_request_query = """
    CREATE TABLE IF NOT EXISTS lagoon_redeemrequest (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        tx_hash VARCHAR(66) NOT NULL,
        request_id BIGINT,
        controller VARCHAR(42),
        owner VARCHAR(42),
        sender VARCHAR(42),
        shares NUMERIC(78, 0),
        status redeem_request_status NOT NULL DEFAULT 'pending',
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_settle_deposit_query = """
    CREATE TABLE IF NOT EXISTS lagoon_settledeposit (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        epoch_id BIGINT,
        settled_id BIGINT,
        total_assets NUMERIC(78, 0),
        total_supply NUMERIC(78, 0),
        assets_deposited NUMERIC(78, 0),
        shares_minted NUMERIC(78, 0),
        tx_hash VARCHAR(66) NOT NULL,
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_settle_redeem_query = """
    CREATE TABLE IF NOT EXISTS lagoon_settleredeem (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        epoch_id BIGINT,
        settled_id BIGINT,
        total_assets NUMERIC(78, 0),
        total_supply NUMERIC(78, 0),
        assets_withdrawed NUMERIC(78, 0),
        shares_burned NUMERIC(78, 0),
        tx_hash VARCHAR(66) NOT NULL,
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_withdraw_query = """
    CREATE TABLE IF NOT EXISTS lagoon_withdraw (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        tx_hash VARCHAR(66) NOT NULL,
        sender VARCHAR(42),
        receiver VARCHAR(42),
        owner VARCHAR(42),
        assets NUMERIC(78, 0),
        shares NUMERIC(78, 0),
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_deposit_request_canceled_query = """
    CREATE TABLE IF NOT EXISTS lagoon_depositrequestcanceled (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        request_id BIGINT,
        controller VARCHAR(42),
        tx_hash VARCHAR(66) NOT NULL,
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_transfer_query = """
    CREATE TABLE IF NOT EXISTS lagoon_transfer (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        from_address VARCHAR(42),
        to_address VARCHAR(42),
        value NUMERIC(78, 0),
        tx_hash VARCHAR(66) NOT NULL,
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    create_new_total_assets_updated_query = """
    CREATE TABLE IF NOT EXISTS lagoon_newtotalassetsupdated (
        vault_id INTEGER NOT NULL,
        block BIGINT NOT NULL,
        log_index BIGINT NOT NULL,
        total_assets NUMERIC(78, 0),
        tx_hash VARCHAR(66) NOT NULL,
        PRIMARY KEY (block, log_index, vault_id),
        FOREIGN KEY (vault_id) REFERENCES vaults(vault_id)
    );
    """

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(create_vaults_query)
            cur.execute(create_vault_snapshots_query)
            cur.execute(create_lagoon_last_processed_query)
            cur.execute(create_deposit_request_status_enum)
            cur.execute(create_deposit_request_query)
            cur.execute(create_redeem_request_status_enum)
            cur.execute(create_redeem_request_query)
            cur.execute(create_settle_deposit_query)
            cur.execute(create_settle_redeem_query)
            cur.execute(create_deposit_request_canceled_query)
            cur.execute(create_withdraw_query)
            cur.execute(create_transfer_query)
            cur.execute(create_new_total_assets_updated_query)
        conn.commit()
    print("Lagoon tables created (or already exist).")

def truncate_event_tables():
    """
    Truncate Lagoon event tables (empty data but keep structure).
    """
    lagoon_tables = [
        # Skip vaults table
        "vault_snapshots",
        "lagoon_last_processed",
        "lagoon_depositrequest",
        "lagoon_redeemrequest",
        "lagoon_settledeposit",
        "lagoon_settleredeem",
        "lagoon_depositrequestcanceled",
        "lagoon_transfer",
        "lagoon_newtotalassetsupdated",
        "lagoon_withdraw"
    ]
    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for table in lagoon_tables:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"Truncated table: {table}")
        conn.commit()

if __name__ == "__main__":
    create_lagoon_tables()
    truncate_event_tables()
