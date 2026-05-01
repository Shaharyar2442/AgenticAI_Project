"""
WebSocket Handler — real-time progress broadcasting.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections: session_id -> [websocket, ...]
connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/ws/progress/{session_id}")
async def progress_ws(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time pipeline progress."""
    await websocket.accept()

    if session_id not in connections:
        connections[session_id] = []
    connections[session_id].append(websocket)

    logger.info(f"WebSocket connected: {session_id}")

    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"WS received from {session_id}: {data}")
    except WebSocketDisconnect:
        connections[session_id].remove(websocket)
        if not connections[session_id]:
            del connections[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")


async def broadcast(session_id: str, message: dict):
    """Broadcast a progress message to all connected clients for a session."""
    if session_id not in connections:
        return

    dead = []
    for ws in connections[session_id]:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)

    for ws in dead:
        connections[session_id].remove(ws)
