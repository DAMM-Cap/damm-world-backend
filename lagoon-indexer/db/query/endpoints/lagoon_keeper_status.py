from db.db import getEnvDb
from typing import Dict, Any
from db.query.lagoon_db_utils import LagoonDbUtils

def update_keeper_status(
    chain_id: int,
    vault_address: str,
    last_processed_block: int,
    last_processed_timestamp: str
) -> Dict[str, Any]:
    """
    Verifies vault_address and chain_id exist, then updates bot_status with sync progress.

    Args:
        chain_id: The chain ID for the vault.
        vault_address: The address of the vault.
        last_processed_block: The latest block processed by the bot.
        last_processed_timestamp: The timestamp of the latest processed block by the bot.

    Returns:
        A dictionary indicating success or error details.
    """
    try:
        # Initialize database connection
        db = getEnvDb('damm-public')

        # 1) Check vault exists
        vaults_query = """
            SELECT v.vault_id FROM vaults v JOIN tokens t ON v.vault_token_id = t.token_id WHERE t.address = %s
        """
        vaults_df = db.frameResponse(vaults_query, (vault_address,))
        if vaults_df.empty:
            return {
                "success": False,
                "error": f"Vault address {vault_address} does not exist in vaults table"
            }
        
        vault_id = vaults_df.iloc[0]['vault_id']

        # 2) Check chain exists
        chains_query = """
            SELECT 1 FROM chains WHERE chain_id = %s
        """
        chains_df = db.frameResponse(chains_query, (chain_id,))
        if chains_df.empty:
            return {
                "success": False,
                "error": f"Chain ID {chain_id} does not exist in chains table"
            }

        # 3) Update bot_status table
        LagoonDbUtils.update_bot_status(db, vault_id, chain_id, last_processed_block, last_processed_timestamp)

        return {
            "success": True,
            "message": f"Updated bot_status for vault_address={vault_address}, chain_id={chain_id}"
        }

    except Exception as e:
        print(f"Error in update_keeper_status: {e}")
        return {"success": False, "error": str(e)}
