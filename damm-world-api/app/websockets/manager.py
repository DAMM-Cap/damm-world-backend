from typing import List, Dict
from fastapi import WebSocket

# Active WebSocket connections for public updates
public_connections: List[WebSocket] = []

# Active WebSocket connections for private user updates: wallet -> WebSocket
active_connections: Dict[str, WebSocket] = {}

async def broadcast_update(message: dict):
    """
    Broadcast a message to all clients connected to public WebSocket endpoints.
    """
    disconnected = []
    for connection in public_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)

    for conn in disconnected:
        public_connections.remove(conn)

async def send_private_update(wallet: str, payload: dict):
    """
    Send a private message only to the client connected as the given wallet.
    """
    wallet = wallet.lower()
    if wallet in active_connections:
        try:
            await active_connections[wallet].send_json(payload)
            print(f"[Manager] Sent private update to {wallet}: {payload}")
        except Exception as e:
            print(f"[Manager] Error sending private update to {wallet}: {e}")
    else:
        print(f"[Manager] No active WebSocket for wallet {wallet}")
