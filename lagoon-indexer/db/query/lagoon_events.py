from db.db import Database
from datetime import datetime
from pandas import DataFrame
from decimal import Decimal
from .lagoon_ev_helpers import LagoonEventsHelpers

class LagoonEvents:
    @staticmethod
    def insert_lagoon_events(db: Database, event_df: DataFrame, table_name: str):
        filtered_cols = [c for c in event_df.columns]
        cleaned_df = event_df[filtered_cols]
        db.insertDf(cleaned_df, table_name)

    @staticmethod
    def update_settled_deposit_requests(db: Database, vault_id: str, settled_timestamp: str):
        query = """
        UPDATE deposit_requests
        SET status = 'settled', updated_at = %s, settled_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND updated_at <= %s
        RETURNING user_id, event_id;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (settled_timestamp, settled_timestamp, vault_id, settled_timestamp))
            results = cur.fetchall()
            updated_user_ids = [row[0] for row in results]
            updated_event_ids = [row[1] for row in results]
        conn.commit()
        wallets, txs_hashes = LagoonEventsHelpers.fetch_wallets_and_tx_hashes(db, updated_user_ids, updated_event_ids)
        return wallets, txs_hashes

    @staticmethod
    def update_canceled_deposit_request(db: Database, vault_id: str, request_id: int, cancel_timestamp: str):
        query = """
        UPDATE deposit_requests
        SET status = 'canceled', updated_at = %s
        WHERE vault_id = %s
          AND request_id = %s
          AND updated_at <= %s
        RETURNING user_id, event_id;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (cancel_timestamp, vault_id, request_id, cancel_timestamp))
            results = cur.fetchall()
            updated_user_ids = [row[0] for row in results]
            updated_event_ids = [row[1] for row in results]
        conn.commit()
        wallets, txs_hashes = LagoonEventsHelpers.fetch_wallets_and_tx_hashes(db, updated_user_ids, updated_event_ids)
        return wallets, txs_hashes

    @staticmethod
    def update_vault_rates(db: Database, vault_id: str, management_rate: int, performance_rate: int, update_timestamp: str):
        query = """
        UPDATE vaults
        SET management_rate = %s, performance_rate = %s, updated_at = %s
        WHERE vault_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (management_rate, performance_rate, update_timestamp, vault_id))
        conn.commit()

    @staticmethod
    def update_vault_status(db: Database, vault_id: str, status: str, update_timestamp: str):
        query = """
        UPDATE vaults
        SET status = %s, updated_at = %s
        WHERE vault_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (status, update_timestamp, vault_id))
        conn.commit()

    @staticmethod
    def update_vault_continue_indexing(db: Database, vault_address: str, chain_id: int, continue_indexing: bool):
        query = """
        UPDATE factory
        SET continue_indexing = %s
        WHERE vault_address = %s AND chain_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (continue_indexing, vault_address, chain_id))
        conn.commit()

    @staticmethod
    def update_settled_redeem_requests(db: Database, vault_id: str, settled_timestamp: str):
        query = """
        UPDATE redeem_requests
        SET status = 'settled', updated_at = %s, settled_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND updated_at <= %s
        RETURNING user_id, event_id;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (settled_timestamp, settled_timestamp, vault_id, settled_timestamp))
            results = cur.fetchall()
            updated_user_ids = [row[0] for row in results]
            updated_event_ids = [row[1] for row in results]
        conn.commit()
        wallets, txs_hashes = LagoonEventsHelpers.fetch_wallets_and_tx_hashes(db, updated_user_ids, updated_event_ids)
        return wallets, txs_hashes

    @staticmethod
    def update_completed_deposit(db: Database, vault_id: str, user_id: str, timestamp: datetime):
        query = """
        UPDATE deposit_requests
        SET status = 'completed', updated_at = %s
        WHERE vault_id = %s
          AND user_id = %s
          AND status = 'settled'
          AND settled_at <= %s
        RETURNING user_id, event_id;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp, vault_id, user_id, timestamp))
            results = cur.fetchall()
            updated_user_ids = [row[0] for row in results]
            updated_event_ids = [row[1] for row in results]
        conn.commit()
        wallets, txs_hashes = LagoonEventsHelpers.fetch_wallets_and_tx_hashes(db, updated_user_ids, updated_event_ids)
        return wallets, txs_hashes
    
    @staticmethod
    def update_completed_redeem(db: Database, vault_id: str, user_id: str, timestamp: datetime):
        query = """
        UPDATE redeem_requests
        SET status = 'completed', updated_at = %s
        WHERE vault_id = %s
          AND user_id = %s
          AND status = 'settled'
          AND settled_at <= %s
        RETURNING user_id, event_id;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp, vault_id, user_id, timestamp))
            results = cur.fetchall()
            updated_user_ids = [row[0] for row in results]
            updated_event_ids = [row[1] for row in results]
        conn.commit()
        wallets, txs_hashes = LagoonEventsHelpers.fetch_wallets_and_tx_hashes(db, updated_user_ids, updated_event_ids)
        return wallets, txs_hashes
        
    @staticmethod
    def update_vault_total_assets(db: Database, vault_id: str, total_assets: Decimal, update_timestamp: datetime):
        query = """
        UPDATE vaults
        SET total_assets = %s, updated_at = %s
        WHERE vault_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (total_assets, update_timestamp, vault_id))
        conn.commit()

    @staticmethod
    def update_vault_high_water_mark(db: Database, vault_id: str, high_water_mark: Decimal, update_timestamp: datetime):
        query = """
        UPDATE vaults
        SET high_water_mark = %s, updated_at = %s
        WHERE vault_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (high_water_mark, update_timestamp, vault_id))
        conn.commit()

    @staticmethod
    def update_deposit_request_referral(db: Database, vault_id: str, user_id: str, referral_user_id: str):
        """
        Update the referral address for a given deposit request.
        No ts is required for update since it's an immediate action to the deposit request.
        """
        query = """
        UPDATE deposit_requests
        SET referral_address = %s
        WHERE vault_id = %s
          AND user_id = %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (referral_user_id, vault_id, user_id))