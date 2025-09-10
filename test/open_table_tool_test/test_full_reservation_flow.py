import pytest
import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider
from services.actions.utils import build_reservation_success_message

RESTAURANT_URL = "https://www.opentable.ae/r/filia-dubai?ref=18584"
WAIT_TIME = 2000  # ms
# Connect to the first Chrome profile launched by launch_chrome_profiles.py
BROWSER_WS_ENDPOINT = "http://localhost:9222"

@pytest.mark.asyncio
async def test_full_reservation_flow():
    provider = OpenTableProvider()
    party_size = 2
    date = "2025-07-22"  # Format: YYYY-MM-DD (adjust as needed)
    time_24h = "19:00"    # Format: HH:MM (24-hour, adjust as needed)
    first_name = "John"
    last_name = "Doe"
    phone = "+971501234567"
    email = "john.doe@example.com"

    async with async_playwright() as p:
        # Connect to the running Chrome instance via CDP
        browser = await p.chromium.connect_over_cdp(BROWSER_WS_ENDPOINT)
        page = await browser.new_page()
        await page.goto(RESTAURANT_URL)
        await page.wait_for_timeout(WAIT_TIME)

        # 1. Select party size
        result = await provider.reserve_with_provider(page, party_size, date, time_24h, first_name, last_name, phone, email)
        print("Party size result:", result.extracted_content)
        assert "success" in result.extracted_content.lower()

        await browser.close()