from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from eth_account.messages import encode_defunct
from eth_account import Account
import json
from .manager import active_connections

router = APIRouter()

@router.websocket("/ws/private")
async def websocket_private(websocket: WebSocket):
    await websocket.accept()

    try:
        auth_msg = await websocket.receive_text()
        auth_data = json.loads(auth_msg)
        wallet = auth_data.get("wallet")
        signature = auth_data.get("signature")
        nonce = auth_data.get("nonce")

        if not wallet or not signature or not nonce:
            await websocket.close(code=4002)
            print("[Private WS] Missing wallet, signature, or nonce")
            return

        # Verify wallet signature
        message = encode_defunct(text=nonce)
        recovered_wallet = Account.recover_message(message, signature=signature)

        if recovered_wallet.lower() != wallet.lower():
            await websocket.close(code=4001)
            print(f"[Private WS] Authentication failed for wallet {wallet}")
            return

        active_connections[wallet.lower()] = websocket
        print(f"[Private WS] Authenticated connection for wallet {wallet}")

        await websocket.send_json({
            "event": "auth_success",
            "message": "WebSocket authenticated successfully"
        })

        while True:
            await websocket.receive_text()  # Keep connection alive

    except WebSocketDisconnect:
        if wallet and wallet.lower() in active_connections:
            del active_connections[wallet.lower()]
        print(f"[Private WS] Disconnected wallet: {wallet}")
