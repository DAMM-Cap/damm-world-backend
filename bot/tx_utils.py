import os
from dotenv import load_dotenv
from core.lagoon_deployments import get_lagoon_deployments
from utils.rpc import get_w3
from constants.abi.lagoon import LAGOON_ABI
from batch_utils import process_batch_transactions

# Load environment variables
load_dotenv()
        
def get_vault_contract(w3, chain_id):
    vault_address = get_lagoon_deployments(chain_id)["lagoon_address"]
    vault_contract = w3.eth.contract(address=vault_address, abi=LAGOON_ABI)
    return vault_contract

def get_safe_credentials(chain_id):
    safe_private_key = os.getenv("SAFE_PRIVATE_KEY")

    if not safe_private_key:
        raise ValueError("SAFE_PRIVATE_KEY environment variable required")
    
    return safe_private_key

def get_valuation_manager_credentials(chain_id):
    vm_pk = os.getenv("VM_PRIVATE_KEY")
    
    if not vm_pk:
        raise ValueError("VM_PRIVATE_KEY environment variable required")
        
    return vm_pk

def handle_request(req, contract, w3):
    """
    Handle a request.
    
    Args:
        req: Request object with type, caller and call parameters.
        contract: Contract object
        w3: Web3 object
    """
    try:
        txs_safe = []
        txs_vm = []
        # Build transaction based on request type
        if req['type'] == 'claimSharesOnBehalf':
            safe_address = req['caller']
            tx = contract.functions.claimSharesOnBehalf(req['controllers']).build_transaction({
                'from': safe_address,
                'nonce': w3.eth.get_transaction_count(safe_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
            txs_safe.append(tx)
        elif req['type'] == 'updateNewTotalAssets':
            valuation_manager_address = req['caller']
            tx = contract.functions.updateNewTotalAssets(req['assets']).build_transaction({
                'from': valuation_manager_address,
                'nonce': w3.eth.get_transaction_count(valuation_manager_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
            txs_vm.append(tx)
        elif req['type'] == 'settleDeposit':
            safe_address = req['caller']
            tx = contract.functions.settleDeposit(req['assets']).build_transaction({
                'from': safe_address,
                'nonce': w3.eth.get_transaction_count(safe_address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            })
            txs_safe.append(tx)
        else:
            raise ValueError(f"Unknown request type: {req['type']}")
        
        return txs_safe, txs_vm
        
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
        "vaults_txs": [
            {
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                "caller": valuationManagerAddress,
                "vault_id": vault_id
            },
            {
                "type": "settleDeposit",
                "assets": realTotalAssets,
                "caller": safeAddress,
                "vault_id": vault_id
            },
            {
                "type": "claimSharesOnBehalf",
                "controllers": [
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000"
                ],
                "caller": safeAddress,
                "vault_id": vault_id
            }
        ]
    }
    """
    try:
        # Initialize Web3 connection
        w3 = get_w3(chain_id)

        # Get contract
        contract = get_vault_contract(w3, chain_id)
    
        for req in pending['vaults_txs']:
            txs_safe, txs_vm = handle_request(req, contract, w3)

            # Sign and batch transactions
            signed_txs = []
            if len(txs_safe)>0:
                safe_private_key = get_safe_credentials(chain_id)
                for tx in txs_safe:
                    signed_tx_safe = w3.eth.account.sign_transaction(tx, private_key=safe_private_key)
                    signed_txs.append(signed_tx_safe)

            if len(txs_vm)>0:
                vm_pk = get_valuation_manager_credentials(chain_id)
                for tx in txs_vm:
                    signed_tx_vm = w3.eth.account.sign_transaction(tx, private_key=vm_pk)
                    signed_txs.append(signed_tx_vm)

            process_batch_transactions(w3, signed_txs)

        return True
            
    except Exception as e:
        print(f"Failed to process requests: {e}")
        raise