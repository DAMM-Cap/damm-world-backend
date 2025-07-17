from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_keeper_txs import get_keepers_pending_txs_metadata
from utils.rpc import get_w3
from app.constants.abi.lagoon import LAGOON_ABI
from app.constants.abi.erc20 import ERC20_ABI

router = APIRouter()

def get_new_total_assets(chain_id: int, vault_address: str, safe_address: str):
    w3 = get_w3(chain_id)
    vault_contract = w3.eth.contract(address=vault_address, abi=LAGOON_ABI)
    deposit_token_address = vault_contract.functions.asset().call()
    deposit_token_contract = w3.eth.contract(address=deposit_token_address, abi=ERC20_ABI)
    realTotalAssets = deposit_token_contract.functions.balanceOf(safe_address).call()
    return realTotalAssets

def get_keeper_txs(chain_id: int = 480):
    result = get_keepers_pending_txs_metadata(chain_id)
    """ Result JSON format example:
    result = {
        "vaults_txs": [
            {
                "status": "ok",
                "message": "Vault is in sync",
                "vault": {
                    "vault_id": "0x123",
                    "vault_address": "0x123",
                    "safe": "0x123",
                    "valuationManager": "0x123",
                    "underlying_token_address": "0x123",
                },
                "vault_txs": {
                    "initialUpdate": True,
                    "pendingDeposit": True,
                    "pendingRedeem": True,
                    "settledDeposit": [
                        "0x0000000000000000000000000000000000000000", 
                        "0x0000000000000000000000000000000000000000"
                    ],
                }
            }
        ]
    }    
    
    result = {
        "vaults_txs": [
            {
                "vault_id": "0x123",
                "vault_address": "0x123",
                "initialUpdate": True,
                "pendingDeposit": True,
                "pendingRedeem": True,
                "settledDeposit": [
                    "0x0000000000000000000000000000000000000000", 
                    "0x0000000000000000000000000000000000000000"
                ],
                "valuationManager": "0x123",
                "underlying_token_address": "0x123",
                "safe": "0x123"
            }
        ]
    } """

    if len(result["vaults_txs"]) == 0:
        return result
    
    
    txs = []
    
    for instance in result["vaults_txs"]:
        status = instance["status"]
        message = instance["message"]
        vault = instance["vault"]
        instance_txs = []
        if instance["status"] == "syncing" or instance["status"] == "error" or instance["vault_txs"] == {}:
            txs.append({
                "status": status,
                "message": message,
                "vault": vault,
                "txs": instance_txs
            })
            continue
        if instance["vault_txs"]["initialUpdate"] == True:
            realTotalAssets = 0
            instance_txs.append({
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                #"caller": vault_txs["valuationManager"],
                #"vault_id": vault_txs["vault_id"]
            })
            txs.append({
                "status": status,
                "message": message,
                "vault": vault,
                "txs": instance_txs
            })
            continue
        if instance["vault_txs"]["pendingDeposit"] == True or instance["vault_txs"]["pendingRedeem"] == True:
            realTotalAssets = get_new_total_assets(chain_id, vault["vault_address"], vault["safe"])
            instance_txs.append({
                "type": "updateNewTotalAssets",
                "assets": realTotalAssets,
                #"caller": vault_txs["valuationManager"],
                #"vault_id": vault_txs["vault_id"]
            })
            if instance["vault_txs"]["pendingRedeem"] == True:
                # The underlying_token address must approve the Vault to handle the required 
                # amount of assets for redeem settlement.
                # That is: asset.approve(vaultAddress, realTotalAssets);
                instance_txs.append({
                    "type": "approve",
                    "assets": realTotalAssets,
                    #"caller": vault_txs["safe"],
                    #"vault_id": vault_txs["vault_id"]
                })
            # Lagoon's deposit settlement includes settle redeem.
            instance_txs.append({
                "type": "settleDeposit",
                "assets": realTotalAssets,
                #"caller": vault_txs["safe"],
                #"vault_id": vault_txs["vault_id"]
            })
        if len(instance["vault_txs"]["settledDeposit"]) > 0:
            instance_txs.append({
                "type": "claimSharesOnBehalf",
                "controllers": instance["vault_txs"]["settledDeposit"],
                #"caller": vault_txs["safe"],
                #"vault_id": vault_txs["vault_id"]
            })
        txs.append({
            "status": status,
            "message": message,
            "vault": vault,
            "txs": instance_txs
        })
    return {"vaults_txs": txs}


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
