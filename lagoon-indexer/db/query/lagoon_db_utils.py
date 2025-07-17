from db.db import Database
import uuid
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from datetime import timedelta, datetime
from typing import Tuple, Optional
from decimal import Decimal
from math import pow
from db.query.lagoon_events import LagoonEvents

class LagoonDbUtils:
    @staticmethod
    def get_user_id(db: Database, address: str, chain_id: int, current_event_ts: datetime) -> str:
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
            result = db.queryResponse(query, (user_id, address, chain_id, current_event_ts, current_event_ts))                
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
    def get_bot_last_processed_block(db: Database, vault_id: str, chain_id: int, default_block: int) -> int:
        """
        Retrieve the last processed block recorded by the bot for a given vault_id.
        If no record exists in bot_status, return the default_block.
        """
        query = """
        SELECT COALESCE(last_processed_block, %s) AS last_block
        FROM bot_status
        WHERE vault_id = %s AND chain_id = %s
        """
        result = db.queryResponse(query, (default_block, vault_id, chain_id))

        if result and 'last_block' in result[0]:
            return int(result[0]['last_block'])
        else:
            return default_block

    @staticmethod
    def update_last_processed_block(db: Database, vault_id: str, chain_id: int, last_block: int, is_syncing: bool):
        """
        Update the last processed block for a given vault_id.
        """
        query = """
        UPDATE indexer_state
        SET
            last_processed_block = %s,
            last_processed_timestamp = %s,
            updated_at = %s,
            is_syncing = %s
        WHERE vault_id = %s AND chain_id = %s
        """
        formatted_ts = LagoonDbDateUtils.get_datetime_formatted_now()
        db.execute(query, (last_block, formatted_ts, formatted_ts, is_syncing, vault_id, chain_id))

    @staticmethod
    def update_bot_status(db: Database, vault_id: str, chain_id: int, last_processed_block: int, last_processed_timestamp: str):
        """
        Update the bot status for a given vault_id.
        """
        query = """
            UPDATE bot_status
            SET
                last_processed_block = %s,
                last_processed_timestamp = %s,
                in_sync = %s,
                updated_at = %s
            WHERE vault_id = %s AND chain_id = %s
        """
        now_ts = LagoonDbDateUtils.get_datetime_formatted_now()
        db.execute(query, (last_processed_block, last_processed_timestamp, False, now_ts, vault_id, chain_id))
    
    @staticmethod
    def update_bot_in_sync(db: Database, vault_id: str, chain_id: int):
        """
        Update the bot status to in sync when the indexer catches up.
        """
        query = """
            UPDATE bot_status
            SET
                in_sync = %s,
                updated_at = %s
            WHERE vault_id = %s AND chain_id = %s
        """
        now_ts = LagoonDbDateUtils.get_datetime_formatted_now()
        db.execute(query, (True, now_ts, vault_id, chain_id))

    @staticmethod
    def get_delta_hours_and_apy_12h_ago(db: Database, vault_id: str, current_share_price: Decimal, current_event_ts: datetime) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Calculate APY based on the share price from approximately 12 hours ago.

        Returns:
            delta_hours (Optional[Decimal]): Hours between the snapshot and now.
            apy (Optional[Decimal]): Annualized yield based on share price change.
        """
        query = """
        SELECT events.event_timestamp, share_price FROM vault_snapshots 
        JOIN events ON vault_snapshots.event_id = events.event_id 
        WHERE vault_snapshots.vault_id = %s
        ORDER BY ABS(EXTRACT(EPOCH FROM events.event_timestamp - %s)) ASC
        LIMIT 1;
        """
        formatted_past_ts = LagoonDbDateUtils.format_timestamp(current_event_ts - timedelta(hours=12))
        result = db.queryResponse(query, (vault_id, formatted_past_ts))
        if result and 'share_price' in result[0] and 'event_timestamp' in result[0]:
            share_price_12h_ago = Decimal(result[0]['share_price'])
            snapshot_ts = result[0]['event_timestamp']
            if isinstance(snapshot_ts, str):
                snapshot_ts = LagoonDbDateUtils.get_datetime_from_str(snapshot_ts)
            delta_hours = (current_event_ts - snapshot_ts).total_seconds() / 3600
            if share_price_12h_ago > 0 and delta_hours > 0:
                apy = (pow(float(current_share_price / share_price_12h_ago), float(8760 / delta_hours)) - 1) * 100
                apy = Decimal(str(apy))
                return delta_hours, apy, snapshot_ts
        
        return None, None, None
    
    @staticmethod
    def _calculate_management_fee(assets: Decimal, rate_bps: int, last_ts: datetime, current_ts: datetime) -> Decimal:
        seconds_in_year = Decimal(365 * 24 * 60 * 60)
        time_elapsed = Decimal((current_ts - last_ts).total_seconds())

        if time_elapsed <= 0 or assets <= 0 or rate_bps <= 0:
            return Decimal("0.0")

        fee = assets * Decimal(rate_bps) / Decimal(10_000) * (time_elapsed / seconds_in_year)
        return fee.quantize(Decimal("0.000001"))

    @staticmethod
    def get_management_fee(db: Database, vault_id: str, total_assets: Decimal, last_ts: datetime, current_event_ts: datetime) -> Optional[Decimal]:
        """
        Get the management fee for a given vault_id.
        """
        query = """
        SELECT management_rate FROM vaults WHERE vault_id = %s
        """
        result = db.queryResponse(query, (vault_id,))
        if result and 'management_rate' in result[0]:
            management_rate = result[0]['management_rate']
            management_fee = LagoonDbUtils._calculate_management_fee(total_assets, management_rate, last_ts, current_event_ts)
            return management_fee
        else:
            return None
    
    @staticmethod
    def get_performance_fee(db: Database, vault_id: str, total_shares: Decimal, share_price: Decimal, current_event_ts: datetime) -> Optional[Decimal]:
        """
        Get the performance fee for a given vault_id.
        """
        query = """
        SELECT performance_rate, high_water_mark FROM vaults WHERE vault_id = %s
        """
        result = db.queryResponse(query, (vault_id,))
        if result and 'performance_rate' in result[0] and 'high_water_mark' in result[0]:
            performance_rate = result[0]['performance_rate']
            high_water_mark = result[0]['high_water_mark']
            if share_price > high_water_mark:
                LagoonEvents.update_vault_high_water_mark(db, vault_id, share_price, current_event_ts)
                profit = (share_price - high_water_mark) * total_shares
                performance_fee = (profit * performance_rate) / 10000
                return performance_fee
            else:
                return None
        else:
            return None
    
    @staticmethod
    def get_deployments_from_chain_id(db: Database, chain_id: int) -> Tuple[str, str, int]:
        """
        Get the deployments for a given chain_id.
        """
        query = """
        SELECT vault_address, silo_address, genesis_block_number FROM factory WHERE chain_id = %s
        """
        result = db.queryResponse(query, (chain_id,))
        return result

    @staticmethod
    def handle_vault_snapshot(db: Database, vault_id: str, total_assets: Decimal, total_shares: Decimal, share_price: Decimal, current_event_ts: datetime) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Handle the vault snapshot for a given vault_id.
        """
        delta_hours, apy, prev_snapshot_ts = LagoonDbUtils.get_delta_hours_and_apy_12h_ago(
            db, 
            vault_id, 
            share_price, 
            current_event_ts
        )

        if prev_snapshot_ts is None:
            return None, None, None, None
        
        management_fee = LagoonDbUtils.get_management_fee(
            db,
            vault_id, 
            total_assets, 
            prev_snapshot_ts, 
            current_event_ts
        )
        performance_fee = LagoonDbUtils.get_performance_fee(
            db,
            vault_id, 
            total_shares,
            share_price,
            current_event_ts
        )
        return delta_hours, apy, management_fee, performance_fee
