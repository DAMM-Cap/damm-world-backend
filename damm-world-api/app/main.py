from fastapi import FastAPI, Depends
from app.auth.auth import router as auth_router
from app.auth.jwt_auth import get_current_user_jwt
from db.db import getEnvDb

app = FastAPI(title="DAMM World API", version="0.1.0")

# Mount /auth endpoints
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Hello from DAMM World!"}

def get_user_txs(address: str):
    db = getEnvDb('damm-public')
    lowercase_address = address.lower()
    tables = [
        "lagoon_depositrequest",
        "lagoon_redeemrequest",
        "lagoon_withdraw",
        "lagoon_transfer"
    ]

    all_txs = []
    for table in tables:
        df = db.frameResponse(
            f"SELECT *, %s AS source_table FROM {table} WHERE owner = %s",
            (table, lowercase_address,)
        )
        # Include a column to identify which table the record came from
        all_txs.extend(df.to_dict(orient="records"))

    return all_txs

@app.get("/lagoon/txs")
def read_user_txs(current_user=Depends(get_current_user_jwt)):
    return get_user_txs(current_user["address"])

@app.get("/lagoon/txs/test/{address}")
def read_user_txs_test(address: str):
    return get_user_txs(address)