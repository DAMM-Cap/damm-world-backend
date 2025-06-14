from db.db import Database

class LagoonDbUtils:
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
