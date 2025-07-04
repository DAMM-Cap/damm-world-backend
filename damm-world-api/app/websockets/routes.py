from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import public_connections

router = APIRouter()

@router.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    await websocket.accept()
    public_connections.append(websocket)
    print(f"[Public WS] Authenticated connection")
    await websocket.send_json({"event": "welcome", "message": "WebSocket connected successfully"})

    try:
        while True:
            await websocket.receive_text()  # optional, can be used for ping/pong
    except WebSocketDisconnect:
        public_connections.remove(websocket)
