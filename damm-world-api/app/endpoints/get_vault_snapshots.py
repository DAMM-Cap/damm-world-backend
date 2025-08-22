from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_vault_snapshots import get_vault_snapshots

router = APIRouter()

@router.get("/lagoon/snapshots/test")
def read_vault_snapshots(
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100."),
    ranges: str = Query("all", description="Range of snapshots to return. Format: 24h | 7d | 1m | 6m | 1y | all")
):
    result = get_vault_snapshots(offset, limit, chain_id, ranges)
    return result

@router.get("/lagoon/snapshots")
def read_vault_snapshots(
    current_user: dict = Depends(get_current_user_jwt),
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100."),
    ranges: str = Query("all", description="Range of snapshots to return. Format: 24h | 7d | 1m | 6m | 1y | all")
):
    result = get_vault_snapshots(offset, limit, chain_id, ranges)
    return result
