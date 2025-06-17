from db.db import Database
from datetime import datetime
import uuid

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
            result = db.queryResponse(query, (user_id, address, chain_id, datetime.now(), datetime.now()))                
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
            last_processed_timestamp = NOW(),
            updated_at = NOW()
        WHERE vault_id = %s AND chain_id = %s
        """
        db.execute(query, (last_block, vault_id, chain_id))
