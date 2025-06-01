class LagoonDbUtils:
    @staticmethod
    def get_last_processed_block(db, chain_id: int, lagoon_address: str, default_block: int) -> int:
        query = """
        SELECT COALESCE(last_processed_block, :default_block)
        FROM lagoon_last_processed
        WHERE chain_id = :chain_id AND contract_address = :contract_address
        """
        result = db.queryResponse(query, {
            "default_block": default_block,
            "chain_id": chain_id,
            "contract_address": lagoon_address
        })
        return int(result[0]['coalesce'])

    @staticmethod
    def update_last_processed_block(db, chain_id: int, lagoon_address: str, last_block: int):
        query = """
        INSERT INTO lagoon_last_processed (chain_id, contract_address, last_processed_block)
        VALUES (:chain_id, :contract_address, :last_block)
        ON CONFLICT (chain_id, contract_address)
        DO UPDATE SET last_processed_block = EXCLUDED.last_processed_block, updated_at = NOW();
        """
        db.execute(query, {
            "chain_id": chain_id,
            "contract_address": lagoon_address,
            "last_block": last_block
        })
