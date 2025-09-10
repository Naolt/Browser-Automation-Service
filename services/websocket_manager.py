from typing import Dict, List
from fastapi import WebSocket

# Store active WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}


async def add_connection(task_id: str, websocket: WebSocket):
    if task_id not in active_connections:
        active_connections[task_id] = []
    active_connections[task_id].append(websocket)


def remove_connection(task_id: str, websocket: WebSocket):
    if task_id in active_connections:
        active_connections[task_id].remove(websocket)
        if not active_connections[task_id]:
            del active_connections[task_id]


def get_connections(task_id: str) -> List[WebSocket]:
    return active_connections.get(task_id, [])
