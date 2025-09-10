import logging
import os
from pathlib import Path
from typing import Optional

from browser_use import AgentHistoryList, BrowserSession, Agent, BrowserProfile
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Import the custom controller if it's in a relative path.
# Assuming 'actions' is a package relative to where BrowserAgent might be imported from.
# Adjust this import based on your actual file structure for 'controller'.
from services.actions.tab_actions import controller

# Configure logging for this module
logging.basicConfig(level=logging.INFO) # Basic config, you might want a more sophisticated setup
logger = logging.getLogger(__name__)

load_dotenv() # Load environment variables from .env file

class BrowserAgent:
    """
    Manages a single browser instance and executes tasks using the browser-use agent.
    Each BrowserAgent operates on a unique Chrome user profile.
    """
    def __init__(self, user_data_dir: Path, cdp_port: int, headless: bool = True):
        """
        Initializes the BrowserAgent with its specific browser profile and CDP port.

        Args:
            user_data_dir (Path): Path to the unique Chrome user data directory for this agent.
                                  This directory should ideally be pre-populated/cloned.
            cdp_port (int): The unique Chrome DevTools Protocol port for this agent.
            headless (bool): Whether to run the browser in headless mode (no visible UI).
                             Defaults to True for production; set to False for debugging.
        """
        self.llm = ChatOpenAI(model="gpt-4o") # Initialize LLM for the browser-use Agent
        self.user_data_dir = user_data_dir
        self.cdp_port = cdp_port
        self.cdp_url = f"http://localhost:{cdp_port}"
        self.headless = headless
        
        # Ensure the user_data_dir exists
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized BrowserAgent for profile: {self.user_data_dir} on CDP port: {self.cdp_port}")

        # Set up browser session
        self.browser_session: Optional[BrowserSession] = None # Will be set in initialize()
        self.is_running = False # Track if the browser session is active

    async def initialize(self):
        """
        Starts the browser session for this agent.
        This should be called once when the agent is added to the pool.
        """
        if self.is_running and self.browser_session and self.browser_session.is_connected:
            logger.info(f"Browser session already running for {self.user_data_dir}.")
            return

        try:
            logger.info(f"Connecting to Chrome instance at {self.cdp_url}...")
            self.browser_session = BrowserSession(
                headless=self.headless,
                viewport={'width': 1920, 'height': 1080}, # Standard viewport
                keep_alive=True, # Keep the browser process alive between tasks
                cdp_url=self.cdp_url, # Connect to the pre-launched Chrome instance
                allowed_domains=['*.google.com', 'maps.app.goo.gl','*.sevenrooms.com'], # IMPORTANT: Expand as needed!
            )
            await self.browser_session.start()
            self.is_running = True
            logger.info(f"Successfully connected to Chrome instance at {self.cdp_url}.")
        except Exception as e:
            self.is_running = False
            logger.error(f"Failed to connect to Chrome instance at {self.cdp_url}: {e}", exc_info=True)
            raise # Re-raise to signal failure to the pool manager

    async def execute_task(self, task_instruction: str) -> AgentHistoryList:
        """
        Execute a browser task using the browser-use agent.
        Assumes the browser session is already initialized and running.

        Args:
            task_instruction (str): The specific instruction string for the agent.

        Returns:
            AgentHistoryList: The history of actions taken by the agent.
        
        Raises:
            RuntimeError: If the browser session is not running.
            Exception: Any error encountered during task execution.
        """
        if not self.is_running or not self.browser_session or not self.browser_session.is_connected:
            # Attempt to restart the session if it's not connected, or raise an error
            logger.warning(f"Browser session for {self.user_data_dir} not active. Attempting to re-initialize.")
            try:
                await self.initialize()
            except Exception as e:
                raise RuntimeError(f"Browser session for {self.user_data_dir} is not running and failed to re-initialize: {e}")

        try:
            logger.info(f"Executing task on {self.user_data_dir}: '{task_instruction}'")

            # Define initial actions using our custom action (e.g., to reset tabs)
            # This ensures a clean slate for each task if desired.
            initial_actions = [
                {'reset_browser_tabs': {'browser_session': self.browser_session}}
            ]

            agent = Agent(
                task=task_instruction,
                llm=self.llm,
                browser_session=self.browser_session,
                use_vision=False, # Set to True if you plan to use vision capabilities with GPT-4o-vision
                initial_actions=initial_actions,
                controller=controller, # Your custom controller for specific actions
                save_conversation_path="logs/conversation" # Optional: path to save agent conversation logs
            )

            print("--------------------------------")
            # log the tools in the controller
            print(str(controller))
            print("--------------------------------")
            
            logger.info(f"Running browser agent for task: '{task_instruction}'")
            result = await agent.run(max_steps=50) # Increased max_steps as a safe default

            duration_sec = result.total_duration_seconds()
            duration_min = round(duration_sec / 60, 2) if duration_sec is not None else None
            steps = result.number_of_steps()
            
            logger.info(f"Browser agent completed task '{task_instruction[:50]}...' successfully in {duration_min} mins and {steps} steps on {self.user_data_dir}.")
            
            return result

        except Exception as e:
            logger.error(f"Error executing browser task '{task_instruction[:50]}...' on {self.user_data_dir}: {e}", exc_info=True)
            # Mark agent as potentially unhealthy if a severe error occurs
            self.is_running = False # Consider a more granular health check
            raise e # Re-raise for the Browser Worker to handle

    async def close(self):
        """
        Gracefully closes the browser session.
        This should be called when the agent is removed from the pool or on shutdown.
        """
        if self.browser_session and self.is_running:
            try:
                logger.info(f"Closing browser session for {self.user_data_dir}...")
                await self.browser_session.close()
                self.is_running = False
                logger.info(f"Browser session closed for {self.user_data_dir}.")
            except Exception as e:
                logger.error(f"Error closing browser session for {self.user_data_dir}: {e}", exc_info=True)
        elif self.browser_session:
             logger.info(f"Browser session for {self.user_data_dir} was already disconnected or not started.")
        else:
            logger.info(f"BrowserSession object not initialized for {self.user_data_dir}.")