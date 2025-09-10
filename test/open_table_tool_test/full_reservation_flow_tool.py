import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider


RESTAURANT_URL = "https://www.opentable.ae/r/filia-dubai?ref=18584"
WAIT_TIME = 2000  # ms
# Connect to the first Chrome profile launched by launch_chrome_profiles.py
BROWSER_WS_ENDPOINT = "http://localhost:9222"


async def main():
    provider = OpenTableProvider()
    party_size = 2
    date = "2025-07-29"  # Use a size that triggers the error (adjust as needed)
    time_24h = "20:30"    # Format: HH:MM (24-hour, adjust as needed)
    first_name = "John"
    last_name = "Doe"
    phone = "+971501234567"
    email = "john.doe@example.com"
    url = RESTAURANT_URL

    async with async_playwright() as p:
        # Connect to the running Chrome instance via CDP
        # browser = await p.chromium.connect_over_cdp(BROWSER_WS_ENDPOINT)
        # default_context = browser.contexts[0]
        # page = default_context.pages[0]
        
        browser = await p.chromium.launch(headless=False)  # headful mode
        page = await browser.new_page()
        await page.goto(url)

        # Wait for the page to load (adjust selector as needed)
        # await page.wait_for_selector('[data-test="party-size-picker"]')

        # Call your provider method
        result = await provider.reserve_with_provider(page, party_size, date, time_24h, first_name, last_name, phone, email)
        print("Result:", result.extracted_content)

        # Keep the browser open for a bit to observe
        await asyncio.sleep(1000)

if __name__ == "__main__":
    asyncio.run(main())