from fastapi import FastAPI
from app.auth.auth import router as auth_router
from app.endpoints.get_user_txs import router as get_user_txs_router

app = FastAPI(title="DAMM World API", version="0.1.0")

# Mount endpoints
app.include_router(auth_router)
app.include_router(get_user_txs_router)

# Root endpoint for testing
@app.get("/")
def read_root():
    return {"message": "Hello from DAMM World!"}

