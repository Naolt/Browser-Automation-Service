import pytest
import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.google_provider import GoogleProvider
from services.actions.provider.open_table_provider import OpenTableProvider
from services.actions.utils import build_reservation_success_message

RESTAURANT_URL = "https://www.google.com/maps/reserve/dine?c=YVy89wh6SDc&ssst=2025-07-24T15%3A00%3A00.000Z&ld=20250724T190000&ps=4&gei=kyKCaJHoLYyqkdUPg-P92AE&hl=en-ET&opi=79508299&source=pa&sourceurl=https%3A%2F%2Fwww.google.com%2Fservice%2FMapsPlaceService%2FGetPlace%3Fhl%3Den%26authuser%3D0%26gl%3Det%26q%3DDoors%2BFreestyle%2BGrill%2B-%2BSteakhouse&ihs=44"
WAIT_TIME = 2000  # ms
# Connect to the first Chrome profile launched by launch_chrome_profiles.py
BROWSER_WS_ENDPOINT = "http://localhost:9222"

async def test_full_reservation_flow():
    provider = GoogleProvider()
    time = "23:00"
    

    async with async_playwright() as p:
        # Connect to the running Chrome instance via CDP
        browser = await p.chromium.connect_over_cdp(BROWSER_WS_ENDPOINT)
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        await page.goto(RESTAURANT_URL)

        await page.wait_for_timeout(WAIT_TIME)

        time_result = await provider.select_reservation_time(page, time)
        print("Time result:", time_result.extracted_content)
        provider_result = await provider.select_reservation_provider(page)
        print("Provider result:", provider_result.extracted_content)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_full_reservation_flow())
    print("Done")