import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_document import DocumentSnapshot
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from models.task import TaskStatus, Task # Import the Task model to map data

import os
from pathlib import Path

# Configure logging for the FirestoreService module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirestoreService:
    """
    Manages interactions with Google Cloud Firestore for persisting task data.
    Ensures Firebase Admin SDK is initialized once and handles task data updates and retrieval.
    """
    def __init__(self):
        # Initialize Firebase Admin SDK if it hasn't been already
        if not firebase_admin._apps: # Check if any app is already initialized
            try:
                # Get the path to the service account key from environment variable
                service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
                
                if not service_account_path:
                    # Fallback to default path for backward compatibility
                    current_dir = Path(__file__).parent
                    service_account_path = str(current_dir.parent / "firebase-service-account.json")
                    logger.warning(f"FIREBASE_SERVICE_ACCOUNT_PATH not set, using default: {service_account_path}")

                service_account_path = Path(service_account_path).expanduser()

                if not service_account_path.exists():
                    raise FileNotFoundError(
                        f"Firebase service account key not found at {service_account_path}"
                        f"\nPlease set FIREBASE_SERVICE_ACCOUNT_PATH environment variable or ensure the file exists."
                    )

                cred = credentials.Certificate(str(service_account_path))
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully.")
            except ValueError:
                logger.warning("Firebase Admin SDK already initialized.")
            except Exception as e:
                logger.error(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
                raise # Re-raise if initialization fails, as service cannot function

        self.db = firestore.client()
        # Define the main collection for tasks. Consider using a clear name like 'tasks' or 'automation_tasks'.
        # 'browser_bookings' is fine if it aligns with your domain.
        self.tasks_collection = self.db.collection('browser_bookings')
        logger.info(f"FirestoreService connected to collection: '{self.tasks_collection.id}'")

    # The original update_task_status was missing 'task' and 'created_at' for initial write.
    # We add them as optional fields.
    async def update_task_status(self, 
                                 task_id: str, 
                                 status: TaskStatus, 
                                 result: Optional[str] = None, 
                                 error: Optional[str] = None, 
                                 duration: Optional[float] = None,
                                 task: Optional[str] = None, # The original instruction string
                                 created_at: Optional[datetime] = None, # Timestamp of task creation
                                 updated_at: Optional[datetime] = None # Explicit update timestamp
                                ):
        """
        Updates task status and other relevant fields in Firestore.
        Uses set(merge=True) for partial updates.
        """
        try:
            task_data: Dict[str, Any] = {
                'status': status.value, # Store enum value as string
                'updated_at': firestore.SERVER_TIMESTAMP # Use server timestamp for updates
            }

            if task is not None:
                task_data['task'] = task
            
            if created_at is not None:
                # Ensure created_at is only set on initial creation
                # Firestore will convert datetime objects to its Timestamp type
                task_data['created_at'] = created_at.astimezone(timezone.utc) # Store as UTC

            if result is not None:
                task_data['result'] = result
            if error is not None:
                task_data['error'] = error
            if duration is not None:
                task_data['duration_seconds'] = duration # Renamed to match Task model field
            
            # Using set(merge=True) creates the document if it doesn't exist or merges data if it does.
            # This is suitable for both initial creation and subsequent updates.
            self.tasks_collection.document(task_id).set(task_data, merge=True)
            logger.info(f"Updated task '{task_id}' with status '{status.value}' in Firestore.")
        except Exception as e:
            logger.error(f"Error updating task '{task_id}' status in Firestore: {e}", exc_info=True)
            raise # Re-raise for calling service to handle

    async def get_task_data(self, task_id: str) -> Optional[Task]:
        """
        Retrieves complete task data for a given task ID from Firestore and
        converts it to a Task Pydantic model.
        """
        try:
            doc: DocumentSnapshot = self.tasks_collection.document(task_id).get()
            if doc.exists:
                data = doc.to_dict()
                if data:
                    # Firestore timestamps are returned as google.cloud.firestore_v1.types.Timestamp
                    # Pydantic's datetime conversion handles this automatically if `datetime` is expected.
                    # Ensure all fields expected by Task model are present or handled as Optional.
                    
                    # Convert Firestore data back to our Pydantic Task model
                    # The 'id' field is the document ID
                    data['id'] = doc.id 
                    
                    # Adjust field names to match Pydantic model if Firestore uses different names
                    # E.g., 'instruction' in Firestore maps to 'instruction' in Task
                    # 'duration' in Firestore maps to 'duration_seconds' in Task
                    if 'duration' in data:
                        data['duration_seconds'] = data.pop('duration')

                    return Task(**data)
            logger.info(f"Task '{task_id}' not found in Firestore.")
            return None
        except Exception as e:
            logger.error(f"Error getting task '{task_id}' data from Firestore: {e}", exc_info=True)
            raise # Re-raise for calling service to handle

# Create a singleton instance of FirestoreService
# This ensures only one connection to Firestore is established
firestore_service = FirestoreService()