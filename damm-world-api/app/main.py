from fastapi import FastAPI
from app.auth.auth import router as auth_router
from app.endpoints.get_user_txs import router as get_user_txs_router
from app.endpoints.get_vault_snapshots import router as get_vault_snapshots_router
from app.endpoints.get_user_position import router as get_user_position_router
from app.endpoints.get_integrated_position import router as get_integrated_position_router
from app.endpoints.get_keeper_txs import router as get_keeper_txs_router
from app.endpoints.post_keeper_status import router as post_keeper_status_router
from app.websockets.routes import router as public_ws_router
from app.websockets.private import router as private_ws_router


from app.redis_listener import register_redis_listener

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DAMM World API", version="0.1.0")

# Allow frontend (localhost:3000) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# Register WebSocket routers
app.include_router(public_ws_router)
app.include_router(private_ws_router)

# Register Redis listener on app startup
register_redis_listener(app)

# Root endpoint for checking if the API is running
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Hello from DAMM World!"}