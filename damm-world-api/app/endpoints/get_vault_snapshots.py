from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_vault_snapshots import get_vault_snapshots

router = APIRouter()

@router.get("/lagoon/snapshots/test/{vault_id}")
def read_vault_snapshots(
    vault_id: str,
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100.")
):
    result = get_vault_snapshots(vault_id, offset, limit, chain_id)
    return result

@router.get("/lagoon/snapshots")
def read_vault_snapshots(
    current_user: dict = Depends(get_current_user_jwt),
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100."),
):
    result = get_vault_snapshots(current_user["vault_id"], offset, limit, chain_id)
    return result
