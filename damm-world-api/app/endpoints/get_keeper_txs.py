from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_keeper_txs import get_keepers_pending_txs_metadata
from core.lagoon_deployments import get_lagoon_deployments
from utils.rpc import get_w3
from app.constants.abi.lagoon import LAGOON_ABI
from app.constants.abi.erc20 import ERC20_ABI

router = APIRouter()

def get_new_total_assets(chain_id: int = 480):
    vault_address = get_lagoon_deployments(chain_id)["lagoon_address"]
    safe_address = get_lagoon_deployments(chain_id)["safe_address"]
    w3 = get_w3(chain_id)
    vault_contract = w3.eth.contract(address=vault_address, abi=LAGOON_ABI)
    deposit_token_address = vault_contract.functions.asset().call()
    deposit_token_contract = w3.eth.contract(address=deposit_token_address, abi=ERC20_ABI)
    realTotalAssets = deposit_token_contract.functions.balanceOf(safe_address).call()
    return realTotalAssets

def get_keeper_txs(chain_id: int = 480):
    result = get_keepers_pending_txs_metadata(chain_id)
    if result["status"] == "syncing":
        return result
    if result["status"] == "error":
        return result
    if len(result["vaults_txs"]) == 0:
        return result
    
    """ Result JSON format example:
    result = {
        "vaults_txs": [
            {
                "vault_id": "0x123",
                "initialUpdate": True,
                "pendingDeposit": True,
                "pendingRedeem": True,
                "settledDeposit": [
                    "0x0000000000000000000000000000000000000000", 
                    "0x0000000000000000000000000000000000000000"
                ],
                "valuationManager": "0x123",
                "safe": "0x123"
            }
        ]
    } """
    txs = []
    
    for vault_txs in result["vaults_txs"]:
        if vault_txs["initialUpdate"] == True:
            realTotalAssets = 0
            txs.append({
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                "caller": vault_txs["valuationManager"],
                "vault_id": vault_txs["vault_id"]
            })
            continue
        if vault_txs["pendingDeposit"] == True or vault_txs["pendingRedeem"] == True:
            realTotalAssets = get_new_total_assets(chain_id)
            txs.append({
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                "caller": vault_txs["valuationManager"],
                "vault_id": vault_txs["vault_id"]
            })
            if vault_txs["pendingRedeem"] == True:
                # The underlying_token address must approve the Vault to handle the required 
                # amount of assets for redeem settlement.
                # That is: asset.approve(vaultAddress, realTotalAssets);
                txs.append({
                    "type": "approve",
                    "contract": vault_txs["underlying_token_address"],
                    "assets": realTotalAssets,
                    "caller": vault_txs["safe"],
                    "vault_id": vault_txs["vault_id"]
                })
            # Lagoon's deposit settlement includes settle redeem.
            txs.append({
                "type": "settleDeposit",
                "assets": realTotalAssets,
                "caller": vault_txs["safe"],
                "vault_id": vault_txs["vault_id"]
            })
        if len(vault_txs["settledDeposit"]) > 0:
            txs.append({
                "type": "claimSharesOnBehalf",
                "controllers": vault_txs["settledDeposit"],
                "caller": vault_txs["safe"],
                "vault_id": vault_txs["vault_id"]
            })
    return {"status": "ok", "vaults_txs": txs}


@router.get("/lagoon/keeper_txs/test/{chain_id}")
def read_keeper_txs_test(
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
):
    result = get_keeper_txs(chain_id)
    return result
    
@router.get("/lagoon/keeper_txs")
def read_keeper_txs(
    current_user: dict = Depends(get_current_user_jwt),
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
):
    result = get_keeper_txs(chain_id)
    return result
