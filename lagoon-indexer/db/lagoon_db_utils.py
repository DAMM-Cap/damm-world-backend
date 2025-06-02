from db.db import Database

class LagoonDbUtils:
    @staticmethod
    def get_last_processed_block(db: Database, chain_id: int, lagoon_address: str, default_block: int) -> int:
        """
        Retrieve the last processed block for the Lagoon indexer.
        If no record exists, return the default_block.
        """
        query = f"""
        SELECT COALESCE(last_processed_block, {default_block}) AS last_block
        FROM lagoon_last_processed
        WHERE chain_id = {chain_id} AND contract_address = '{lagoon_address}'
        """
        result = db.queryResponse(query)
        if result and 'last_block' in result[0]:
            return int(result[0]['last_block'])
        else:
            return default_block

    @staticmethod
    def update_last_processed_block(db: Database, chain_id: int, lagoon_address: str, last_block: int):
        """
        Update the last processed block for the Lagoon indexer.
        """
        query = f"""
        INSERT INTO lagoon_last_processed (chain_id, contract_address, last_processed_block)
        VALUES ({chain_id}, '{lagoon_address}', {last_block})
        ON CONFLICT (chain_id, contract_address)
        DO UPDATE SET last_processed_block = EXCLUDED.last_processed_block, updated_at = NOW();
        """
        db.execute(query)
