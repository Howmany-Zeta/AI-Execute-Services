from typing import Any, Dict

import socketio  # type: ignore[import-untyped]
from typing import Dict, Any
from aiecs.config.config import get_settings

settings = get_settings()
# In production, this should be set to specific origins
# For example: ["https://your-frontend-domain.com"]
allowed_origins = settings.cors_allowed_origins.split(",") if hasattr(settings, "cors_allowed_origins") else ["http://express-gateway:3001"]

# Allow all origins for development (more permissive)
# In production, you should use specific origins
# Explicitly set async_mode to 'asgi' for compatibility with uvicorn
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
# We no longer create a FastAPI app or combined ASGI app here
# The FastAPI app will be created in main.py and the Socket.IO server will
# be mounted there

# Store connected clients by user ID
connected_clients: Dict[str, Any] = {}


@sio.event
async def connect(sid, environ, auth=None):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for user, socket_id in list(connected_clients.items()):
        if socket_id == sid:
            del connected_clients[user]


@sio.event
async def register(sid, data):
    user_id = data.get("user_id")
    if user_id:
        connected_clients[user_id] = sid
        print(f"Registered user {user_id} on SID {sid}")


# Send progress update to user


async def push_progress(user_id: str, data: dict):
    sid = connected_clients.get(user_id)
    if sid:
        await sio.emit("progress", data, to=sid)
