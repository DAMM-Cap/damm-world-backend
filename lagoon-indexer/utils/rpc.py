import os
import time
from web3 import Web3


FALLBACK_ENV_VARS = {
    480: "WORLDCHAIN_JSON_RPC",
    31337: "ANVIL_FORKED_WC_JSON_RPC",
    8453: "BASE_JSON_RPC",
    1: "MAINNET_JSON_RPC",
    11155111: "SEPOLIA_JSON_RPC",
}


def is_rpc_working(url: str) -> bool:
    try:
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 3}))
        return isinstance(w3.eth.block_number, int)
    except Exception as e:
        print(f"RPC test failed for {url}: {e}")
        return False


def get_rpc_url_candidates(chain_id: int) -> list[str]:
    urls = []

    if chain_id != 31337:
        gateway = os.getenv("RPC_GATEWAY")
        api_keys = os.getenv("RPC_API_KEYS", "")
        if gateway and api_keys:
            keys = [k.strip() for k in api_keys.split(",") if k.strip()]
            urls.extend([f"{gateway}/{chain_id}/{key}" for key in keys])

    fallback_env = FALLBACK_ENV_VARS.get(chain_id)
    if fallback_env:
        fallback_raw = os.getenv(fallback_env, "")
        urls.extend([u.strip() for u in fallback_raw.split(",") if u.strip()])

    return urls


def get_rpc_url(chain_id: int) -> str:
    """Eagerly return the first working URL (for shallow pre-check use)."""
    urls = get_rpc_url_candidates(chain_id)
    if not urls:
        raise ValueError(f"No RPC URLs configured for chain_id {chain_id}")

    for url in urls:
        print(f"[{chain_id}] Testing RPC: {url}")
        if is_rpc_working(url):
            print(f"[{chain_id}] Using RPC: {url}")
            return url
        else:
            print(f"[{chain_id}] RPC failed: {url}")

    raise ConnectionError(f"[{chain_id}] All RPCs failed in shallow test")


def get_w3(chain_id: int, retries_per_url: int = 2, delay: float = 2.0) -> Web3:
    """Returns a connected Web3 instance after rotating through candidates + retries."""
    urls = get_rpc_url_candidates(chain_id)
    if not urls:
        raise ValueError(f"No RPC URLs available for chain_id {chain_id}")

    for url in urls:
        for attempt in range(1, retries_per_url + 1):
            try:
                print(f"[{chain_id}] Connecting via Web3 ({attempt}/{retries_per_url}): {url}")
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 5}))
                if is_rpc_working(url):
                    print(f"[{chain_id}] Connected to RPC: {url}")
                    return w3
                else:
                    print(f"[{chain_id}] Web3 not connected: {url}")
            except Exception as e:
                print(f"[{chain_id}] Error on Web3 attempt {attempt}: {e}")
            time.sleep(delay)

    raise ConnectionError(f"[{chain_id}] Failed to connect to any RPC after retries")
