from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_user_position import get_user_position

router = APIRouter()

@router.get("/lagoon/position/test/{address}")
def read_user_positions_test(
    address: str,
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100.")
):
    result = get_user_position(address, offset, limit, chain_id)
    return result

@router.get("/lagoon/position")
def read_user_positions(
    current_user: dict = Depends(get_current_user_jwt),
    chain_id: int = Query(480, description="Chain ID (default: 480 for Worldchain)"),
    offset: int = Query(0, ge=0, description="Offset for pagination. Must be >= 0."),
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return per page. Max 100."),
):
    result = get_user_position(current_user["address"], offset, limit, chain_id)
    return result
