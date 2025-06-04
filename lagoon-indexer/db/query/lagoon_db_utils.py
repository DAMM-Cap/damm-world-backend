from db.db import Database

class LagoonDbUtils:
    @staticmethod
    def get_last_processed_block(db: Database, vault_id: int, default_block: int) -> int:
        """
        Retrieve the last processed block for a given vault_id.
        If no record exists, return the default_block.
        """
        query = f"""
        SELECT COALESCE(last_processed_block, {default_block}) AS last_block
        FROM lagoon_last_processed
        WHERE vault_id = {vault_id}
        """
        result = db.queryResponse(query)
        if result and 'last_block' in result[0]:
            return int(result[0]['last_block'])
        else:
            return default_block

    @staticmethod
    def update_last_processed_block(db: Database, vault_id: int, last_block: int):
        """
        Update the last processed block for a given vault_id.
        """
        query = f"""
        INSERT INTO lagoon_last_processed (vault_id, last_processed_block)
        VALUES ({vault_id}, {last_block})
        ON CONFLICT (vault_id)
        DO UPDATE SET last_processed_block = EXCLUDED.last_processed_block, updated_at = NOW();
        """
        db.execute(query)
