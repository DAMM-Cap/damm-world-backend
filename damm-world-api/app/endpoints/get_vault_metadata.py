from fastapi import Depends, Query, APIRouter, HTTPException
from app.auth.jwt_auth import get_current_user_jwt
from db.query.endpoints.lagoon_vault_metadata import get_vault_metadata

router = APIRouter()

@router.get("/lagoon/vault-metadata/test/{vault_id}")
def read_vault_metadata_test(
    vault_id: str
):
    result = get_vault_metadata(vault_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Vault with id {vault_id} not found")
    return result

@router.get("/lagoon/vault-metadata")
def read_vault_metadata(
    current_user: dict = Depends(get_current_user_jwt),
    vault_id: str = Query(..., description="Vault ID (UUID)")
):
    result = get_vault_metadata(vault_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Vault with id {vault_id} not found")
    return result

