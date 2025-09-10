import asyncio
import subprocess
import os
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use import Agent

STORAGE_STATE_PATH = '/tmp/google_auth.json'
GOOGLE_URL = 'https://mail.google.com/'

async def run_parallel_agents():
    # Create a shared profile with the storage state
    shared_profile = BrowserProfile(
        headless=False,  # Set to False for visibility during test
        user_data_dir=None,  # Use temp dir per session
        storage_state=STORAGE_STATE_PATH,
        keep_alive=True,
    )

    # Start two browser sessions with the same profile
    window1 = BrowserSession(browser_profile=shared_profile)
    window2 = BrowserSession(browser_profile=shared_profile)
    await window1.start()
    await window2.start()

    # Open Gmail in both sessions and check if logged in
    async def check_logged_in(window, label):
        page = await window.new_page()
        await page.goto(GOOGLE_URL)
        await asyncio.sleep(5)  # Wait for page to load
        title = await page.title()
        print(f"[{label}] Page title: {title}")
        # Optionally, check for a user-specific element
        content = await page.content()
        logged_in = 'Inbox' in title or 'Google Account' in content
        print(f"[{label}] Logged in: {logged_in}")
        await page.close()
        return logged_in

    results = await asyncio.gather(
        check_logged_in(window1, 'Session 1'),
        check_logged_in(window2, 'Session 2'),
    )

    await window1.save_storage_state()
    await window2.save_storage_state()
    await window1.close()
    await window2.close()
    print(f"Both sessions logged in: {results}")

if __name__ == '__main__':
    # Step 1: If storage state does not exist, open browser for manual login
    if not os.path.exists(STORAGE_STATE_PATH):
        print(f"Storage state not found at {STORAGE_STATE_PATH}. Launching Playwright for manual login...")
        subprocess.run([
            'playwright', 'open', 'https://accounts.google.com/', f'--save-storage={STORAGE_STATE_PATH}'
        ])
        print("Please log in to Google in the opened browser, then close it to continue.")
        input("Press Enter after closing the browser...")
    # Step 2: Run the parallel agent test
    asyncio.run(run_parallel_agents()) 