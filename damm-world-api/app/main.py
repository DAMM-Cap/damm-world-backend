from fastapi import FastAPI
from app.auth.auth import router as auth_router
from app.endpoints.get_user_txs import router as get_user_txs_router
from app.endpoints.get_vault_snapshots import router as get_vault_snapshots_router
from app.endpoints.get_user_position import router as get_user_position_router
from app.endpoints.get_integrated_position import router as get_integrated_position_router
from app.endpoints.get_keeper_txs import router as get_keeper_txs_router
from app.endpoints.post_keeper_status import router as post_keeper_status_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DAMM World API", version="0.1.0")

allowed_origins_urls = []
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins:
    allowed_origins_urls = [u.strip() for u in allowed_origins.split(",") if u.strip()]

# Allow frontend (localhost:3000) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount endpoints
app.include_router(auth_router)
app.include_router(get_user_txs_router)
app.include_router(get_vault_snapshots_router)
app.include_router(get_user_position_router)
app.include_router(get_integrated_position_router)
app.include_router(get_keeper_txs_router)
app.include_router(post_keeper_status_router)

# Root endpoint for checking if the API is running
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Hello from DAMM World!"}