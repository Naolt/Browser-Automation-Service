from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskStatus(str, Enum):
    """
    Represents the current status of a browser automation task.
    """
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled" # Added for completeness

class Task(BaseModel):
    """
    Represents a single browser automation task.
    """
    id: str = Field(..., description="Unique identifier for the task (session ID).")
    
    # The instruction string directly fed to the browser agent.
    # This comes from the AI Agent Orchestrator.
    instruction: str = Field(..., description="The direct instruction string for the browser agent.")
    
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current status of the task.")
    
    result: Optional[str] = Field(None, description="The result/output of the task upon completion.")
    
    error: Optional[str] = Field(None, description="Error message if the task failed.")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the task was created.")
    
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the task was last updated.")
    
    duration_seconds: Optional[float] = Field(None, description="Total duration of the task execution in seconds.")

    steps: Optional[int] = Field(None, description="Number of steps taken during the task execution.")

    class Config:
        use_enum_values = True # Ensures that enum values (strings) are used when serializing/deserializing

# This model is specifically for the API response as discussed
class TaskResponse(BaseModel):
    """
    API response model for task creation, returning just the session ID.
    """
    session_id: str = Field(..., description="The unique identifier for the created task.")

# This model is for the incoming request to the API
class TaskRequest(BaseModel):
    """
    API request model for creating a new task.
    """
    task: str = Field(..., description="The instruction string for the browser agent to execute.")


class TaskStatusResponse(BaseModel):
    status: TaskStatus

class TaskResultResponse(BaseModel):
    """
    Response model for retrieving the final result or error of a completed/failed task.
    """
    result: Optional[str] = Field(None, description="The final result string of the completed task.")
    error: Optional[str] = Field(None, description="An error message if the task failed.")

# ... (Your existing TaskRequest and TaskResponse models go here) ...