import subprocess
from utils.rpc import get_rpc_url

def run_safe_tx(url, contract, safe_address, *batched_args):
    cmd = [
        "yarn",
        "--cwd", "safe-tx",
        "send",
        "--rpc-url", url,
        "--lagoon", contract,
        "--safe", safe_address,
        *batched_args
    ]
    print("Running command:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("EXIT CODE:", result.returncode)

    if result.returncode != 0:
        raise RuntimeError("Safe transaction failed")

def keeper_txs_handler(chain_id, pending):
    """
    Handle keeper transactions.
    
    Args:
        chain_id: Chain ID
        pending: Pending transactions metadata
    
    Metadata format example:
    [{
        "status": "ok",
        "message": "Vault is in sync",
        "vault": {
            "vault_id": "0x123",
            "vault_address": "0x123",
            "safe": "0x123",
            "valuationManager": "0x123",
            "underlying_token_address": "0x123",
        },
        "txs": [
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
            },
            {
                "type": "approve",
                "assets": realTotalAssets,
                "caller": safeAddress,
                "vault_id": vault_id
            }
        ]
    }]
    """
    try:
        for instance in pending:
            vault_address = instance["vault"]["vault_address"]
            status = instance["status"]
            message = instance.get("message", "")

            if status == "syncing":
                print(f"[{vault_address}] Indexer syncing: {message}")
                continue

            if status == "error":
                raise Exception(f"[{vault_address}] Keeper error: {message}")

            if status != "ok":
                print(f"[{vault_address}] Unexpected status: {status} - {message}")
                continue

            instance_txs = instance.get("txs", [])
            if not instance_txs:
                print(f"[{vault_address}] No pending transactions found")
                continue

            print(f"[{vault_address}] Found {len(instance_txs)} pending transactions")

            batched_args = []

            for req in instance_txs:
                method = req["type"]
                contract = vault_address

                if method == "updateNewTotalAssets":
                    batched_args.extend([method, contract, str(req["assets"])])

                elif method == "settleDeposit":
                    batched_args.extend([method, contract, str(req["assets"])])

                elif method == "claimSharesOnBehalf":
                    batched_args.extend([method, contract, *req["controllers"]])

                elif method == "approve":
                    token_contract = instance["vault"]["underlying_token_address"]
                    batched_args.extend([
                        method, token_contract, contract, str(req["assets"])
                    ])

                else:
                    raise ValueError(f"[{vault_address}] Unknown request type: {method}")

            if batched_args:
                url = get_rpc_url(chain_id)
                run_safe_tx(url, contract, instance["vault"]["safe"], *batched_args)

        return True

    except Exception as e:
        print(f"[{chain_id}] Failed to process keeper requests: {e}")
        raise
