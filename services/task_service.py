import asyncio
import uuid
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

# Assuming these are in your project structure
from models.task import Task, TaskStatus, TaskResultResponse, TaskRequest, TaskResponse
from services.browser_agent import BrowserAgent
from services.firestore_service import firestore_service # Assuming this is correctly implemented

# Environment variables for configuration
import os
from dotenv import load_dotenv

# Configure logging for the TaskService module
logging.basicConfig(level=logging.INFO) # Basic config; consider more advanced for production
logger = logging.getLogger(__name__)

load_dotenv() # Load environment variables from .env file

# --- Configuration Constants (load from environment variables) ---
# Number of concurrent browser agents/workers
NUM_BROWSER_WORKERS = int(os.getenv("NUM_BROWSER_WORKERS", 2))
# Base directory where cloned Chrome profiles are stored
CLONED_PROFILES_BASE_DIR = Path(os.getenv("CLONED_PROFILES_BASE_DIR", "~/.config/browseruse/profiles"))
# Starting CDP port for browser agents
START_CDP_PORT = int(os.getenv("START_CDP_PORT", 9222))
# Whether browser agents should run in headless mode (True for production)
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"


class TaskService:
    """
    Manages the lifecycle of browser automation tasks, including queuing,
    dispatching to a pool of browser agents, and persisting state to Firestore.
    """


    def __init__(self):
        self.task_queue: asyncio.Queue = asyncio.Queue()  # Queue for incoming tasks
        self.tasks: Dict[str, Task] = {}  # In-memory registry of all tasks by ID
        
        # Pool of available BrowserAgent instances (ready to take a task)
        self.available_agents: asyncio.Queue[BrowserAgent] = asyncio.Queue()
        # Keep a master list of all browser agents created for proper shutdown
        self._all_browser_agents: List[BrowserAgent] = []
        
        # Semaphore to limit the number of concurrent browser operations
        self.browser_semaphore = asyncio.Semaphore(NUM_BROWSER_WORKERS)
        
        # List to hold references to the background worker coroutines
        self._worker_tasks: List[asyncio.Task] = []

        logger.info("TaskService initialized.")

    async def _initialize_browser_agents(self):
        """
        Creates the pool of BrowserAgent instances without starting their sessions.
        Sessions will be started lazily when agents are first used.
        """
        logger.info(f"Creating {NUM_BROWSER_WORKERS} browser agents...")
        
        # Ensure the base directory for cloned profiles exists
        CLONED_PROFILES_BASE_DIR.mkdir(parents=True, exist_ok=True)

        for i in range(NUM_BROWSER_WORKERS):
            # Assign a unique user data directory for each browser agent
            # We use modulo operator to cycle through available cloned profiles
            # if NUM_BROWSER_WORKERS > NUM_PROFILE_COPIES (assumed to be 5 from original code)
            # You'd typically need a pre-created set of unique profiles here.
            # For this example, we'll assume profile_0, profile_1 etc. are pre-cloned.
            profile_name = f"profile_{i % 5}" # Assuming you have at least 5 pre-cloned profiles
            agent_user_data_dir = CLONED_PROFILES_BASE_DIR / profile_name
            
            # Assign a unique CDP port to each agent
            agent_cdp_port = START_CDP_PORT + i

            try:
                # Instantiate BrowserAgent with its unique configuration (but don't start session yet)
                agent = BrowserAgent(
                    user_data_dir=agent_user_data_dir,
                    cdp_port=agent_cdp_port,
                    headless=HEADLESS_MODE
                )
                self._all_browser_agents.append(agent) # Add to master list
                await self.available_agents.put(agent) # Add to available pool
                logger.info(f"BrowserAgent {i} (profile: {agent_user_data_dir.name}, port: {agent_cdp_port}) created and added to pool.")
            except Exception as e:
                logger.error(f"Failed to create BrowserAgent {i}: {e}", exc_info=True)
                # Depending on error, you might want to stop startup or log and continue with fewer agents
                continue # Try to create next agent

        if not self._all_browser_agents:
            logger.error("No browser agents could be created. TaskService cannot run.")
            raise RuntimeError("No browser agents available.")

    async def start(self):
        """
        Start the TaskService, initializing browser agents and launching worker coroutines.
        """
        logger.info("Starting TaskService...")
        await self._initialize_browser_agents() # Initialize the browser agent pool

        # Launch multiple worker coroutines to process tasks concurrently
        for i in range(NUM_BROWSER_WORKERS):
            worker_task = asyncio.create_task(self._process_single_worker(i))
            self._worker_tasks.append(worker_task)
        
        logger.info(f"TaskService started with {len(self._worker_tasks)} worker(s).")

    async def stop(self):
        """
        Stop the TaskService, gracefully shutting down workers and browser agents.
        """
        logger.info("Stopping TaskService...")
        
        # 1. Cancel all running worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for all worker tasks to finish cancellation
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        logger.info("All worker tasks cancelled.")

        # 2. Close all browser agents
        for agent in self._all_browser_agents:
            await agent.close()
        logger.info("All browser agents closed.")
        
        logger.info("TaskService stopped.")

    async def _check_and_restart_agents(self):
        """
        Check if any agents are healthy and attempt to reconnect to Chrome instances.
        Note: This can only reconnect to existing Chrome instances, not start new ones.
        """
        logger.info("Checking agent health and attempting reconnections...")
        
        healthy_agents = 0
        for agent in self._all_browser_agents:
            if agent.is_running:
                healthy_agents += 1
            else:
                # Try to reconnect to existing Chrome instance
                try:
                    logger.info(f"Attempting to reconnect to Chrome instance for {agent.user_data_dir.name} on {agent.cdp_url}...")
                    await agent.initialize()
                    if agent.is_running:
                        await self.available_agents.put(agent)
                        healthy_agents += 1
                        logger.info(f"Successfully reconnected to Chrome instance for {agent.user_data_dir.name}")
                    else:
                        logger.warning(f"Failed to reconnect to Chrome instance for {agent.user_data_dir.name} - Chrome may need to be restarted manually")
                except Exception as e:
                    logger.error(f"Error reconnecting to Chrome instance for {agent.user_data_dir.name}: {e}")
        
        logger.info(f"Agent health check complete: {healthy_agents}/{len(self._all_browser_agents)} agents healthy")
        
        if healthy_agents == 0:
            logger.error("⚠️  ALL BROWSERS ARE DOWN! Manual intervention required.")
            logger.error("Please run: python launch_chrome_profiles.py")
        
        return healthy_agents > 0

    async def create_task(self, instruction: str) -> str:
        """
        Create a new task with the given instruction string.

        Args:
            instruction (str): The instruction string for the browser agent.

        Returns:
            str: The generated task ID.
        """
        task_id = str(uuid.uuid4())
        task_obj = Task(
            id=task_id, 
            instruction=instruction,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            duration_seconds=None, # Initially no duration
            steps=None, # Initially no steps
            result=None, # Initially no result
            error=None, # Initially no error
        )
        self.tasks[task_id] = task_obj
        await self.task_queue.put((task_id, task_obj))
        logger.info(f"Created new task with id: {task_id}, instruction: '{instruction[:50]}...'")
        
        # Persist initial task state to Firestore
        await firestore_service.update_task_status(
            task_id, 
            TaskStatus.PENDING, 
            task=task_obj.instruction, # Store the full instruction
            created_at=task_obj.created_at
        )
        
        return task_id

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID from the in-memory registry.
        """
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task from the in-memory registry.
        """
        task = self.tasks.get(task_id)
        return task.status if task else None

    def get_task_result(self, task_id: str) -> Optional[TaskResultResponse]:
        """
        Get the result of a completed or failed task.
        """
        task = self.tasks.get(task_id)
        if not task or (task.status != TaskStatus.COMPLETED and task.status != TaskStatus.FAILED):
            return None

        return TaskResultResponse(
            result=task.result,
            error=task.error
        )

    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                 result: Optional[str] = None, error: Optional[str] = None, 
                                 duration: Optional[float] = None) -> Optional[Task]:
        """
        Update the status of a task in both in-memory registry and Firestore.
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now() # Update timestamp

            if result is not None: # Check for None explicitly as result might be empty string
                task.result = result
            if error is not None:
                task.error = error
            if duration is not None:
                task.duration_seconds = duration

            # Update status in Firestore
            await firestore_service.update_task_status(
                task_id, 
                status, 
                result=task.result, 
                error=task.error, 
                duration=task.duration_seconds,
                updated_at=task.updated_at
            )
            logger.debug(f"Task {task_id} status updated to {status.value} in Firestore.")
            return task
        logger.warning(f"Attempted to update status for non-existent task: {task_id}")
        return None

    async def _process_single_worker(self, worker_id: int) -> None:
        """
        Background worker coroutine that processes tasks from the queue.
        Each worker operates independently and manages its assigned browser agent.
        """
        logger.info(f"Worker {worker_id} started.")
        while True:
            browser_agent: Optional[BrowserAgent] = None # Declare outside try for finally block
            task_id, task_obj = None, None # Declare outside try for logging in finally block
            try:
                # 1. Get a task from the queue
                task_id, task_obj = await self.task_queue.get()
                logger.info(f"Worker {worker_id} picked up task {task_id}.")

                # 2. Acquire a semaphore slot for concurrent browser operation
                async with self.browser_semaphore:
                    # 3. Get an available browser agent from the pool
                    try:
                        browser_agent = await asyncio.wait_for(self.available_agents.get(), timeout=30.0)
                        logger.info(f"Worker {worker_id} acquired agent on {browser_agent.cdp_url} for task {task_id}.")
                        
                        # Initialize the browser session if it's not already running
                        if not browser_agent.is_running:
                            logger.info(f"Connecting to Chrome instance on {browser_agent.cdp_url}...")
                            try:
                                await browser_agent.initialize()
                            except Exception as init_error:
                                # Handle CDP connection failures specifically
                                if "ECONNREFUSED" in str(init_error) or "connect" in str(init_error).lower():
                                    logger.error(f"Worker {worker_id}: Cannot connect to Chrome instance on {browser_agent.cdp_url}. Chrome may be down.")
                                    # Mark this agent as unhealthy and try to get another one
                                    browser_agent.is_running = False
                                    # Put the task back in queue and try with a different agent
                                    await self.task_queue.put((task_id, task_obj))
                                    await self.update_task_status(
                                        task_id, 
                                        TaskStatus.PENDING, 
                                        error=f"Task re-queued: Chrome instance down on {browser_agent.cdp_url}"
                                    )
                                    # Don't return this agent to the pool
                                    browser_agent = None
                                    continue  # Try with next agent
                                else:
                                    # Re-raise other initialization errors
                                    raise init_error
                            
                    except asyncio.TimeoutError:
                        # No healthy agents available - all browsers might be down
                        logger.error(f"Worker {worker_id}: No healthy browser agents available after 30 seconds. All browsers may be down.")
                        
                        # Try to reconnect to existing Chrome instances
                        agents_restored = await self._check_and_restart_agents()
                        
                        if agents_restored:
                            logger.info(f"Worker {worker_id}: Some Chrome instances were reconnected. Re-queuing task to try again.")
                            # Re-queue the task to try with reconnected agents
                            await self.task_queue.put((task_id, task_obj))
                            await self.update_task_status(
                                task_id, 
                                TaskStatus.PENDING, 
                                error="Task re-queued: Chrome instances reconnected, retrying"
                            )
                        else:
                            logger.error(f"Worker {worker_id}: No Chrome instances could be reconnected. Manual restart required.")
                            # Mark task as failed since no agents are available
                            await self.update_task_status(
                                task_id, 
                                TaskStatus.FAILED, 
                                error="Task failed: All Chrome instances down. Manual restart required: python launch_chrome_profiles.py"
                            )
                        
                        # Wait before trying again
                        await asyncio.sleep(10)
                        continue  # Skip to next iteration

                    # Update task status to IN_PROGRESS
                    await self.update_task_status(task_id, TaskStatus.IN_PROGRESS)

                    # 4. Execute the task using the browser agent
                    try:
                        agent_result = await browser_agent.execute_task(task_obj.instruction)
                        duration = agent_result.total_duration_seconds()

                        if not agent_result.is_successful():
                            # Task failed in browser agent
                            error_details = str(agent_result.errors()) if agent_result.errors() else "Unknown browser agent error."
                            logger.error(f"Task {task_id} failed in browser agent. Errors: {error_details}")
                            
                            # Mark task as failed immediately
                            await self.update_task_status(
                                task_id, 
                                TaskStatus.FAILED, 
                                result=str(agent_result.final_result()), 
                                error=error_details, 
                                duration=duration
                            )
                        else:
                            # Task completed successfully
                            logger.info(f"Task {task_id} completed successfully. Duration: {duration} seconds")
                            await self.update_task_status(
                                task_id, 
                                TaskStatus.COMPLETED, 
                                result=str(agent_result.final_result()), 
                                duration=duration
                            )

                    except Exception as e:
                        # Catch unexpected errors during execute_task (e.g., browser crash, LLM error)
                        error_msg = f"Browser agent critical error: {str(e)}"
                        logger.error(f"Task {task_id} encountered critical browser agent error: {error_msg}", exc_info=True)
                        
                        # Check if the browser agent became unhealthy
                        if browser_agent and not browser_agent.is_running:
                            logger.warning(f"BrowserAgent {browser_agent.user_data_dir.name} is unhealthy. Re-queuing task {task_id} for another agent...")
                            
                            # Re-queue the task for another agent to process
                            await self.task_queue.put((task_id, task_obj))
                            
                            # Update status to indicate task is being retried
                            await self.update_task_status(
                                task_id, 
                                TaskStatus.PENDING, 
                                error=f"Task re-queued due to unhealthy agent: {error_msg}"
                            )
                            
                            # Try to restart the unhealthy agent
                            try:
                                await browser_agent.close() # Ensure it's fully closed
                                await browser_agent.initialize() # Attempt restart
                                logger.info(f"BrowserAgent {browser_agent.user_data_dir.name} restarted successfully.")
                            except Exception as restart_e:
                                logger.error(f"Failed to restart BrowserAgent {browser_agent.user_data_dir.name}: {restart_e}. This agent might be unusable.", exc_info=True)
                                # If an agent fails to restart, consider removing it from the pool
                                # and potentially replacing it or scaling down. For simplicity, we'll
                                # keep it in _all_browser_agents but it won't be returned to available_agents.
                        else:
                            # If the agent is still healthy, mark task as failed (likely a task-specific error)
                            await self.update_task_status(task_id, TaskStatus.FAILED, error=error_msg)


            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled.")
                break # Exit loop cleanly
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Unexpected error in worker {worker_id}: {error_msg}", exc_info=True)
                
                # Check if this is a CDP connection error
                if "ECONNREFUSED" in error_msg or "connect" in error_msg.lower():
                    logger.error(f"Worker {worker_id}: CDP connection failed. Chrome instances may be down.")
                    logger.error("Please restart Chrome instances with: python launch_chrome_profiles.py")
                    
                    # If we have a task, mark it as failed with clear instructions
                    if task_id and task_obj:
                        await self.update_task_status(
                            task_id, 
                            TaskStatus.FAILED, 
                            error=f"CDP connection failed: {error_msg}. Please restart Chrome instances with: python launch_chrome_profiles.py"
                        )
                
                # Prevent tight loop on persistent unexpected errors
                await asyncio.sleep(5) 
            finally:
                # Ensure the task is marked done in the queue
                if task_id: # Only call task_done if a task was actually popped
                    self.task_queue.task_done() 
                # Return the browser agent to the available pool ONLY if it's still healthy
                if browser_agent and browser_agent.is_running:
                    await self.available_agents.put(browser_agent)
                    logger.debug(f"Agent {browser_agent.user_data_dir.name} returned to pool by worker {worker_id}.")
                elif browser_agent:
                    logger.warning(f"Agent {browser_agent.user_data_dir.name} was unhealthy and not returned to pool by worker {worker_id}.")