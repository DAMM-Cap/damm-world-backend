from db.db import Database
from pandas import DataFrame

def insert_lagoon_events(event_df: DataFrame, table_name: str, db: Database):
    filtered_cols = [c for c in event_df.columns]
    cleaned_df = event_df[filtered_cols]
    db.insertDf(cleaned_df, table_name)

class LagoonEvents:
    @staticmethod
    def update_settled_deposit_requests(db: Database, vault_id: str, settled_timestamp: str):
        query = """
        UPDATE deposit_requests
        SET status = 'settled', updated_at = %s, settled_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND updated_at <= %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (settled_timestamp, settled_timestamp, vault_id, settled_timestamp))
        conn.commit()

    @staticmethod
    def update_canceled_deposit_request(db: Database, vault_id: str, request_id: int, cancel_timestamp: str):
        query = """
        UPDATE deposit_requests
        SET status = 'canceled', updated_at = %s
        WHERE vault_id = %s
          AND request_id = %s
          AND updated_at <= %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (cancel_timestamp, vault_id, request_id, cancel_timestamp))
        conn.commit()

    @staticmethod
    def update_settled_redeem_requests(db: Database, vault_id: str, settled_timestamp: str):
        query = """
        UPDATE redeem_requests
        SET status = 'settled', updated_at = %s, settled_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND updated_at <= %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (settled_timestamp, settled_timestamp, vault_id, settled_timestamp))
        conn.commit()

    @staticmethod
    def update_completed_deposit(db: Database, vault_id: str, timestamp: str):
        query = """
        UPDATE deposit_requests
        SET status = 'completed', updated_at = %s
        WHERE vault_id = %s
          AND status = 'settled'
          AND updated_at <= %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp, vault_id, timestamp))
        conn.commit()
    
    @staticmethod
    def update_completed_redeem(db: Database, vault_id: str, timestamp: str):
        query = """
        UPDATE redeem_requests
        SET status = 'completed', updated_at = %s
        WHERE vault_id = %s
          AND status = 'settled'
          AND updated_at <= %s;
        """
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp, vault_id, timestamp))
        conn.commit()