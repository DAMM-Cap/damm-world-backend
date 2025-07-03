import os

from web3 import Web3

def get_rpc_url_fallback(chain_id):
    print(f"Using fallback RPC URL")
    if chain_id == 480:
        return os.getenv('WORLDCHAIN_JSON_RPC')
    elif chain_id == 31337:
        return os.getenv('ANVIL_FORKED_WC_JSON_RPC')
    elif chain_id == 8453:
        return os.getenv('BASE_JSON_RPC')
    elif chain_id == 1:
        return os.getenv('MAINNET_JSON_RPC')
    elif chain_id == 11155111:
        return os.getenv('SEPOLIA_JSON_RPC')
    else:
        raise Exception('RPC unavailable for that chain_id')

def get_rpc_url(chain_id):
    try:
        if chain_id == 31337: 
            return os.getenv('ANVIL_FORKED_WC_JSON_RPC')
        return f"{os.getenv('RPC_GATEWAY')}/{chain_id}/{os.getenv('RPC_API_KEY')}"
    except Exception as e:
        print(f"Error getting Premium RPC URL: {e}")
        return get_rpc_url_fallback(chain_id)

def get_w3(chain_id):
    w3 = Web3(Web3.HTTPProvider(get_rpc_url(chain_id)))
    if not w3.is_connected():
        print(f"Failed to connect to RPC at {w3.provider.endpoint_uri}")
        
        w3 = Web3(Web3.HTTPProvider(get_rpc_url_fallback(chain_id)))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC at {w3.provider.endpoint_uri}")
    return w3
