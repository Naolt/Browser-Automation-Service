import pytest
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider

# Use the provided sample URL for testing reservation type selection
RESERVATION_TYPE_URL = "https://www.opentable.ae/booking/specials?availabilityToken=eyJ2IjoyLCJtIjoxLCJwIjowLCJjIjo0NjEwMjcxLCJzIjoxLCJuIjowfQ&correlationId=3e8b1749-7138-41bf-8ba8-bca08d0d6d57&creditCardRequired=false&dateTime=2025-07-22T18:45:00&experienceIds=499808&partySize=2&points=100&pointsType=Standard&resoAttribute=default&rid=1277611&slotHash=2711189874&isModify=false&isMandatory=false&cfe=true&st=Experience&tableCategory=default&diningAreaId=1"

@pytest.mark.asyncio
async def test_select_reservation_type():
    provider = OpenTableProvider()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(RESERVATION_TYPE_URL)
        await page.wait_for_timeout(2000)

        result = await provider.select_reservation_type(page)
        print("Reservation type result:", result.extracted_content)
        assert "success" in result.extracted_content.lower()

        await browser.close()

@pytest.mark.asyncio
async def test_select_reservation_type_with_wrong_url():
    provider = OpenTableProvider()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.opentable.com")
        await page.wait_for_timeout(2000)

        result = await provider.select_reservation_type(page)
        print("Reservation type result:", result.extracted_content)
        assert "wrong" in result.extracted_content.lower()

        await browser.close()
        