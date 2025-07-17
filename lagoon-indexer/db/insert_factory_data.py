import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from db import getEnvDb
from utils.lagoon_db_date_utils import LagoonDbDateUtils
from web3 import Web3
from utils.rpc import get_rpc_url
from dotenv import load_dotenv
load_dotenv()

def get_factory_metadata(tx_hash: str, chain_id: int) -> dict:
    """
    Extracts metadata related to a vault and its associated silo from a factory creation transaction.

    This function analyzes the internal call trace of the given transaction using the `debug_traceTransaction`
    RPC method with the `callTracer` tracer.

    It identifies:
    - The vault contract: created via a `CREATE2` opcode just before the silo is created.
    - The silo contract: created via a `CREATE` opcode, triggered from the vault.
    - The block number in which the transaction was included.

    Parameters:
    ----------
    tx_hash : str
        The transaction hash of the factory creation.
    chain_id : int
        The EVM chain ID to resolve the appropriate RPC URL.

    Returns:
    -------
    dict
        A dictionary containing:
        - "vault": address of the vault (created via CREATE2)
        - "silo": address of the silo (created via CREATE)
        - "block_number": block number of the transaction
    """
    # Resolve RPC URL and set up Web3 provider
    rpc_url = get_rpc_url(chain_id)
    web3 = Web3(Web3.HTTPProvider(rpc_url))

    # Perform a call trace of the transaction using `debug_traceTransaction`
    trace = web3.provider.make_request("debug_traceTransaction", [
        tx_hash,
        {"tracer": "callTracer"}
    ])
    result = trace["result"]

    # Initialize storage for tracking contracts
    vault_address = None
    silo_address = None
    last_create2 = None

    def walk_trace_linear(call: dict) -> bool:
        """
        Traverses the call trace linearly (depth-first), looking for the CREATE2 (vault)
        followed by the CREATE (silo). Captures the vault address immediately before
        the silo is created and then terminates.

        Parameters:
        ----------
        call : dict
            A node in the call trace.

        Returns:
        -------
        bool
            True if the silo was found (terminates recursion), False otherwise.
        """
        nonlocal last_create2, vault_address, silo_address

        # If this is a CREATE2 call, store the contract address as a potential vault
        if call.get("type") == "CREATE2" and call.get("to"):
            last_create2 = Web3.to_checksum_address(call["to"])

        # If this is a CREATE call, assume it created the silo
        if call.get("type") == "CREATE" and call.get("to"):
            silo_address = Web3.to_checksum_address(call["to"])
            vault_address = last_create2  # Use the most recent CREATE2 as vault
            return True  # Stop traversal once the silo is found

        # Recursively inspect subcalls
        for subcall in call.get("calls", []):
            if walk_trace_linear(subcall):
                return True  # Stop if silo was found in subcall
        return False  # Continue traversal

    # Begin traversal of the trace
    walk_trace_linear(result)

    return {
        "vault": vault_address,
        "silo": silo_address,
        "block_number": web3.eth.get_transaction(tx_hash).blockNumber
    }

def insert_factory_data(creation_tx_hash: str, chain_id: int):
    db = getEnvDb(os.getenv("DB_NAME"))
    print("Inserting factory data...")
    
    metadata = get_factory_metadata(creation_tx_hash, chain_id)
    vault_address = metadata["vault"]
    silo_address = metadata["silo"]
    genesis_block_number = metadata["block_number"]
    print(f"Chain id: {chain_id}")
    print(f"Vault address: {vault_address}")
    print(f"Silo address: {silo_address}")
    print(f"Genesis block number: {genesis_block_number}")
    
    now_ts = LagoonDbDateUtils.get_datetime_formatted_now()

    with db.connection.cursor() as cursor:
        query = """
        INSERT INTO factory (
            creation_tx_hash,
            chain_id,
            genesis_block_number,
            vault_address,
            silo_address,
            created_at
        ) 
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (creation_tx_hash) DO NOTHING;
        """
        cursor.execute(query, (creation_tx_hash, chain_id, genesis_block_number, vault_address, silo_address, now_ts))
    db.connection.commit()
    print("Factory data inserted successfully.")
    db.closeConnection()


""" if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python your_script.py <tx_hash> <chain_id>")
        sys.exit(1)

    tx_hash = sys.argv[1]
    chain_id = int(sys.argv[2])

    contracts = get_internal_contracts(tx_hash, chain_id)
    print("Internal contracts created:")
    for addr in contracts:
        print(f"- {addr}")
 """