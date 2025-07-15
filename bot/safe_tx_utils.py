from core.lagoon_deployments import get_lagoon_deployments
import subprocess
from utils.rpc import get_rpc_url

def run_safe_tx(url, *batched_args):
    cmd = [
        "yarn",
        "--cwd", "safe-tx",
        "send",
        "--rpc-url", url,
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
            },
            {
                "type": "approve",
                "contract": token_contract,
                "caller": safeAddress,
                "vault_id": vault_id
            }
        ]
    }
    """
    try:
        batched_args = []

        for req in pending['vaults_txs']:
            method = req["type"]
            contract = get_lagoon_deployments(chain_id)["lagoon_address"]

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
                token_contract = req["contract"]
                assets = str(req["assets"])
                batched_args.extend([method, token_contract, *[contract, assets]])

            else:
                raise ValueError(f"Unknown request type: {method}")

        if batched_args:
            url = get_rpc_url(chain_id)
            run_safe_tx(url, *batched_args)

        return True

    except Exception as e:
        print(f"Failed to process requests: {e}")
        raise
