import os
from dotenv import load_dotenv
from core.lagoon_deployments import get_lagoon_deployments
from utils.rpc import get_w3
from constants.abi.lagoon import LAGOON_ABI

# Load environment variables
load_dotenv()
        
def get_vault_contract(w3, chain_id):
    vault_address = get_lagoon_deployments(chain_id)["lagoon_address"]
    vault_contract = w3.eth.contract(address=vault_address, abi=LAGOON_ABI)
    return vault_contract

def get_keeper_credentials(chain_id):
    keeper_address = get_lagoon_deployments(chain_id)["safe_address"]
    keeper_private_key = os.getenv("KEEPER_PRIVATE_KEY")
    
    if not keeper_address or not keeper_private_key:
        raise ValueError("KEEPER_ADDRESS and KEEPER_PRIVATE_KEY environment variables are required")
        
    return keeper_address, keeper_private_key

def handle_request(req, contract, keeper_address, keeper_private_key, w3):
    """
    Handle a request.
    
    Args:
        chain_id: Chain ID
        req: Request object with type and assets
        
    Returns:
        str: Transaction hash
    """
    try:
        # Build transaction based on request type
        if req['type'] == 'claimSharesOnBehalf':
            tx = contract.functions.claimSharesOnBehalf(req['controllers']).build_transaction({
                'from': keeper_address,
                'nonce': w3.eth.get_transaction_count(keeper_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
        elif req['type'] == 'updateNewTotalAssets':
            tx = contract.functions.updateNewTotalAssets(req['assets']).build_transaction({
                'from': keeper_address,
                'nonce': w3.eth.get_transaction_count(keeper_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
        elif req['type'] == 'settleDeposit':
            tx = contract.functions.settleDeposit(req['assets']).build_transaction({
                'from': keeper_address,
                'nonce': w3.eth.get_transaction_count(keeper_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
        else:
            raise ValueError(f"Unknown request type: {req['type']}")
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=keeper_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"Request {req['type']} successfully processed. Tx hash: {tx_hash.hex()}")
        return tx_hash.hex()
        
    except Exception as e:
        print(f"Failed to process request {req['type']}: {e}")
        raise

def keeper_txs_handler(chain_id, pending):
    """
    Handle keeper transactions.
    
    Args:
        chain_id: Chain ID
        pending: Pending transactions metadata
    
    Metadata format example:
    {
        "txs": [
            {
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                "caller": "valuationManager"
            },
            {
                "type": "settleDeposit",
                "assets": realTotalAssets,
                "caller": "safe"
            },
            {
                "type": "claimSharesOnBehalf",
                "controllers": [
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000"
                ],
                "caller": "safe"
            }
        ]
    }
    """
    try:
        # Get keeper credentials
        keeper_address, keeper_private_key = get_keeper_credentials(chain_id)

        # Initialize Web3 connection
        w3 = get_w3(chain_id)

        # Get contract
        contract = get_vault_contract(w3, chain_id)
    
        for req in pending['txs']:
            handle_request(req, contract, keeper_address, keeper_private_key, w3)
            
    except Exception as e:
        print(f"Failed to process requests: {e}")
        raise