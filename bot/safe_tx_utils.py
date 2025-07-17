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
            # Handle different response statuses
            if instance["status"] == "syncing":
                print(f"[{instance['vault']['vault_address']}]", instance["message"], "Indexer is syncing")
                return
            if instance["status"] == "error":
                raise Exception(f"[{instance['vault']['vault_address']}]", instance["message"], "Unknown error")
            if instance["status"] == "ok":
                # Check if there are any transactions
                instance_txs = instance["txs"]
                if len(instance_txs) == 0:
                    print(f"[{instance['vault']['vault_address']}]", "No pending transactions found")
                    return

                print(f"[{instance['vault']['vault_address']}]", f"Found {len(instance_txs)} pending transactions to trigger")
            
                batched_args = []

                for req in instance_txs:
                    method = req["type"]
                    contract = instance["vault"]["vault_address"]

                    if method == "updateNewTotalAssets":
                        assets = str(req["assets"])
                        batched_args.extend([method, contract, assets])

                    elif method == "settleDeposit":
                        assets = str(req["assets"])
                        batched_args.extend([method, contract, assets])

                    elif method == "claimSharesOnBehalf":
                        controllers = req["controllers"]
                        batched_args.extend([method, contract, *controllers])

                    elif method == "approve":
                        token_contract = instance["vault"]["underlying_token_address"]
                        assets = str(req["assets"])
                        batched_args.extend([method, token_contract, *[contract, assets]])

                    else:
                        raise ValueError(f"Unknown request type: {method}")

                if batched_args:
                    url = get_rpc_url(chain_id)
                    run_safe_tx(url, contract, instance["vault"]["safe"], *batched_args)

            else:
                # Fallback for unexpected response format
                print(f"[{instance['vault']['vault_address']}]", f"Unexpected response format: {instance}")
                return

        return True

    except Exception as e:
        print(f"Failed to process requests: {e}")
        raise
