from db.db import Database
import uuid
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from datetime import timedelta
from typing import Tuple, Optional

class LagoonDbUtils:
    @staticmethod
    def get_user_id(db: Database, address: str, chain_id: int) -> str:
        """
        Retrieve the user_id for a given address and chain_id. If no user_id is found, creates the user and returns the user_id.
        """
        query = """
        SELECT user_id FROM users WHERE address = %s AND chain_id = %s
        """
        result = db.queryResponse(query, (address, chain_id))
        
        if result and 'user_id' in result[0]:
            return result[0]['user_id']
        else:
            user_id = str(uuid.uuid4())
            query = """
            INSERT INTO users (user_id, address, chain_id, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING user_id
            """
            formatted_ts = LagoonDbDateUtils.get_datetime_formatted_now()
            result = db.queryResponse(query, (user_id, address, chain_id, formatted_ts, formatted_ts))                
            if result and 'user_id' in result[0]:
                return result[0]['user_id']
            else:
                raise Exception(f"Failed to create user for address {address} on chain {chain_id}. Insert returned: {result}")
            
    @staticmethod
    def get_last_processed_block(db: Database, vault_id: str, chain_id: int, default_block: int) -> int:
        """
        Retrieve the last processed block for a given vault_id.
        If no record exists, return the default_block.
        """
        query = """
        SELECT COALESCE(last_processed_block, %s) AS last_block
        FROM indexer_state
        WHERE vault_id = %s AND chain_id = %s
        """
        result = db.queryResponse(query, (default_block, vault_id, chain_id))

        if result and 'last_block' in result[0]:
            return int(result[0]['last_block'])
        else:
            return default_block

    @staticmethod
    def update_last_processed_block(db: Database, vault_id: str, chain_id: int, last_block: int):
        """
        Update the last processed block for a given vault_id.
        """
        query = """
        UPDATE indexer_state
        SET
            last_processed_block = %s,
            last_processed_timestamp = %s,
            updated_at = %s
        WHERE vault_id = %s AND chain_id = %s
        """
        formatted_ts = LagoonDbDateUtils.get_datetime_formatted_now()
        db.execute(query, (last_block, formatted_ts, formatted_ts, vault_id, chain_id))

    @staticmethod
    def get_delta_hours_and_apy_12h_ago(db: Database, vault_id: str, current_share_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate APY based on the share price from approximately 12 hours ago.

        Returns:
            delta_hours (Optional[float]): Hours between the snapshot and now.
            apy (Optional[float]): Annualized yield based on share price change.
        """
        query = """
        SELECT events.event_timestamp, share_price FROM vault_snapshots 
        JOIN events ON vault_snapshots.event_id = events.event_id 
        WHERE vault_snapshots.vault_id = %s AND events.event_timestamp <= %s
        ORDER BY events.event_timestamp DESC
        LIMIT 1;
        """
        formatted_now_ts = LagoonDbDateUtils.get_datetime_formatted_now()
        formatted_past_ts = LagoonDbDateUtils.format_timestamp(formatted_now_ts - timedelta(hours=12))
        result = db.queryResponse(query, (vault_id, formatted_past_ts))
        if result and 'share_price' in result[0] and 'event_timestamp' in result[0]:
            share_price_12h_ago = float(result[0]['share_price'])
            snapshot_ts = result[0]['event_timestamp']
            if isinstance(snapshot_ts, str):
                snapshot_ts = LagoonDbDateUtils.get_datetime_from_str(snapshot_ts)
            delta_hours = (formatted_now_ts - snapshot_ts).total_seconds() / 3600
            if share_price_12h_ago > 0 and delta_hours > 0:
                apy = ((current_share_price / share_price_12h_ago) ** (8760 / delta_hours) - 1) * 100
                return delta_hours, apy
        
        return None, None