from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_user_txs import get_user_txs

router = APIRouter()

@router.get("/lagoon/txs/test/{address}/{vault_address}")
def read_user_txs_test(
    address: str,
    vault_address: str,
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100.")
):
    result = get_user_txs(address, offset, limit, chain_id, vault_address)
    return result

@router.get("/lagoon/txs")
def read_user_txs(
    current_user: dict = Depends(get_current_user_jwt),
    vault_address: str = Query(..., description="Vault address"),
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100."),
):
    result = get_user_txs(current_user["address"], offset, limit, chain_id, vault_address)
    return result
