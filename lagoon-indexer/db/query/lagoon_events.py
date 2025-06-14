from datetime import datetime
from db.db import Database
from pandas import DataFrame

def insert_lagoon_events(event_df: DataFrame, table_name: str, db: Database):
    filtered_cols = [c for c in event_df.columns]
    cleaned_df = event_df[filtered_cols]
    
    #db.insertDf(cleaned_df, table_name)
    db.insertDf(cleaned_df, "events")

class LagoonEvents:
    @staticmethod
    def update_settled_deposit_requests(db: Database, vault_id: str, settled_timestamp: datetime):
        query = """
        UPDATE lagoon_depositrequest
        SET status = 'settled', status_updated_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND timestamp <= %s;
        """
        timestamp_str = settled_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp_str, vault_id, timestamp_str))
        conn.commit()

    @staticmethod
    def update_canceled_deposit_request(db: Database, vault_id: str, request_id: int, cancel_timestamp: datetime):
        query = """
        UPDATE lagoon_depositrequest
        SET status = 'canceled', status_updated_at = %s
        WHERE vault_id = %s
          AND request_id = %s
          AND timestamp <= %s;
        """
        timestamp_str = cancel_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp_str, vault_id, request_id, timestamp_str))
        conn.commit()

    @staticmethod
    def update_settled_redeem_requests(db: Database, vault_id: str, settled_timestamp: datetime):
        query = """
        UPDATE lagoon_redeemrequest
        SET status = 'settled', status_updated_at = %s
        WHERE vault_id = %s
          AND status = 'pending'
          AND timestamp <= %s;
        """
        timestamp_str = settled_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        conn = db.connection
        with conn.cursor() as cur:
            cur.execute(query, (timestamp_str, vault_id, timestamp_str))
        conn.commit()
