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
    w3 = get_w3(chain_id)
    vault_contract = w3.eth.contract(address=vault_address, abi=LAGOON_ABI)
    deposit_token_address = vault_contract.functions.asset().call()
    deposit_token_contract = w3.eth.contract(address=deposit_token_address, abi=ERC20_ABI)
    realTotalAssets = deposit_token_contract.functions.balanceOf(vault_address).call()
    return realTotalAssets

def get_keeper_txs(chain_id: int = 480):
    result = get_keepers_pending_txs_metadata(chain_id)
    if len(result) == 0:
        return {"txs": []}
    
    """ Result JSON format example:
    result = {
        "pendingDeposit": True,
        "pendingRedeem": True,
        "settledDeposit": [
            0x0000000000000000000000000000000000000000, 
            0x0000000000000000000000000000000000000000
        ]
    } """
    txs = []
    
    if result["pendingDeposit"] == True or result["pendingRedeem"] == True:
        realTotalAssets = get_new_total_assets(chain_id)
        txs.append({
            "type": "updateNewTotalAssets",
            "assets": realTotalAssets,
            "caller": 'valuationManager'
        })

        # TODO: Check if the Safe must approve the Vault to transfer the required 
        # amount of assets for redeem settlement.

        # Lagoon's deposit settlement includes settle redeem.
        txs.append({
            "type": "settleDeposit",
            "assets": realTotalAssets,
            "caller": 'safe'
        })
    if len(result["settledDeposit"]) > 0:
        txs.append({
            "type": "claimSharesOnBehalf",
            "controllers": result["settledDeposit"],
            "caller": 'safe'
        })
    return {"txs": txs}


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
