from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
from models.task import TaskRequest, TaskResponse, TaskStatusResponse, TaskResultResponse
from services.task_service import TaskService
from services.websocket_manager import add_connection, remove_connection

router = APIRouter()
task_service = TaskService()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    await add_connection(task_id, websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # You can handle client messages here if needed
    except WebSocketDisconnect:
        remove_connection(task_id, websocket)


@router.post("/book", response_model=TaskResponse)
async def create_task(request: TaskRequest):
    """Create a new task and return a session ID"""
    session_id = await task_service.create_task(request.task)
    return TaskResponse(session_id=session_id)


@router.get("/status/{session_id}", response_model=TaskStatusResponse)
async def get_task_status(session_id: str):
    """Get the status of a task"""
    status = task_service.get_task_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(status=status)


@router.get("/result/{session_id}", response_model=TaskResultResponse)
async def get_task_result(session_id: str):
    """Get the result of a completed task"""
    result = task_service.get_task_result(session_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Task not found or not completed")
    return result
