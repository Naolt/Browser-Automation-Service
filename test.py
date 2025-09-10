from browser_use import AgentHistoryList, BrowserSession, Agent, BrowserProfile
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


async def function_to_run():
    """
    This function is a placeholder for the main logic of your script.
    It can be used to encapsulate the code that you want to run.
    """

    browser_session = BrowserSession(
        # Linux path to Chrome or Chromium executable

        executable_path='/usr/bin/google-chrome',

        # Persistent user data directory (for storing cookies, sessions, etc.)
        user_data_dir='~/.config/browseruse/profiles/default',

        # Optional: run in visible mode (set to False to run headless)
        headless=False,
        timezone_id='America/New_York',

        locale='en-US',  # Set the locale for the browser session

        keep_alive=True,  # Keep the session alive for reuse

    )

    await browser_session.start()  # Start the browser session

    page1 = await browser_session.new_tab()  # Open a new tab in the browser session
    page2 = await browser_session.new_tab()  # Open another new tab in the browser session

    agent1 = Agent(
        task="Open google.com and see the lastest deepseek model specificaion",  # e.g., "Reserve a restaurant using Reserve with Google"
        llm=ChatOpenAI(model="gpt-4o"),                 # your LLM instance (e.g., OpenAI, Claude, etc.)
        page=page1,  # Use the first tab for this agent
    )

    agent2 = Agent(
        task="Open google.com and see the lastest gemini model specification",  # e.g., "Reserve a restaurant using Reserve with Google"
        llm=ChatOpenAI(model="gpt-4o"),                 # your LLM instance (e.g., OpenAI, Claude, etc.)
        page=page2,  # Use the second tab for this agent
    )


    await asyncio.gather(agent1.run(), agent2.run()) # run in parallel

if __name__ == "__main__":
    import asyncio

    # Run the function in an event loop
    asyncio.run(function_to_run())
    