from fastapi import Depends, Query, APIRouter
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_keeper_status import update_keeper_status as update_keeper_status_logic

router = APIRouter()

@router.post("/lagoon/keeper_status/test/{chain_id}/{vault_address}/{last_processed_block}/{last_processed_timestamp}")
def update_keeper_status_test(
    chain_id: int,
    vault_address: str,
    last_processed_block: int,
    last_processed_timestamp: str,
):
    """
    Test endpoint: Update keeper status without authentication (direct path params).
    """
    result = update_keeper_status_logic(chain_id, vault_address, last_processed_block, last_processed_timestamp)
    return result

@router.post("/lagoon/keeper_status")
def update_keeper_status(
    current_user: dict = Depends(get_current_user_jwt),
    chain_id: int = Query(..., description="Chain ID (default: 480 for Worldchain)"),
    vault_address: str = Query(..., description="Vault Address"),
    last_processed_block: int = Query(..., description="Last processed block"),
    last_processed_timestamp: str = Query(..., description="Last processed timestamp"),
):
    """
    Authenticated endpoint: Update keeper status with required query parameters.
    """
    result = update_keeper_status_logic(chain_id, vault_address, last_processed_block, last_processed_timestamp)
    return result
