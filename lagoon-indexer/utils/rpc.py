import os

from web3 import Web3

def get_rpc_url(chain_id):
    try:
        return f"{os.getenv('RPC_GATEWAY')}/{chain_id}/{os.getenv('RPC_API_KEY')}"
    except Exception as e:
        print(f"Error getting Premium RPC URL: {e}")
        print(f"Using fallback RPC URL")
        if chain_id == 480:
            return os.getenv('WORLDCHAIN_JSON_RPC')
        elif chain_id == 31337:
            return os.getenv('ANVIL_FORKED_WC_JSON_RPC')
        elif chain_id == 8453:
            return os.getenv('BASE_JSON_RPC')
        else:
            raise Exception('RPC unavailable for that chain_id')

def get_w3(chain_id):
    return Web3(Web3.HTTPProvider(get_rpc_url(chain_id)))
