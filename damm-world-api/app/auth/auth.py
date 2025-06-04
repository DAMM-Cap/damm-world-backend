from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from eth_account.messages import encode_defunct
from eth_account import Account
from app.auth.jwt_auth import create_jwt

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    address: str
    signature: str
    message: str

@router.post("/login")
def login(data: LoginRequest):
    encoded_message = encode_defunct(text=data.message)
    recovered_address = Account.recover_message(encoded_message, signature=data.signature)

    if recovered_address.lower() != data.address.lower():
        raise HTTPException(status_code=401, detail="Signature verification failed")

    # Generate JWT
    jwt_payload = {"address": data.address}
    token = create_jwt(jwt_payload)
    return {"access_token": token, "token_type": "bearer"}
